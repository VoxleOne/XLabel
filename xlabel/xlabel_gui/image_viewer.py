from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

class ImageViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Open an XLabel PNG to view.")
        self.setStyleSheet("QLabel { background-color: #333; color: white; border: 1px solid #555; }")