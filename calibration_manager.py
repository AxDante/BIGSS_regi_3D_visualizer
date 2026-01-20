import os
import logging
import numpy as np
import test_calibration
from transformable_object import TransformableObject
import geo.core as kg
from custom_vector import CustomVector

class CalibrationManager:
    def __init__(self, visualizer):
        self.viz = visualizer
        self.data = []  # List of 4x4 matrices
        self.results = {}
        self.active_ghost_name = None # Name of the currently active ghost object
        self.target_transform_name = None # "O_from_D"
        self.v_t = None
        self.visible = True

    def load_data(self, folder_path):
        if not os.path.exists(folder_path):
            return 0
        self.data = test_calibration.load_transforms(folder_path)
        return len(self.data)

    def run_calibration(self, transform_name, threshold=2.0):
        if not self.data or len(self.data) < 3:
            return None, None, 0.0

        self.target_transform_name = transform_name
        
        # Run Solver
        v_t, v_pivot, rmse, inliers = test_calibration.solve_pivot_calibration_ransac(
            self.data, threshold=threshold
        )
        
        if v_t is None:
            return None, None, 0.0

        self.results = {
            'v_t': v_t,
            'v_pivot': v_pivot,
            'rmse': rmse,
            'inliers': inliers
        }
        self.v_t = v_t
        
        # Register v_pivot immediately (permanent visualization until cleared)
        self._register_pivot(transform_name, v_pivot)
        
        # Reset preview state
        self._clear_active_ghost()
        
        return v_t, v_pivot, rmse

    def _register_pivot(self, transform_name, v_pivot):
        target_obj = self.viz.transform_map.get(transform_name)
        if not target_obj or not target_obj.parent:
            return
        
        parent_obj = target_obj.parent
        
        # Update/Add Pivot Landmark
        if not getattr(parent_obj, 'landmarks', None):
            parent_obj.landmarks = {'labels': [], 'points': []}
            
        if 'Pivot' in parent_obj.landmarks['labels']:
            idx = parent_obj.landmarks['labels'].index('Pivot')
            parent_obj.landmarks['points'][idx] = v_pivot
        else:
            parent_obj.landmarks['labels'].append('Pivot')
            parent_obj.landmarks['points'].append(v_pivot)
            
        # Create v_pivot vector if needed
        vec_name = "v_pivot"
        existing_vec = next((v for v in self.viz.custom_vectors if v.name == vec_name), None)
        
        if not existing_vec:
            vec = CustomVector(vec_name, parent_obj.name, "Pivot", parent_obj.name, 
                               self.viz.plotter, {'color': 'yellow'}, self.viz.object_map)
            self.viz.custom_vectors.append(vec)

    def _clear_active_ghost(self):
        """Robustly removes the current ghost object and its artifacts."""
        if not self.active_ghost_name:
            return

        name = self.active_ghost_name
        
        # 1. Remove Object
        obj = self.viz.object_map.get(name)
        if obj:
            if obj.parent:
                obj.parent.children.remove(obj)
            for actor in obj.frame_actors:
                self.viz.plotter.remove_actor(actor)
            if obj.origin_label_actor:
                self.viz.plotter.remove_actor(obj.origin_label_actor)

            # Cleanup internal vector actors (managed by TransformableObject)
            if hasattr(obj, 'vector_actor') and obj.vector_actor:
                self.viz.plotter.remove_actor(obj.vector_actor)
            if hasattr(obj, 'vector_label_actor') and obj.vector_label_actor:
                self.viz.plotter.remove_actor(obj.vector_label_actor)
            
            if obj in self.viz.objects:
                self.viz.objects.remove(obj)
            del self.viz.object_map[name]
        
        # 2. Remove Transform Config (Green Arrow)
        # Iterate to ensure we remove ALL pointing to this ghost (orphan cleanup)
        transforms_to_remove = [t for t in self.viz.config.get('transforms', []) if t.get('child') == name]
        
        for t_conf in transforms_to_remove:
            self.viz.config['transforms'].remove(t_conf)
            t_name = t_conf['name']
            if hasattr(self.viz, 'dependent_actors') and t_name in self.viz.dependent_actors:
                cache = self.viz.dependent_actors[t_name]
                if cache['arrow']: self.viz.plotter.remove_actor(cache['arrow'])
                if cache['label']: self.viz.plotter.remove_actor(cache['label'])
                del self.viz.dependent_actors[t_name]

        # 3. Remove Tip Vector (Yellow Arrow)
        vec_name = f"v_tip_{name}"
        vec = next((v for v in self.viz.custom_vectors if v.name == vec_name), None)
        if vec:
            if vec.actor: self.viz.plotter.remove_actor(vec.actor)
            if vec.label_actor: self.viz.plotter.remove_actor(vec.label_actor)
            self.viz.custom_vectors.remove(vec)
            
        self.active_ghost_name = None

    def preview_pose(self, index):
        """Lazy creation of a single ghost pose."""
        if not self.data or index < 0 or index >= len(self.data):
            return

        # Clear previous one first
        self._clear_active_ghost()
        
        if not self.visible:
            self.viz.update_scene()
            self.viz.plotter.render()
            return

        target_obj = self.viz.transform_map.get(self.target_transform_name)
        if not target_obj: return
        parent_obj = target_obj.parent
        child_name = target_obj.name
        
        # Create NEW ghost
        ghost_name = f"{child_name}_Ghost" # Single reused name prefix logic, but unique instance
        pose_matrix = self.data[index]
        
        # 1. Object
        ghost_obj = TransformableObject(ghost_name, f"{target_obj.abbreviation}_{index}", self.viz.plotter, movable=False)
        ghost_obj.parent = parent_obj
        parent_obj.children.append(ghost_obj)
        self.viz.objects.append(ghost_obj)
        self.viz.object_map[ghost_name] = ghost_obj
        ghost_obj.local_transform = kg.FrameTransform(pose_matrix)
        
        # 2. Transform Config (Green Arrow)
        t_name = f"{parent_obj.abbreviation}_from_{ghost_obj.abbreviation}"
        t_conf = {
            'name': t_name,
            'parent': parent_obj.name,
            'child': ghost_name,
            'type': 'dependent',
            'dynamic': True
        }
        self.viz.config['transforms'].append(t_conf)
        
        # 3. Vector (Yellow Arrow)
        if self.v_t is not None:
             # Add Landmark
            ghost_obj.landmarks = {'labels': ['Tip'], 'points': [self.v_t]}
            vec_name = f"v_tip_{ghost_name}"
            vec = CustomVector(vec_name, ghost_name, "Tip", ghost_name, 
                               self.viz.plotter, {'color': 'yellow'}, self.viz.object_map)
            self.viz.custom_vectors.append(vec)
            
        self.active_ghost_name = ghost_name
        self.viz.update_scene()
        self.viz.plotter.render()

    def toggle_visibility(self, visible):
        self.visible = visible
        
        # Pivot Toggle
        pivot = self.viz.object_map.get("PivotPoint")
        if pivot: pivot.set_visible(visible)
        
        v_pivot = next((v for v in self.viz.custom_vectors if v.name == "v_pivot"), None)
        if v_pivot:
            if v_pivot.actor: v_pivot.actor.SetVisibility(visible)
            if v_pivot.label_actor: v_pivot.label_actor.SetVisibility(visible)
            
        # Reshow active ghost if enabled, or hide/clear
        if self.active_ghost_name:
            obj = self.viz.object_map.get(self.active_ghost_name)
            if obj:
                obj.set_visible(visible)
                
                # Handle Green Arrow manually since it's dependent
                t_conf = next((t for t in self.viz.config.get('transforms', []) if t.get('child') == self.active_ghost_name), None)
                if t_conf:
                    t_name = t_conf['name']
                    if hasattr(self.viz, 'dependent_actors') and t_name in self.viz.dependent_actors:
                        cache = self.viz.dependent_actors[t_name]
                        if cache['arrow']: cache['arrow'].SetVisibility(visible)
                        if cache['label']: cache['label'].SetVisibility(visible)
                        
            # Handle Vector
            vec_name = f"v_tip_{self.active_ghost_name}"
            vec = next((v for v in self.viz.custom_vectors if v.name == vec_name), None)
            if vec:
                if vec.actor: vec.actor.SetVisibility(visible)
                if vec.label_actor: vec.label_actor.SetVisibility(visible)
                
        self.viz.plotter.render()
