from PySide6.QtWidgets import QListWidget

class AnnotationList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItem("Annotation list will appear here.")