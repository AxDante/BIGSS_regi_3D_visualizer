
import logging
import threading
import time
import os
import yaml
import numpy as np
import pyvista as pv
from vtkmodules.vtkCommonColor import vtkNamedColors

import geo.core as kg
from transformable_object import TransformableObject
from calibration_control_panel import CalibrationControlPanel
import test_calibration

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CalibrationVisualizer:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config(config_path)
        
        self.plotter = pv.Plotter()
        self.objects = []
        self.object_map = {}
        self.transform_map = {} # Map 'name' -> FrameTransform
        
        self.device_poses = []  # List of dicts: {'name': str, 'transform': FrameTransform, 'obj': TransformableObject}
        self.v_tip_actors = []  # List of actors for tool tip vectors
        
        self.control_panel = CalibrationControlPanel(self)
        
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        # Settings
        self.show_device_frames = True
        self.adjustable_grid = True # Assuming this is a default setting you might want
        self.screenshot_path = os.path.join(os.getcwd(), "screenshots") # Default screenshot path
        self.logging_path = os.path.join(os.getcwd(), "logs") # Default logs path
        self.recording_dir = self.config.get('recording_dir', "visualizer_outputs/recordings")

        # Initialize Scene
        self._setup_scene()
        
    def load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
            
    def _setup_scene(self):
        # 1. Create Base Objects (World, OpticalTracker, etc.)
        world = TransformableObject("World", "W", self.plotter, movable=False)
        self._add_object(world)
        
        for frame_conf in self.config.get('frames', []):
            # Exclude dummy pass keys
            if 'name' not in frame_conf: continue
            
            obj = TransformableObject(
                name=frame_conf['name'],
                abbreviation=frame_conf['abbreviation'],
                plotter=self.plotter,
                movable=frame_conf.get('movable', True)
            )
            self._add_object(obj)
            
        # 2. Establish Hierarchy & Initial Transforms
        self._link_objects()
        self._apply_initial_transforms()
        
        self.plotter.show_axes()
        self.plotter.show_grid()
        self.plotter.view_isometric()

    def _add_object(self, obj):
        self.objects.append(obj)
        self.object_map[obj.name] = obj
        
    def _link_objects(self):
        # Link parents based on config
        for t_conf in self.config.get('transforms', []):
            parent = self.object_map.get(t_conf['parent'])
            child = self.object_map.get(t_conf['child'])
            if parent and child:
                child.parent = parent
                parent.children.append(child)
                
    def _apply_initial_transforms(self):
        # Apply initial transforms from config
        for t_conf in self.config.get('transforms', []):
            child = self.object_map.get(t_conf['child'])
            if child:
                if 'initial_transform' in t_conf:
                    data = np.array(t_conf['initial_transform'])
                    child.local_transform = kg.FrameTransform(data)
                elif 'path' in t_conf:
                    # Load from file if specified
                    pass # TODO: Implement if needed, for O_from_D usually loaded dynamically

    def load_device_data(self, folder_path):
        """Loads O_from_D transforms from folder and creates visual objects."""
        logging.info(f"Loading data from {folder_path}...")
        
        # Clear existing dynamic device objects
        self._clear_device_poses()
        
        # Load transforms using the helper from test_calibration
        transforms = test_calibration.load_transforms(folder_path)
        if not transforms:
            logging.warning("No valid transforms found.")
            return

        parent = self.object_map.get('OpticalTracker')
        if not parent:
            logging.error("OpticalTracker frame not found in scene.")
            return

        for i, T in enumerate(transforms):
            name = f"Device_{i+1:02d}"
            
            # Create a lightweight object (or full TransformableObject)
            # For 50 objects, full TransformableObject is fine.
            obj = TransformableObject(name, f"D{i+1}", self.plotter, movable=False)
            obj.parent = parent
            parent.children.append(obj)
            
            # Set Local Transform (O_from_D)
            # Note: TransformableObject.local_transform expects kg.FrameTransform
            obj.local_transform = kg.FrameTransform(T)
            
            # Reduce axis scale for individual device frames to avoid clutter
            obj.set_frame_scale(15.0) 
            obj.set_label_size(0) # Hide labels to reduce clutter
            
            self._add_object(obj)
            self.device_poses.append({
                'name': name,
                'transform': T, # Numpy array
                'obj': obj
            })
            
        logging.info(f"Loaded {len(self.device_poses)} device poses.")
        self.update_scene()
        
    def _clear_device_poses(self):
        """Removes previously loaded device objects."""
        for item in self.device_poses:
            obj = item['obj']
            # Hide/Remove actors
            # This is a simplified removal, ideally TransformableObject should have cleanup
            if obj.parent:
                obj.parent.children.remove(obj)
            
            # Hide actors (rudimentary cleanup)
            for actor in obj.frame_actors:
                self.plotter.remove_actor(actor)
            if obj.origin_label_actor:
                self.plotter.remove_actor(obj.origin_label_actor)
            
            if obj.name in self.object_map:
                del self.object_map[obj.name]
            if obj in self.objects:
                self.objects.remove(obj)
                
        self.device_poses = []
        
        # Clear v_tip lines
        for actor in self.v_tip_actors:
            self.plotter.remove_actor(actor)
        self.v_tip_actors = []

    def perform_calibration(self):
        """Runs the calibration and visualizes results."""
        if not self.device_poses:
            logging.warning("No data loaded.")
            return None, None, 0.0

        transforms = [item['transform'] for item in self.device_poses]
        
        # 1. Run RANSAC Solver
        # Using parameters that were effective in verification
        v_t, v_pivot, rmse, inliers = test_calibration.solve_pivot_calibration_ransac(
            transforms, threshold=2.0
        )
        
        if v_t is None:
            logging.error("Calibration failed.")
            return None, None, 0.0
            
        # 2. Update Pivot Point Object
        pivot_obj = self.object_map.get('PivotPoint')
        if pivot_obj and pivot_obj.parent:
            # Pivot v_pivot is in OpticalTracker frame (O_from_P)
            # We can set its local transform directly relative to OpticalTracker
            # Construct transform from translation v_pivot (rotation identity)
            T_pivot = np.eye(4)
            T_pivot[:3, 3] = v_pivot
            pivot_obj.local_transform = kg.FrameTransform(T_pivot)
            
            # Add a sphere actor to highlight it if not present
            if not getattr(pivot_obj, 'custom_actor', None):
                sphere = pv.Sphere(radius=2.0, center=(0,0,0)) # Local origin
                # We need to act carefully, best to rely on visualizer update loop
                # or just let the frame axes show the point.
                # Let's add a custom sphere actor to the object if possible?
                # Or just add to plotter directly using global transform.
                pass 
            
        # 3. Visualize v_tip lines
        # Remove old lines
        for actor in self.v_tip_actors:
            self.plotter.remove_actor(actor)
        self.v_tip_actors = []
        
        # Draw lines: Start at Device Origin, End at Device Origin + R * v_t
        # Actually, simpler: Start at Device Origin, End at Pivot (ideally)
        # But to visualize ERROR, we should draw the ESTIMATED tip location for each pose.
        # Tip_world = O_from_D * v_t_local
        
        # v_t is in Device Frame.
        # For each device pose T (O_from_D):
        # Tip_in_O = T * v_t (homogenous)
        
        for i, item in enumerate(self.device_poses):
            T = item['transform'] # O_from_D
            obj = item['obj']
            
            # Calculate tip position in Optical Frame
            # p_tip_O = R * v_t + p
            p_tip_O = T[:3, :3] @ v_t + T[:3, 3]
            
            # Draw line from Device Origin (p) to Tip (p_tip_O)
            start_point = T[:3, 3]
            end_point = p_tip_O
            
            # Color logic: Green if inlier, Red if outlier
            color = 'green' if inliers[i] else 'red'
            
            # We need to transform these points to WORLD frame for PyVista if we just add actor directly
            # Or attach to parent?
            # PyVista actors are usually in World coordinates.
            # Convert O coordinates to World coordinates.
            O_obj = self.object_map['OpticalTracker']
            W_from_O = O_obj.global_transform.data
            
            start_W = (W_from_O @ np.append(start_point, 1.0))[:3]
            end_W = (W_from_O @ np.append(end_point, 1.0))[:3]
            
            line = pv.Line(start_W, end_W)
            actor = self.plotter.add_mesh(line, color=color, line_width=2)
            self.v_tip_actors.append(actor)
            
        self.update_scene()
        return v_t, v_pivot, rmse

    def update_scene(self):
        """Updates all object transforms."""
        # Propagate Transforms
        # World is root
        world = self.object_map['World']
        world.update_transform(self.transform_map)

    def run(self):
        self.control_panel.root.update()
        self.plotter.show(interactive_update=True)
        
        while not self.stop_event.is_set():
            try:
                # 1. Update Control Panel
                self.control_panel.root.update()
                
                # 2. Update Scene Logic (if things moved dynamically)
                self.update_scene()
                
                # 3. Render
                self.plotter.update()
                
                # Sleep to prevent burning CPU
                time.sleep(0.01)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                break
                
        self.plotter.close()
        self.control_panel.root.destroy()

if __name__ == "__main__":
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), "configs", "config_pivot_calibration.yaml")
    viz = CalibrationVisualizer(CONFIG_FILE)
    viz.run()
