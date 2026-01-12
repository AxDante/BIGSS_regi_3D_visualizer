
import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
import os
import logging

class CalibrationControlPanel:
    def __init__(self, visualizer):
        self.viz = visualizer
        self.root = tk.Tk()
        self.root.title("Pivot Calibration Control")
        self.root.geometry("400x500")
        
        # Handle closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.create_widgets()
        
    def on_close(self):
        self.viz.stop_event.set()
        
    def create_widgets(self):
        # 1. Data Selection Frame
        data_frame = ttk.LabelFrame(self.root, text="Data Selection", padding="10")
        data_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(data_frame, text="Select Data Folder:").pack(anchor=tk.W)
        
        path_frame = ttk.Frame(data_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        self.path_var = tk.StringVar()
        # Default to the test directory we observed earlier
        default_path = os.path.join(os.path.dirname(__file__), "test_files", "pivot_calibration", "optical_tracker")
        self.path_var.set(default_path)
        
        entry = ttk.Entry(path_frame, textvariable=self.path_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        btn_browse = ttk.Button(path_frame, text="...", width=3, command=self.browse_folder)
        btn_browse.pack(side=tk.LEFT)
        
        self.btn_load = ttk.Button(data_frame, text="Load Data", command=self.load_data)
        self.btn_load.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(data_frame, text="Ready", foreground="gray")
        self.status_label.pack(anchor=tk.W, pady=2)
        
        # 2. Calibration Controls
        calib_frame = ttk.LabelFrame(self.root, text="Calibration", padding="10")
        calib_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.btn_calibrate = ttk.Button(calib_frame, text="Estimate Pivot Calibration", command=self.run_calibration)
        self.btn_calibrate.pack(fill=tk.X, pady=5)
        
        # 3. Results Display
        result_frame = ttk.LabelFrame(self.root, text="Results", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.result_text = tk.Text(result_frame, height=10, width=40, state='disabled')
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
    def browse_folder(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            
    def load_data(self):
        folder = self.path_var.get()
        if not os.path.isdir(folder):
            self.status_label.config(text="Invalid folder path!", foreground="red")
            return
            
        self.status_label.config(text="Loading...", foreground="blue")
        self.root.update()
        
        try:
            self.viz.load_device_data(folder)
            count = len(self.viz.device_poses)
            self.status_label.config(text=f"Loaded {count} poses.", foreground="green")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            self.status_label.config(text=f"Error: {e}", foreground="red")
            
    def run_calibration(self):
        self.status_label.config(text="Calibrating...", foreground="blue")
        self.root.update()
        
        try:
            v_t, v_pivot, rmse = self.viz.perform_calibration()
            
            if v_t is not None:
                self.status_label.config(text="Calibration Successful", foreground="green")
                
                # Display Results
                res_str = f"RMSE: {rmse:.4f} mm\n\n"
                res_str += f"v_tip (Device Frame): \n{np.array2string(v_t, precision=3, suppress_small=True)}\n\n"
                res_str += f"v_pivot (Optical Frame): \n{np.array2string(v_pivot, precision=3, suppress_small=True)}\n"
                
                self.result_text.config(state='normal')
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, res_str)
                self.result_text.config(state='disabled')
            else:
                self.status_label.config(text="Calibration Failed", foreground="red")
                
        except Exception as e:
            logging.error(f"Error during calibration: {e}")
            self.status_label.config(text=f"Error: {e}", foreground="red")
