from PySide6.QtCore import Signal, QPoint, Qt
from PySide6.QtGui import QKeyEvent, QColor
from .base_panel import BasePanel

class KeypointsPanel(BasePanel):
    # --- THE FIX: Added the missing new_annotation signal ---
    new_annotation = Signal()
    # This signal will notify the UI to update if properties change
    properties_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        # State
        self._completed_sets = []
        self._active_points = []
        self._selected_point_idx = -1
        self._is_dragging = False
        self._cursor_pos = None

        # Configurable properties
        self.point_radius = 8
        self.point_color = QColor(255, 165, 0, 200)

    def get_annotations(self):
        # The viewer needs lists of points, not dicts
        completed_for_viewer = [item['points'] for item in self._completed_sets]
        
        return {
            "completed": completed_for_viewer,
            "active": self._active_points,
            "cursor_pos": self._cursor_pos,
            # Pass extra info for the painter
            "active_colors": [item['color'] for item in self._active_points],
            "completed_colors": [
                [p['color'] for p in s['points']] for s in self._completed_sets
            ],
            "point_radius": self.point_radius,
            "selected_point_idx": self._selected_point_idx
        }

    def clear_annotations(self):
        self._completed_sets.clear()
        self._active_points.clear()
        self._selected_point_idx = -1
        self._is_dragging = False
        if self.parent():
            self.parent().update()

    def delete_annotation(self, index):
        if 0 <= index < len(self._completed_sets):
            self._completed_sets.pop(index)
            return True
        return False

    def complete_set(self):
        if not self._active_points:
            return

        # Store a deep copy of points and their colors
        self._completed_sets.append({
            'points': [{'pos': p['pos'], 'color': p['color']} for p in self._active_points]
        })
        self._active_points.clear()
        self._selected_point_idx = -1
        self.new_annotation.emit() # Notify main window
        self.parent().update()

    def mousePressEvent(self, event):
        image_pos = self.parent().map_to_image(event.pos())
        if not image_pos: return

        if event.button() == Qt.LeftButton:
            # Check if clicking on an existing point to drag it
            for i, point_data in reversed(list(enumerate(self._active_points))):
                dist_sq = (point_data['pos'] - image_pos).manhattanLength()
                if dist_sq < self.point_radius * 2:
                    self._selected_point_idx = i
                    self._is_dragging = True
                    self.parent().update()
                    return

            # If not dragging, add a new point
            self._active_points.append({
                'pos': image_pos,
                'color': self.point_color
            })
            self._selected_point_idx = len(self._active_points) - 1
            self.parent().update()

    def mouseMoveEvent(self, event):
        self._cursor_pos = self.parent().map_to_image(event.pos())
        if not self._cursor_pos:
            self.parent().update()
            return

        if self._is_dragging and 0 <= self._selected_point_idx < len(self._active_points):
            self._active_points[self._selected_point_idx]['pos'] = self._cursor_pos
        
        self.parent().update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
        elif event.button() == Qt.RightButton:
            self.complete_set()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.complete_set()
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if 0 <= self._selected_point_idx < len(self._active_points):
                self._active_points.pop(self._selected_point_idx)
                self._selected_point_idx = -1
                self.parent().update()
        else:
            super().keyPressEvent(event)