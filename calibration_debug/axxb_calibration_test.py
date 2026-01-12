import numpy as np
import os
import glob
import logging
from scipy.spatial.transform import Rotation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def load_data(data_dir):
    """
    Loads robot and marker transforms from files.
    """
    # Subfolders
    robot_files = sorted(glob.glob(os.path.join(data_dir, "R_from_Re", "R_from_Re_*.txt")))
    marker_files = sorted(glob.glob(os.path.join(data_dir, "O_from_Rm", "O_from_Rm_*.txt")))
    # phantom_files = sorted(glob.glob(os.path.join(data_dir, "O_from_Pm", "O_from_Pm_*.txt"))) # Not used for now in AXXB
    
    if len(robot_files) != len(marker_files):
        raise ValueError(f"Mismatch in file counts: {len(robot_files)} robot vs {len(marker_files)} marker")
    
    robot_transforms = [np.loadtxt(f) for f in robot_files]
    marker_transforms = [np.loadtxt(f) for f in marker_files]
    
    # Load GT if available
    gt_X_path = os.path.join(data_dir, "GT_Re_from_Rm.txt")
    gt_Y_inv_path = os.path.join(data_dir, "GT_O_from_R.txt")
    
    gt_X = np.loadtxt(gt_X_path) if os.path.exists(gt_X_path) else None
    gt_Y_inv = np.loadtxt(gt_Y_inv_path) if os.path.exists(gt_Y_inv_path) else None
    
    return robot_transforms, marker_transforms, gt_X, gt_Y_inv

def compute_relative_motions(robot_transforms, marker_transforms, min_angle_deg=5.0):
    """
    Computes relative motions A (Robot) and B (Marker) for valid pairs.
    AX = XB
    A = Re_j_from_Re_i = inv(R_from_Re_j) * R_from_Re_i
    B = Rm_j_from_Rm_i = inv(O_from_Rm_j) * O_from_Rm_i
    """
    N = len(robot_transforms)
    A_motions = []
    B_motions = []
    
    pairs_count = 0
    skipped_count = 0
    
    # Stride of 1 (i, i+1) is usually sufficient if motion is continuous, 
    # but all-pairs or random pairs gives more data. 
    # Let's do all-pairs (i, j) where j > i
    for i in range(N):
        for j in range(i + 1, N):
            T_R_Re_i = robot_transforms[i]
            T_R_Re_j = robot_transforms[j]
            
            T_O_Rm_i = marker_transforms[i]
            T_O_Rm_j = marker_transforms[j]
            
            # A = inv(T_j) * T_i   (Motion in End-Effector Frame)
            A = np.linalg.inv(T_R_Re_j) @ T_R_Re_i
            
            # B = inv(T_j) * T_i   (Motion in Marker Frame)
            B = np.linalg.inv(T_O_Rm_j) @ T_O_Rm_i
            
            # Check rotation magnitude
            rot_A = Rotation.from_matrix(A[:3, :3])
            angle = rot_A.magnitude() # in radians
            
            if np.degrees(angle) < min_angle_deg:
                skipped_count += 1
                continue
                
            A_motions.append(A)
            B_motions.append(B)
            pairs_count += 1
            
    logging.info(f"Generated {pairs_count} motion pairs (skipped {skipped_count} small rotations).")
    return A_motions, B_motions

def solve_axxb(A_motions, B_motions):
    """
    Solves AX = XB for X (Re_from_Rm) using Park & Martin method.
    """
    n = len(A_motions)
    if n < 2:
        logging.error("Not enough motion pairs to solve.")
        return None
    
    # 1. Solve Rotation R_X
    # k_A = R_X * k_B
    # Minimize sum || R_X * k_B_i - k_A_i ||^2
    # This is an orthogonal Procrustes problem: R * Source = Target
    # Source = k_B, Target = k_A
    
    k_A_list = []
    k_B_list = []
    
    for i in range(n):
        R_A = A_motions[i][:3, :3]
        R_B = B_motions[i][:3, :3]
        
        # Extract axis-angle (scaled by angle? Park&Martin typically use Log(R)/(2*theta) * theta = Log(R)/2 ?)
        # Using scipy: magnitude * axis
        r_a = Rotation.from_matrix(R_A)
        r_b = Rotation.from_matrix(R_B)
        
        vec_a = r_a.as_rotvec()
        vec_b = r_b.as_rotvec()
        
        k_A_list.append(vec_a)
        k_B_list.append(vec_b)
        
    k_A_mat = np.array(k_A_list).T # 3 x N
    k_B_mat = np.array(k_B_list).T # 3 x N
    
    # Solve R_X * k_B = k_A
    # M = k_B * k_A^T
    M = k_B_mat @ k_A_mat.T
    U, S, Vt = np.linalg.svd(M)
    
    # R = V * U^T
    R_X = Vt.T @ U.T
    
    # Ensure determinant is +1 (rotation, not reflection)
    if np.linalg.det(R_X) < 0:
        logger.warning("Det(R) < 0, correcting reflection.")
        Vt[2, :] *= -1
        R_X = Vt.T @ U.T
        
    # 2. Solve Translation t_X
    # (R_A - I) * t_X = R_X * t_B - t_A
    # C * t_X = d
    
    C_list = []
    d_list = []
    
    for i in range(n):
        R_A = A_motions[i][:3, :3]
        t_A = A_motions[i][:3, 3]
        
        R_B = B_motions[i][:3, :3]
        t_B = B_motions[i][:3, 3]
        
        # C = R_A - I
        C = R_A - np.eye(3)
        
        # d = R_X * t_B - t_A
        d = R_X @ t_B - t_A
        
        C_list.append(C)
        d_list.append(d)
        
    C_full = np.vstack(C_list) # 3N x 3
    d_full = np.hstack(d_list) # 3N (flattened if hstack? no, d is vector)
    # Wait, d_list is list of 1D arrays (3,). hstack makes it (3N,).
    
    t_X, residuals, rank, s = np.linalg.lstsq(C_full, d_full, rcond=None)
    
    X_est = np.eye(4)
    X_est[:3, :3] = R_X
    X_est[:3, 3] = t_X
    
    return X_est

