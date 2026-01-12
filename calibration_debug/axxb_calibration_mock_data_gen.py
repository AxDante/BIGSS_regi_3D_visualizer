import numpy as np
import os
import sys
from scipy.spatial.transform import Rotation

# Ensure output directory exists
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "test_files", "axxb_calibration")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def generate_axxb_data(num_samples=30):
    print(f"Generating {num_samples} samples into {OUTPUT_DIR}")

    # Define Subdirectories
    DIR_ROBOT = os.path.join(OUTPUT_DIR, "R_from_Re")
    DIR_MARKER_ROBOT = os.path.join(OUTPUT_DIR, "O_from_Rm")
    DIR_MARKER_PHANTOM = os.path.join(OUTPUT_DIR, "O_from_Pm")
    
    for d in [DIR_ROBOT, DIR_MARKER_ROBOT, DIR_MARKER_PHANTOM]:
        if not os.path.exists(d):
            os.makedirs(d)

    # 1. Define Static Ground Truth Transforms (Hidden unknowns we want to find)
    
    # Y_inv = R_from_O (Robot Base from Optical Tracker)
    # User given: O_from_R (which is Y). 
    # Translation O_from_R = [-1050, -3350, -1250]
    t_O_from_R_gt = np.array([-1050.0, -3350.0, -1250.0])
    # Rotation: Let's assume some fixed rotation between Tracker and Robot Base
    r_O_from_R_gt = Rotation.from_euler('xyz', [180, 0, 90], degrees=True) # Example setup
    T_O_from_R_gt = np.eye(4)
    T_O_from_R_gt[:3, :3] = r_O_from_R_gt.as_matrix()
    T_O_from_R_gt[:3, 3] = t_O_from_R_gt
    
    # X = Re_from_Rm (Robot End Effector to Robot Marker)
    # User given translation: [35, 14, -24]
    t_Re_from_Rm_gt = np.array([35.0, 14.0, -24.0])
    # Rotation: Marker is attached to end effector with some orientation
    r_Re_from_Rm_gt = Rotation.from_euler('xyz', [0, 45, 0], degrees=True)
    T_Re_from_Rm_gt = np.eye(4)
    T_Re_from_Rm_gt[:3, :3] = r_Re_from_Rm_gt.as_matrix()
    T_Re_from_Rm_gt[:3, 3] = t_Re_from_Rm_gt
    
    # Phantom Marker (Pm) - Static in World (or Tracker Frame)
    # Let's assume it's at some fixed position in Tracker Frame
    T_O_from_Pm_gt = np.eye(4)
    T_O_from_Pm_gt[:3, 3] = [100, 200, 500] 
    T_O_from_Pm_gt[:3, :3] = Rotation.from_euler('xyz', [10, 20, 30], degrees=True).as_matrix()

    # Save Ground Truth for verification
    np.savetxt(os.path.join(OUTPUT_DIR, "GT_O_from_R.txt"), T_O_from_R_gt)
    np.savetxt(os.path.join(OUTPUT_DIR, "GT_Re_from_Rm.txt"), T_Re_from_Rm_gt)

    # 2. Generate Random Robot Poses (R_from_Re)
    # To solve AX=XB well, we need good rotation diversity in the robot movement.
    
    # --- Noise Parameters ---
    # Optical Tracker Noise
    TRACKER_NOISE_POS_MEAN = np.array([5.0, 0.0, 0.0]) # mm
    TRACKER_NOISE_POS_STD = 1.0 # mm
    TRACKER_NOISE_ROT_MEAN = np.array([0.0, 0.0, 0.0]) # degrees
    TRACKER_NOISE_ROT_STD = 0.5 # degrees

    # Robot Noise (High precision)
    ROBOT_NOISE_POS_MEAN = np.array([0.0, 0.0, 0.0]) # mm
    ROBOT_NOISE_POS_STD = 0.1 # mm
    ROBOT_NOISE_ROT_MEAN = np.array([0.0, 0.0, 0.0]) # degrees
    ROBOT_NOISE_ROT_STD = 0.1 # degrees

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

    for i in range(num_samples):
        # Generate true robot pose
        t_R_from_Re_true = np.random.uniform(low=-200, high=200, size=3) + np.array([500, 0, 500])
        r_R_from_Re_true = Rotation.random()
        
        T_R_from_Re_true = np.eye(4)
        T_R_from_Re_true[:3, :3] = r_R_from_Re_true.as_matrix()
        T_R_from_Re_true[:3, 3] = t_R_from_Re_true
        
        # Apply Robot Noise
        T_R_from_Re_meas = apply_noise(T_R_from_Re_true, 
                                       ROBOT_NOISE_POS_MEAN, ROBOT_NOISE_POS_STD, 
                                       ROBOT_NOISE_ROT_MEAN, ROBOT_NOISE_ROT_STD)
        
        # Calculate True Tracker Observation for Robot Marker
        T_O_from_Rm_true = T_O_from_R_gt @ T_R_from_Re_true @ T_Re_from_Rm_gt
        
        # Apply Tracker Noise to Robot Marker
        T_O_from_Rm_meas = apply_noise(T_O_from_Rm_true,
                                       TRACKER_NOISE_POS_MEAN, TRACKER_NOISE_POS_STD,
                                       TRACKER_NOISE_ROT_MEAN, TRACKER_NOISE_ROT_STD)

        # Apply Tracker Noise to Phantom Marker (O_from_Pm)
        # Assuming Pm is static, but measured with noise each time
        T_O_from_Pm_meas = apply_noise(T_O_from_Pm_gt,
                                       TRACKER_NOISE_POS_MEAN, TRACKER_NOISE_POS_STD,
                                       TRACKER_NOISE_ROT_MEAN, TRACKER_NOISE_ROT_STD)
        
        # Save Files (Measured Data)
        np.savetxt(os.path.join(DIR_ROBOT, f"R_from_Re_{i+1:02d}.txt"), T_R_from_Re_meas)
        np.savetxt(os.path.join(DIR_MARKER_ROBOT, f"O_from_Rm_{i+1:02d}.txt"), T_O_from_Rm_meas)
        np.savetxt(os.path.join(DIR_MARKER_PHANTOM, f"O_from_Pm_{i+1:02d}.txt"), T_O_from_Pm_meas)
        
    print(f"Done. Generated 3 folders in {OUTPUT_DIR}")
if __name__ == "__main__":
    generate_axxb_data()
