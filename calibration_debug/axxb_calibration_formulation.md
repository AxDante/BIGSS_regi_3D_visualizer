# AXXB Calibration Formulation

## 1. Problem Description
We aim to calibrate the static coordinate transformations in a robot-assisted surgery setup.
The system consists of:
*   **Robot Base ($R$)**: The fixed base frame of the robot.
*   **Robot End-Effector ($Re$)**: The moving tip of the robot. The robot kinematics provide the transform **$R\_from\_Re$**.
*   **Robot Marker ($Rm$)**: An optical marker rigidly attached to the device on the End-Effector.
*   **Optical Tracker ($O$)**: The camera system observing data. It provides the transform **$O\_from\_Rm$**.
*   **Phantom Marker ($Pm$)**: A reference marker (potentially static or used as another reference). Tracker provides **$O\_from\_Pm$**.

## 2. Goals
We want to estimate two **static** transforms using a set of collected poses:
1.  **$X = Re\_from\_Rm$**: The transform from the Robot End-Effector to the attached Robot Marker. (The "Hand-Eye" or "Flange-to-Tool" equivalent).
2.  **$Y = O\_from\_R$** (or its inverse $R\_from\_O$): The transform between the Optical Tracker and the Robot Base.

## 3. Mathematical Derivation ($AX = XB$)

For any recorded pose $i$, we have the closed kinematic chain:
$$ R\_from\_Re_i \cdot Re\_from\_Rm = R\_from\_O \cdot O\_from\_Rm_i $$
Let:
*   $T_{base} = R\_from\_Re_i$ (Robot kinematics)
*   $X = Re\_from\_Rm$ (Unknown Calibration 1)
*   $Y_{inv} = R\_from\_O$ (Unknown Calibration 2)
*   $T_{cam} = O\_from\_Rm_i$ (Optical Tracker data)

Equation:
$$ T_{base} \cdot X = Y_{inv} \cdot T_{cam} $$

Since $X$ and $Y_{inv}$ are constant, consider two poses $i$ and $j$:
$$ T_{base,i} \cdot X \cdot T_{cam,i}^{-1} = Y_{inv} = T_{base,j} \cdot X \cdot T_{cam,j}^{-1} $$
$$ T_{base,j}^{-1} \cdot T_{base,i} \cdot X = X \cdot T_{cam,j}^{-1} \cdot T_{cam,i} $$
$$ (T_{base,j}^{-1} \cdot T_{base,i}) \cdot X = X \cdot (T_{cam,j}^{-1} \cdot T_{cam,i}) $$

This is the form **$A X = X B$**:
*   **$A_{ji}$**: Relative motion of the Robot End-Effector (from $j$ to $i$ in Robot frame? No, local frame).
    *   Let's check indices carefully.
    *   $A = Re\_from\_R_j \cdot R\_from\_Re_i = (R\_from\_Re_j)^{-1} \cdot R\_from\_Re_i$. This is the motion of the End-Effector *in the End-Effector frame* (assuming $X$ is on the right).
    *   **$A = Re_j\_from\_Re_i$**
*   **$B_{ji}$**: Relative motion of the Marker.
    *   $B = T_{cam,j}^{-1} \cdot T_{cam,i} = Rm\_from\_O_j \cdot O\_from\_Rm_i$.
    *   **$B = Rm_j\_from\_Rm_i$**

Constraint: **$A \cdot X = X \cdot B$**
Where $X = Re\_from\_Rm$.

## 4. Proposed Solution Strategy
We will implement `test_axxb_calibration.py` with the following steps:

1.  **Data Generation (Mock)**:
    *   Define true $X$ (`Re_from_Rm`) and $Y$ (`O_from_R`).
    *   Simulate random robot movements (`R_from_Re`).
    *   Compute simulated tracker observations (`O_from_Rm`) using the loop:
        $$ O\_from\_Rm = O\_from\_R \cdot R\_from\_Re \cdot Re\_from\_Rm $$
    *   Add noise to rotations and translations.

2.  **Solver Implementation**:
    *   **Pair Generation**: Create pairs of poses $(i, j)$ with sufficient rotation difference.
    *   **Rotation Solving (Park & Martin)**:
        *   Extract axis-angle vectors $k_A, \theta_A$ and $k_B, \theta_B$.
        *   Solve $R_X \cdot k_B = k_A$.
        *   Ideally $\theta_A \approx \theta_B$.
    *   **Translation Solving**:
        *   Using computed $R_X$, solve $(R_A - I)t_X = R_X t_B - t_A$.
    *   **Base Transform Solving**:
        *   Once $X$ is found, average $Y_{inv} = T_{base} X T_{cam}^{-1}$ over all poses to find $R\_from\_O$.

3.  **Verification**:
    *   Report residual errors for $AX - XB$ (rotation and translation).
    *   Report error vs Ground Truth.

## 5. Notes on Frames
*   **Rm_from_Pm**: The user mentioned this as a task. If $Pm$ is just another marker tracked by $O$ ($O\_from\_Pm$), then:
    *   $Rm\_from\_Pm = (O\_from\_Rm)^{-1} \cdot O\_from\_Pm$.
    *   This is purely an optical tracker calculation, unless we imply a *static* relationship. If they are moving independently, this is just a calculation per frame. If $Pm$ is static in $O$, calibration is not needed beyond tracking.
    *   We will assume the core task is estimating the **system calibrations** ($X$ and $Y$).
