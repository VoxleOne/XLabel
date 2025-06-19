from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QPainter, QPen
from PySide6.QtCore import Qt, QRect, QPoint

class ImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._rectangles = []  # List of final QRects
        self._selected_rect_index = None
        self.setMinimumSize(400, 300)
    
    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._rectangles.clear()
        self.update()
        
    def set_selected_rect(self, idx):
        self._selected_rect_index = idx
        self.update()

    def add_rectangle(self, rect: QRect):
        """Adds a finalized rectangle to the list."""
        self._rectangles.append(rect)

    def get_rectangles(self):
        return self._rectangles

    def paintEvent(self, event):
        """Paints the base image and the finalized annotations."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if not self._pixmap:
            return

        # Calculate scaling and offset to center the image
        pixmap_scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset = QPoint(
            (self.width() - pixmap_scaled.width()) // 2,
            (self.height() - pixmap_scaled.height()) // 2
        )
        painter.drawPixmap(offset, pixmap_scaled)

        # Transform painter to draw annotations in image coordinates
        painter.translate(offset)
        scale_x = pixmap_scaled.width() / self._pixmap.width()
        scale_y = pixmap_scaled.height() / self._pixmap.height()
        painter.scale(scale_x, scale_y)

        # Draw all committed rectangles
        for i, rect in enumerate(self._rectangles):
            pen_width = 3 if i == self._selected_rect_index else 2
            pen_color = Qt.yellow if i == self._selected_rect_index else Qt.red
            pen = QPen(pen_color, pen_width / max(scale_x, scale_y))
            painter.setPen(pen)
            painter.drawRect(rect)
            
    def map_to_image(self, widget_point: QPoint):
        """Maps a point from widget coordinates to image coordinates."""
        if not self._pixmap:
            return None
            
        pixmap_scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - pixmap_scaled.width()) // 2
        offset_y = (self.height() - pixmap_scaled.height()) // 2
        
        # Check if the point is within the visible image area
        if not QRect(offset_x, offset_y, pixmap_scaled.width(), pixmap_scaled.height()).contains(widget_point):
            return None

        # Translate and scale the point
        x = widget_point.x() - offset_x
        y = widget_point.y() - offset_y
        scale_x = self._pixmap.width() / pixmap_scaled.width()
        scale_y = self._pixmap.height() / pixmap_scaled.height()
        
        return QPoint(int(x * scale_x), int(y * scale_y))