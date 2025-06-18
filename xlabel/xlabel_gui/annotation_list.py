from PySide6.QtWidgets import QListWidget
from PySide6.QtCore import Signal

class AnnotationList(QListWidget):
    annotation_selected = Signal(int)  # index of the annotation

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentRowChanged.connect(self._on_row_changed)

    def set_annotations(self, rects):
        self.clear()
        for i, rect in enumerate(rects):
            self.addItem(f"Rect {i+1}: ({rect.x()},{rect.y()}) {rect.width()}x{rect.height()}")

    def _on_row_changed(self, row):
        if row >= 0:
            self.annotation_selected.emit(row)
