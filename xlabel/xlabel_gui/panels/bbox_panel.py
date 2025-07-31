from PySide6.QtCore import Signal, QPoint, QRect, Qt
from PySide6.QtGui import QKeyEvent
from .base_panel import BasePanel

class BoundingBoxPanel(BasePanel):
    # --- THE FIX: The signal no longer needs to carry data ---
    new_annotation = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations = []
        self._is_drawing = False
        self._start_pos = None
        self._current_rect = None
        self.setFocusPolicy(Qt.StrongFocus)

    def get_annotations(self):
        return {
            "completed": self._annotations,
            "active": self._current_rect
        }

    def delete_annotation(self, index):
        if 0 <= index < len(self._annotations):
            self._annotations.pop(index)
            return True
        return False

    def clear_annotations(self):
        self._annotations.clear()
        self._current_rect = None
        if self.parent():
            self.parent().update()

    def mousePressEvent(self, event):
        image_pos = self.parent().map_to_image(event.pos())
        if not image_pos: return
        if event.button() == Qt.LeftButton:
            self._is_drawing = True
            self._start_pos = image_pos
            self._current_rect = QRect(self._start_pos, self._start_pos)
            self.parent().update()

    def mouseMoveEvent(self, event):
        if not self._is_drawing: return
        image_pos = self.parent().map_to_image(event.pos())
        if not image_pos: return
        self._current_rect = QRect(self._start_pos, image_pos).normalized()
        self.parent().update()

    def mouseReleaseEvent(self, event):
        if not self._is_drawing or event.button() != Qt.LeftButton:
            return
        
        self._is_drawing = False
        if self._current_rect and self._current_rect.width() > 3 and self._current_rect.height() > 3:
            # --- THE FIX: Add the annotation directly and emit the simple signal ---
            self._annotations.append(self._current_rect)
            self._current_rect = None
            self.new_annotation.emit()
        else:
            self._current_rect = None
            self.parent().update()