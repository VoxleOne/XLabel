from PySide6.QtWidgets import QListWidget

class ClassList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #f6f6f6; padding: 10px;")
        self.addItem("Class list will appear here.")
