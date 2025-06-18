from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QPen
from PySide6.QtCore import Qt, QRect, QPoint

class ImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._rectangles = []  # List of QRect
        self._drawing = False
        self._start_point = None
        self._current_rect = None
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self._selected_rect_index = None
    
    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._rectangles.clear()
        self.update()
        
    def set_selected_rect(self, idx):
        self._selected_rect_index = idx
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self._pixmap:
            pixmap_scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            offset = QPoint(
                (self.width() - pixmap_scaled.width()) // 2,
                (self.height() - pixmap_scaled.height()) // 2
            )
            painter.drawPixmap(offset, pixmap_scaled)
            painter.translate(offset)
            scale_x = pixmap_scaled.width() / self._pixmap.width()
            scale_y = pixmap_scaled.height() / self._pixmap.height()
            painter.scale(scale_x, scale_y)
            pen = QPen(Qt.red, 2 / max(scale_x, scale_y))
            painter.setPen(pen)
            for i, rect in enumerate(self._rectangles):
                if i == self._selected_rect_index:
                    painter.setPen(QPen(Qt.yellow, 3 / max(scale_x, scale_y)))
                else:
                    painter.setPen(QPen(Qt.red, 2 / max(scale_x, scale_y)))
                painter.drawRect(rect)
            
    def mousePressEvent(self, event):
        if not self._pixmap:
            return
        if event.button() == Qt.LeftButton:
            img_pos = self._map_to_image(event.pos())
            if img_pos:
                self._drawing = True
                self._start_point = img_pos
                self._current_rect = QRect(img_pos, img_pos)

    def mouseMoveEvent(self, event):
        if self._drawing and self._pixmap:
            img_pos = self._map_to_image(event.pos())
            if img_pos:
                self._current_rect = QRect(self._start_point, img_pos)
                self.update()

    def mouseReleaseEvent(self, event):
        if self._drawing and self._pixmap:
            img_pos = self._map_to_image(event.pos())
            if img_pos and self._current_rect:
                self._current_rect = QRect(self._start_point, img_pos).normalized()
                self._rectangles.append(self._current_rect)
                self._drawing = False
                self._current_rect = None
                self._start_point = None
                self.update()

    def _map_to_image(self, widget_point):
        if not self._pixmap:
            return None
        pixmap_scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - pixmap_scaled.width()) // 2
        offset_y = (self.height() - pixmap_scaled.height()) // 2
        x = widget_point.x() - offset_x
        y = widget_point.y() - offset_y
        if x < 0 or y < 0 or x >= pixmap_scaled.width() or y >= pixmap_scaled.height():
            return None
        scale_x = self._pixmap.width() / pixmap_scaled.width()
        scale_y = self._pixmap.height() / pixmap_scaled.height()
        img_x = int(x * scale_x)
        img_y = int(y * scale_y)
        return QPoint(img_x, img_y)

    def get_rectangles(self):
        return self._rectangles
