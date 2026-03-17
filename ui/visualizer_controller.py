from __future__ import annotations

import time
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, Property


class VisualizerController(QObject):
    statusChanged = Signal()
    listsChanged = Signal()
    selectionChanged = Signal()
    framesChanged = Signal()

    def __init__(self, visualizer):
        super().__init__()
        self._viz = visualizer
        self._status_text = "Ready"
        self._transform_names = []
        self._vector_names = []
        self._plane_names = []
        self._pose_names = []
        self._frames = []
        self._selected_transform = ""
        self._tx = 0.0
        self._ty = 0.0
        self._tz = 0.0
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self._chain = ""
        self._matrix_text = ""
        self._can_edit = False
        self._last_sync = 0.0

        self.refresh_lists()

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property('QStringList', notify=listsChanged)
    def transformNames(self):
        return self._transform_names

    @Property('QStringList', notify=listsChanged)
    def vectorNames(self):
        return self._vector_names

    @Property('QStringList', notify=listsChanged)
    def planeNames(self):
        return self._plane_names

    @Property('QStringList', notify=listsChanged)
    def poseNames(self):
        return self._pose_names

    @Property('QVariantList', notify=framesChanged)
    def frames(self):
        return self._frames

    @Property(str, notify=selectionChanged)
    def selectedTransform(self) -> str:
        return self._selected_transform

    @Property(float, notify=selectionChanged)
    def tx(self) -> float:
        return self._tx

    @Property(float, notify=selectionChanged)
    def ty(self) -> float:
        return self._ty

    @Property(float, notify=selectionChanged)
    def tz(self) -> float:
        return self._tz

    @Property(float, notify=selectionChanged)
    def roll(self) -> float:
        return self._roll

    @Property(float, notify=selectionChanged)
    def pitch(self) -> float:
        return self._pitch

    @Property(float, notify=selectionChanged)
    def yaw(self) -> float:
        return self._yaw

    @Property(str, notify=selectionChanged)
    def chain(self) -> str:
        return self._chain

    @Property(str, notify=selectionChanged)
    def matrixText(self) -> str:
        return self._matrix_text

    @Property(bool, notify=selectionChanged)
    def canEdit(self) -> bool:
        return self._can_edit

    @Slot()
    def refreshLists(self):
        self.refresh_lists()

    def refresh_lists(self):
        self._transform_names = [t["name"] for t in self._viz.config.get("transforms", [])]
        self._vector_names = [v.name for v in getattr(self._viz, "custom_vectors", [])]
        self._plane_names = [p.name for p in getattr(self._viz, "reference_planes", []) if getattr(p, "visible", True)]
        self._pose_names = []
        self.listsChanged.emit()
        self._build_frames()
        if not self._selected_transform and self._transform_names:
            self._selected_transform = self._transform_names[0]
            self._sync_selection()
            self.selectionChanged.emit()

    def _build_frames(self):
        frames = []
        for obj in self._viz.objects:
            if obj.name == "World":
                continue
            has_model = bool(obj.actor or obj.segmentation_actor or (obj.obj_type == "model"))
            has_landmarks = bool(obj.landmarks)
            show_frame = getattr(obj, "show_frame_actors", True)
            frames.append({
                "name": obj.name,
                "abbr": obj.abbreviation or "",
                "visible": bool(getattr(obj, "visible", True)),
                "hasModel": has_model,
                "showModel": bool(getattr(obj, "show_model", False)),
                "hasLandmarks": has_landmarks,
                "showLandmarks": bool(getattr(obj, "show_landmarks", False)),
                "showFrame": show_frame,
            })
        self._frames = frames
        self.framesChanged.emit()

    @Slot(str)
    def setSelectedTransform(self, name: str):
        if name == self._selected_transform:
            return
        self._selected_transform = name
        self._sync_selection()
        self.selectionChanged.emit()

    def _find_transform_config(self, name: str):
        for t in self._viz.config.get("transforms", []):
            if t.get("name") == name:
                return t
        return None

    def _get_active_object(self):
        t_config = self._find_transform_config(self._selected_transform)
        if not t_config:
            return None, None
        if t_config.get("type") == "dependent":
            return None, t_config
        return self._viz.object_map.get(t_config.get("child")), t_config

    def _sync_selection(self):
        obj, t_config = self._get_active_object()
        if obj:
            self._tx = float(obj.local_transform.t[0])
            self._ty = float(obj.local_transform.t[1])
            self._tz = float(obj.local_transform.t[2])
            euler = obj.get_rotation_euler()
            self._roll = float(euler[0])
            self._pitch = float(euler[1])
            self._yaw = float(euler[2])
            self._chain = obj.get_kinematic_chain_string()
            self._matrix_text = obj.get_transform_str()
            self._can_edit = bool(obj.movable and not obj.is_subscribed and not obj.constraint_expression)
        elif t_config:
            parent = self._viz.object_map.get(t_config.get("parent"))
            child = self._viz.object_map.get(t_config.get("child"))
            if parent and child:
                matrix = np.linalg.inv(parent.global_transform.data) @ child.global_transform.data
                self._tx = float(matrix[0, 3])
                self._ty = float(matrix[1, 3])
                self._tz = float(matrix[2, 3])
                self._roll = 0.0
                self._pitch = 0.0
                self._yaw = 0.0
                self._chain = f"{t_config.get('parent')}_from_{t_config.get('child')}"
                self._matrix_text = f"{self._chain}:\n{matrix}"
                self._can_edit = False
            else:
                self._tx = self._ty = self._tz = 0.0
                self._roll = self._pitch = self._yaw = 0.0
                self._chain = ""
                self._matrix_text = ""
                self._can_edit = False
        else:
            self._tx = self._ty = self._tz = 0.0
            self._roll = self._pitch = self._yaw = 0.0
            self._chain = ""
            self._matrix_text = ""
            self._can_edit = False

    @Slot()
    def syncState(self):
        now = time.time()
        if now - self._last_sync < 0.2:
            return
        self._last_sync = now
        self._build_frames()
        self._sync_selection()
        self.selectionChanged.emit()

    @Slot(str, float)
    def setTranslation(self, axis: str, value: float):
        obj, _ = self._get_active_object()
        if not obj:
            return
        axis_map = {"x": 0, "y": 1, "z": 2}
        if axis.lower() not in axis_map:
            return
        obj.set_translation(axis_map[axis.lower()], float(value), self._viz.transform_map)
        self._sync_selection()
        self.selectionChanged.emit()

    @Slot(str, float)
    def setRotation(self, axis: str, value: float):
        obj, _ = self._get_active_object()
        if not obj:
            return
        axis_map = {"roll": 0, "pitch": 1, "yaw": 2}
        key = axis.lower()
        if key not in axis_map:
            return
        obj.set_rotation_euler(axis_map[key], float(value), self._viz.transform_map)
        self._sync_selection()
        self.selectionChanged.emit()

    @Slot(str, bool)
    def setFrameVisible(self, name: str, visible: bool):
        obj = self._viz.object_map.get(name)
        if not obj:
            return
        obj.show_frame_actors = bool(visible)
        if visible:
            for actor in obj.frame_actors:
                actor.VisibilityOn()
            if obj.origin_label_actor:
                obj.origin_label_actor.VisibilityOn()
        else:
            for actor in obj.frame_actors:
                actor.VisibilityOff()
            if obj.origin_label_actor:
                obj.origin_label_actor.VisibilityOff()
        obj.update_transform(self._viz.transform_map)
        self._build_frames()

    @Slot(str, bool)
    def setModelVisible(self, name: str, visible: bool):
        obj = self._viz.object_map.get(name)
        if not obj:
            return
        obj.set_show_model(bool(visible))
        self._build_frames()

    @Slot(str, bool)
    def setLandmarksVisible(self, name: str, visible: bool):
        obj = self._viz.object_map.get(name)
        if not obj:
            return
        obj.set_show_landmarks(bool(visible))
        self._build_frames()

    @Slot(str, bool)
    def setObjectVisible(self, name: str, visible: bool):
        obj = self._viz.object_map.get(name)
        if not obj:
            return
        obj.set_visible(bool(visible))
        self._build_frames()

    @Slot()
    def toggleLogging(self):
        try:
            self._viz.toggle_logging()
            self._status_text = "Toggled logging"
        except Exception:
            self._status_text = "Logging toggle failed"
        self.statusChanged.emit()

    @Slot()
    def toggleRecording(self):
        try:
            self._viz.toggle_recording()
            self._status_text = "Toggled recording"
        except Exception:
            self._status_text = "Recording toggle failed"
        self.statusChanged.emit()
