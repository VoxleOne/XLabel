from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter
from PySide6.QtCore import QRect
from .base_panel import BasePanel

class KeypointsPanel(BasePanel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._annotations = []

    def get_annotations(self) -> list:
        return self._annotations

    def clear_annotations(self):
        self._annotations.clear()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._background_color)
        ribbon_rect = QRect(0, 0, self.ribbon_width, self.height())
        painter.fillRect(ribbon_rect, self.ribbon_color)