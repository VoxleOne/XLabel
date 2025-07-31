from PySide6.QtCore import Signal, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from .base_panel import BasePanel

class PolygonPanel(BasePanel):
    # --- THE FIX: Signal is now argument-free for consistency ---
    new_annotation = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations = []
        self._active_polygon = []
        self._cursor_pos = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def setVisible(self, visible):
        super().setVisible(visible)
        if not visible:
            self._active_polygon = []
            self._cursor_pos = None

    def get_annotations(self):
        return {
            "completed": self._annotations,
            "active": self._active_polygon,
            "cursor_pos": self._cursor_pos
        }

    # --- THE FIX: This method is no longer needed with the new architecture ---
    # def add_annotation(self, polygon): ...

    # --- THE FIX: A new private method to handle finishing a polygon ---
    def _finalize_polygon(self):
        if self._active_polygon and len(self._active_polygon) > 2:
            self._annotations.append(list(self._active_polygon))
            self.new_annotation.emit()
        self._active_polygon = []
        self._cursor_pos = None
        self.parent().update()

    def delete_annotation(self, index):
        if 0 <= index < len(self._annotations):
            self._annotations.pop(index)
            return True
        return False

    def clear_annotations(self):
        self._annotations.clear()
        self._active_polygon = []
        if self.parent():
            self.parent().update()

    def mousePressEvent(self, event):
        image_pos = self.parent().map_to_image(event.pos())
        if not image_pos: return

        if event.button() == Qt.LeftButton:
            self._active_polygon.append(image_pos)
            self.parent().update()
        elif event.button() == Qt.RightButton:
            self._finalize_polygon()

    def mouseMoveEvent(self, event):
        self._cursor_pos = self.parent().map_to_image(event.pos())
        self.parent().update()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._finalize_polygon()
        elif event.key() == Qt.Key_Escape:
            self._active_polygon = []
            self.parent().update()
        else:
            super().keyPressEvent(event)