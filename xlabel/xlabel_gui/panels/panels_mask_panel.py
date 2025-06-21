from PySide6.QtCore import Signal, QPoint, Qt
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QKeyEvent
from .base_panel import BasePanel

class MaskPanel(BasePanel):
    """A panel for creating and managing pixel-mask annotations."""
    # --- THE FIX: Signal is now argument-free for consistency with other panels ---
    new_annotation = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations = []
        self._active_mask = None
        self._is_drawing = False
        self._last_pos = None
        self.mode = 'brush'
        self.brush_size = 8
        self.brush_color = QColor(255, 0, 0, 70)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_brush_mode(self):
        self.mode = 'brush'

    def set_eraser_mode(self):
        self.mode = 'eraser'

    # --- THE FIX: This method now correctly manages its own state ---
    def finalize_annotation(self):
        if self._active_mask:
            self._annotations.append(self._active_mask)
            self._active_mask = None
            self.new_annotation.emit()
            self.parent().update_annotations_display()

    def _reset_mask(self):
        if self.parent() and hasattr(self.parent(), '_pixmap') and self.parent()._pixmap:
            image_size = self.parent()._pixmap.size()
            self._active_mask = QPixmap(image_size)
            self._active_mask.fill(Qt.transparent)
        else:
            self._active_mask = None
        self.parent().update_annotations_display()

    def get_annotations(self):
        return {
            "completed": self._annotations,
            "active": self._active_mask
        }

    def delete_annotation(self, index):
        if 0 <= index < len(self._annotations):
            self._annotations.pop(index)
            return True
        return False

    def clear_annotations(self):
        self._annotations.clear()
        self._active_mask = None
        if self.parent():
            self.parent().update()

    def _paint_stroke(self, to_pos: QPoint):
        if self._active_mask is None: return

        painter = QPainter(self._active_mask)
        
        if self.mode == 'eraser':
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            pen_color = QColor(0, 0, 0, 0)
            pen = QPen(pen_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(self.brush_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        
        painter.setPen(pen)
        if self._last_pos:
            painter.drawLine(self._last_pos, to_pos)
        else:
            painter.drawPoint(to_pos)
        painter.end()

        self._last_pos = to_pos
        self.parent().update()

    def mousePressEvent(self, event):
        image_pos = self.parent().map_to_image(event.pos())
        if not image_pos: return

        if event.button() == Qt.LeftButton:
            if self._active_mask is None:
                self._reset_mask()
            self._is_drawing = True
            self._last_pos = None
            self._paint_stroke(image_pos)
        
    def mouseMoveEvent(self, event):
        if not self._is_drawing:
            return
        image_pos = self.parent().map_to_image(event.pos())
        if not image_pos:
            return
        self._paint_stroke(image_pos)

    def mouseReleaseEvent(self, event):
        if self._is_drawing and event.button() == Qt.LeftButton:
            self._is_drawing = False
        elif event.button() == Qt.RightButton:
            self.finalize_annotation()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.finalize_annotation()
        else:
            super().keyPressEvent(event)