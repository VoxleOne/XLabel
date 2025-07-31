from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Signal, Qt, QRect
from PySide6.QtGui import QPixmap, QIcon, QColor, QKeyEvent, QPainter

class AnnotationList(QListWidget):
    annotation_selected = Signal(int)
    annotation_deleted = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemClicked.connect(self._on_item_clicked)

    def set_annotations(self, annotations_data):
        self.clear()
        
        annotations = annotations_data.get('completed', [])
        
        for i, annotation in enumerate(annotations):
            item_text = f"Annotation {i + 1}"
            icon = QIcon()

            if isinstance(annotation, QPixmap):
                icon_pixmap = QPixmap(64, 64)
                icon_pixmap.fill(QColor(50, 50, 50))
                painter = QPainter(icon_pixmap)
                painter.drawPixmap(icon_pixmap.rect(), annotation.scaled(icon_pixmap.size(), Qt.KeepAspectRatio))
                painter.end()
                icon = QIcon(icon_pixmap)
                item_text = f"Mask {i + 1}"
            elif isinstance(annotation, QRect):
                item_text = f"B-Box {i + 1}"
            elif isinstance(annotation, list):
                item_text = f"Polygon {i + 1}"
            
            list_item = QListWidgetItem(icon, item_text)
            self.addItem(list_item)

    def _on_item_clicked(self, item):
        self.annotation_selected.emit(self.row(item))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete:
            selected_items = self.selectedItems()
            if selected_items:
                row = self.row(selected_items[0])
                self.annotation_deleted.emit(row)
        else:
            super().keyPressEvent(event)