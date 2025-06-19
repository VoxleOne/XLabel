from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from .base_panel import BasePanel

class BoundingBoxPanel(BasePanel):
    """Interactive panel for drawing bounding boxes."""
    
    # Signal -> Emits the final rectangle when drawing is complete
    new_annotation = Signal(QRect)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._drawing = False
        self._start_point = QPoint()
        self._current_rect = QRect()

    def paintEvent(self, event):
        """Draws the semi-transparent background and the in-progress rectangle."""
        painter = QPainter(self)
        # Transparent background
        painter.fillRect(self.rect(), Qt.transparent)
        
        # If we are currently drawing, draw the "rubber band" rectangle
        if self._drawing:
            pen = QPen(Qt.cyan, 2) # Use a distinct color for the drawing tool
            painter.setPen(pen)
            # The panel's coordinates are the same as the viewer's, so we can draw directly
            painter.drawRect(self._current_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = event.pos()
            # Check if the click is inside the actual image area
            if self.parent().map_to_image(self._start_point):
                self._drawing = True
                self._current_rect = QRect(self._start_point, self._start_point)
                self.update()

    def mouseMoveEvent(self, event):
        if self._drawing:
            self._current_rect = QRect(self._start_point, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._drawing and event.button() == Qt.LeftButton:
            self._drawing = False
            
            # Map the final rectangle from widget coordinates to image coordinates
            top_left_img = self.parent().map_to_image(self._current_rect.topLeft())
            bottom_right_img = self.parent().map_to_image(self._current_rect.bottomRight())
            
            if top_left_img and bottom_right_img:
                final_rect = QRect(top_left_img, bottom_right_img).normalized()
                # Emit the signal with the final, correctly mapped rectangle
                if final_rect.width() > 2 and final_rect.height() > 2: # Ignore tiny accidental clicks
                    self.new_annotation.emit(final_rect)
            
            self._current_rect = QRect()
            self.update()