import numpy as np
import pyvista as pv

class CustomVector:
    def __init__(self, name, parent_name, landmark_label, landmark_object_name, plotter, visual_settings, object_map):
        self.name = name
        self.parent_name = parent_name
        self.landmark_label = landmark_label
        self.landmark_object_name = landmark_object_name
        self.plotter = plotter
        self.object_map = object_map
        
        # Visual Settings
        self.visual_settings = visual_settings or {}
        self.color = self.visual_settings.get('color', 'yellow')
        self.opacity = self.visual_settings.get('opacity', 0.9)
        self.line_width = self.visual_settings.get('line_width', 5) # Not used for arrow mesh, but good to have
        self.label_size = self.visual_settings.get('label_size', 14)
        self.label_color = self.visual_settings.get('label_color', self.color)
        
        self.actor = None
        self.label_actor = None
        self.current_vector = None
        self.current_length = 0.0
        self.start_pos = None
        self.end_pos = None
        
    def update_transform(self, transform_map):
        """Alias for update to satisfy dependent interface."""
        # logging.info(f"[{self.name}] update_transform called")
        self.update(transform_map)

    def update(self, map_ignored=None):
        # 1. Get Start Position (Parent Origin)
        if self.parent_name == "World":
            start_pos = np.array([0.0, 0.0, 0.0])
        else:
            parent = self.object_map.get(self.parent_name)
            if not parent:
                return # Parent not found
            start_pos = parent.global_transform.t
            
        # 2. Get End Position (Landmark)
        lm_obj = self.object_map.get(self.landmark_object_name)
        if not lm_obj:
            return # Landmark object not found
            
        end_pos = lm_obj.get_landmark_world_position(self.landmark_label)
        
        if end_pos is None:
            # Landmark not found, hide actor if it exists
            if self.actor: self.actor.VisibilityOff()
            if self.label_actor: self.label_actor.VisibilityOff()
            return # Landmark not found
            
        # Check if changed
        if self.start_pos is not None and self.end_pos is not None:
            if np.allclose(start_pos, self.start_pos, atol=1e-5) and \
               np.allclose(end_pos, self.end_pos, atol=1e-5):
                return # No change
            
        # 3. Draw Vector
        vec = end_pos - start_pos
        length = float(np.linalg.norm(vec))
        
        if length < 1e-6:
            if self.actor: self.actor.VisibilityOff()
            if self.label_actor: self.label_actor.VisibilityOff()
            return
            
        direction = vec / length
        
        # Fixed dimensions for visibility
        fixed_shaft_radius = 1.0
        fixed_tip_radius = 3.0
        fixed_tip_length = 10.0
        
        arrow_mesh = pv.Arrow(start=start_pos, direction=direction, scale=length,
                        shaft_radius=fixed_shaft_radius/length,
                        tip_radius=fixed_tip_radius/length,
                        tip_length=fixed_tip_length/length)
                        
        if self.actor:
            # Update existing actor
            self.actor.mapper.dataset.copy_from(arrow_mesh)
            self.actor.VisibilityOn()
        else:
            # Create new
            self.actor = self.plotter.add_mesh(arrow_mesh, color=self.color, opacity=self.opacity, show_scalar_bar=False)
        
        # 4. Draw Label
        midpoint = (start_pos + end_pos) / 2
        
        # Recreate label (2D, less expensive)
        if self.label_actor:
            self.plotter.remove_actor(self.label_actor)
            
        self.label_actor = self.plotter.add_point_labels(
            [midpoint], [self.name],
            font_size=self.label_size, text_color=self.label_color,
            show_points=False, always_visible=True
        )
        
        self.current_vector = vec
        self.current_length = length
        self.start_pos = start_pos
        self.end_pos = end_pos