def solve_base_transform(robot_frames, marker_frames, X):
    """
    Computes Y (O_from_R) using the calculated X.
    Chain: T_cam = Y * T_base * X
    => Y = T_cam * inv(X) * inv(T_base)
    (O_from_R = O_from_Rm * Rm_from_Re * Re_from_R)
    """
    N = len(robot_frames)
    rotations = []
    translations = []
    
    X_inv = np.linalg.inv(X)
    
    for i in range(N):
        T_base = robot_frames[i]
        T_cam = marker_frames[i]
        
        # Y candidate: T_cam * inv(X) * inv(T_base)
        Y = T_cam @ X_inv @ np.linalg.inv(T_base)
        
        rotations.append(Rotation.from_matrix(Y[:3, :3]))
        translations.append(Y[:3, 3])
        
    # Average Translation
    avg_t = np.mean(translations, axis=0)
    
    # Average Rotation
    quats = np.array([r.as_quat() for r in rotations])
    
    # Align quaternions
    for i in range(1, N):
        if np.dot(quats[i], quats[0]) < 0:
            quats[i] = -quats[i]
            
    avg_quat = np.mean(quats, axis=0)
    avg_quat /= np.linalg.norm(avg_quat)
    avg_R = Rotation.from_quat(avg_quat).as_matrix()
    
    Y_final = np.eye(4)
    Y_final[:3, :3] = avg_R
    Y_final[:3, 3] = avg_t
    
    return Y_final

if __name__ == "__main__":
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "test_files", "axxb_calibration")
    
    try:
        # 1. Load Data
        logging.info("--- 1. Loading Data ---")
        R_frames, M_frames, gt_X, gt_Y = load_data(DATA_DIR)
        logging.info(f"Loaded {len(R_frames)} samples.")
        
        # 2. Compute Motions
        logging.info("--- 2. Computing Motions ---")
        A, B = compute_relative_motions(R_frames, M_frames)
        
        # 3. Solve X (Re_from_Rm)
        logging.info("--- 3. Solving AX=XB (Re_from_Rm) ---")
        X_est = solve_axxb(A, B)
        
        if X_est is None:
            logging.error("Calibration failed.")
            exit(1)
            
        logging.info(f"Estimated X (Re_from_Rm):\n{X_est}")
        if gt_X is not None:
             err_t = np.linalg.norm(X_est[:3, 3] - gt_X[:3, 3])
             R_diff = X_est[:3, :3] @ gt_X[:3, :3].T
             angle_err = np.degrees(Rotation.from_matrix(R_diff).magnitude())
             logging.info(f"Error vs GT -> Trans: {err_t:.4f} mm, Rot: {angle_err:.4f} deg")
             
        # 4. Solve Y (O_from_R)
        logging.info("--- 4. Solving Y (O_from_R) ---")
        Y_est = solve_base_transform(R_frames, M_frames, X_est)
        
        logging.info(f"Estimated Y (O_from_R):\n{Y_est}")
        if gt_Y is not None:
             err_t = np.linalg.norm(Y_est[:3, 3] - gt_Y[:3, 3])
             R_diff = Y_est[:3, :3] @ gt_Y[:3, :3].T
             angle_err = np.degrees(Rotation.from_matrix(R_diff).magnitude())
             logging.info(f"Error vs GT -> Trans: {err_t:.4f} mm, Rot: {angle_err:.4f} deg")


    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

