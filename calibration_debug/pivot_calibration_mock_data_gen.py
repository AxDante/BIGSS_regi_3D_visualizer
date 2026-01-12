
import numpy as np
import os
import sys
import random
import logging
from scipy.spatial.transform import Rotation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure output directory exists
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "test_files", "pivot_calibration")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Noise Parameters (Predefined, similar to AXXB gen)
# Optical Tracker Noise
TRACKER_NOISE_POS_MEAN = np.array([0.0, 0.0, 0.0]) # mm (Assume zero mean for simple noise)
TRACKER_NOISE_POS_STD = 0.5 # mm
TRACKER_NOISE_ROT_MEAN = np.array([0.0, 0.0, 0.0]) # degrees
TRACKER_NOISE_ROT_STD = 0.2 # degrees

def apply_noise(T_true, pos_mean, pos_std, rot_mean, rot_std):
    """
    Applies T_measured = T_true @ T_error
    where T_error is constructed from random noise.
    """
    # Translation Error (epsilon)
    epsilon = np.random.normal(pos_mean, pos_std, 3)
    
    # Rotation Error (alpha)
    alpha_deg = np.random.normal(rot_mean, rot_std, 3)
    alpha_rad = np.radians(alpha_deg)
    R_error = Rotation.from_rotvec(alpha_rad).as_matrix()
    
    T_error = np.eye(4)
    T_error[:3, :3] = R_error
    T_error[:3, 3] = epsilon
    
    return T_true @ T_error

def generate_pivot_data_subset(output_dir, num_samples, v_t_gt, v_pivot_gt, 
                               add_noise=True, outlier_prob=0.0, outlier_magnitude=50.0):
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    logging.info(f"Generating {num_samples} samples into {output_dir}")
    
    generated_files = []
    outlier_count = 0
    
    for i in range(num_samples):
        # 1. Generate random rotation for the tool
        # We want to cover the sphere roughly
        axis = np.random.randn(3)
        axis /= np.linalg.norm(axis)
        
        # Using full random quaternion for robust coverage
        rot = Rotation.random()
        R = rot.as_matrix()

        # 2. Compute clean position
        # Constraint: R * v_t + p = v_pivot
        # => p = v_pivot - R * v_t
        p_clean = v_pivot_gt - R @ v_t_gt
        
        T_clean = np.eye(4)
        T_clean[:3, :3] = R
        T_clean[:3, 3] = p_clean
        
        # 3. Apply Noise (Right-hand side error model)
        if add_noise:
            T_meas = apply_noise(T_clean,
                                 TRACKER_NOISE_POS_MEAN, TRACKER_NOISE_POS_STD,
                                 TRACKER_NOISE_ROT_MEAN, TRACKER_NOISE_ROT_STD)
        else:
            T_meas = T_clean.copy()
            
        # 4. Outliers
        if outlier_prob > 0 and random.random() < outlier_prob:
            # Huge shift in position to simulate bad tracking
            outlier_offset = np.random.randn(3)
            outlier_offset /= np.linalg.norm(outlier_offset) 
            outlier_offset *= outlier_magnitude
            
            # Apply to translation directly
            T_meas[:3, 3] += outlier_offset
            
            outlier_count += 1
            
        # Save to file
        filename = f"O_from_D_{i+1:02d}.txt"
        filepath = os.path.join(output_dir, filename)
        np.savetxt(filepath, T_meas, fmt='%.10f')
        generated_files.append(filepath)

    logging.info(f"Generated {len(generated_files)} files (Outliers: {outlier_count})")

def generate_pivot_calibration_data():
    # Ground Truth
    v_t_gt = np.array([0.0, 0.0, 150.0]) # Device Tip in Device Frame
    v_pivot_gt = np.array([200.0, 230.0, -50.0]) # Pivot Point in Optical Tracker Frame
    
    # Save Ground Truth
    np.savetxt(os.path.join(OUTPUT_DIR, "GT_v_t.txt"), v_t_gt)
    np.savetxt(os.path.join(OUTPUT_DIR, "GT_v_pivot.txt"), v_pivot_gt)

    # 1. Clean Data (No noise, No outliers) - verify algorithms theoretically
    # Actually, let's make "Clean" usually mean "Small normal noise" in experimental context, 
    # but "Perfect" means "No noise". 
    # The existing test had "clean" (noise but no outliers) and "outliers" (noise + outliers).
    # Let's align with that.
    
    # "Clean" Dataset: Normal noise, 0 outliers
    CLEAN_DIR = os.path.join(OUTPUT_DIR, "clean")
    generate_pivot_data_subset(CLEAN_DIR, num_samples=50, 
                               v_t_gt=v_t_gt, v_pivot_gt=v_pivot_gt,
                               add_noise=True, outlier_prob=0.0)

    # "Outlier" Dataset: Normal noise + outliers
    OUTLIER_DIR = os.path.join(OUTPUT_DIR, "outliers")
    generate_pivot_data_subset(OUTLIER_DIR, num_samples=50, 
                               v_t_gt=v_t_gt, v_pivot_gt=v_pivot_gt,
                               add_noise=True, outlier_prob=0.1, outlier_magnitude=30.0)

if __name__ == "__main__":
    generate_pivot_calibration_data()
