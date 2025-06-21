from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from .base_panel import BasePanel

class BoundingBoxPanel(BasePanel):
    """Interactive panel for drawing bounding boxes with a visual ribbon."""
    
    new_annotation = Signal(QRect)

    # CORRECTED CONSTRUCTOR: Now accepts 'color' and 'parent'
    def __init__(self, color: QColor, parent: QWidget):
        # Pass both arguments to the parent class constructor
        super().__init__(color, parent)
        self._drawing = False
        self._start_point = QPoint()
        self._current_rect = QRect()

    def paintEvent(self, event):
        """Draws the panel's UI: ribbon, background, and the in-progress rectangle."""
        painter = QPainter(self)
        
        # 1. Draw the semi-transparent background
        painter.fillRect(self.rect(), self.background_color)
        
        # 2. Draw the colored ribbon on the left edge
        ribbon_rect = QRect(0, 0, self.ribbon_width, self.height())
        painter.fillRect(ribbon_rect, self.ribbon_color)
        
        # 3. If drawing, draw the "rubber band" rectangle
        if self._drawing:
            pen = QPen(Qt.cyan, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.transparent)
            painter.drawRect(self._current_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = event.pos()
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
            top_left_img = self.parent().map_to_image(self._current_rect.topLeft())
            bottom_right_img = self.parent().map_to_image(self._current_rect.bottomRight())
            
            if top_left_img and bottom_right_img:
                final_rect = QRect(top_left_img, bottom_right_img).normalized()
                if final_rect.width() > 2 and final_rect.height() > 2:
                    self.new_annotation.emit(final_rect)
            
            self._current_rect = QRect()
            self.update()