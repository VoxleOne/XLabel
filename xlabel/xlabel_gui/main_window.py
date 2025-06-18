from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QDockWidget
)
from PySide6.QtCore import Qt
from .image_viewer import ImageViewer
from .annotation_list import AnnotationList
from .class_list import ClassList

class XLabelMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLabel - Annotation Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Central image viewer
        self.image_viewer = ImageViewer(self)
        self.setCentralWidget(self.image_viewer)

        # Annotation list dock
        self.annotation_list = AnnotationList(self)
        self.annotations_dock = QDockWidget("Annotations", self)
        self.annotations_dock.setWidget(self.annotation_list)
        self.annotations_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.annotations_dock)

        # Class list dock
        self.class_list = ClassList(self)
        self.class_dock = QDockWidget("Class Names", self)
        self.class_dock.setWidget(self.class_list)
        self.class_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.class_dock)

        self._create_menu()
        self._create_status_bar()

    def _create_menu(self):
        menu = self.menuBar()  # <-- FIXED
        file_menu = menu.addMenu("&File")
        # Add menu actions in later bricks
        help_menu = menu.addMenu("&Help")

    def _create_status_bar(self):
        status = QStatusBar(self)
        status.showMessage("Ready")
        self.setStatusBar(status)
        
# --- Menu Action Handlers ---

    def _open_file(self):
        QMessageBox.information(self, "Open", "This would open a file dialog to select an XLabel PNG.")

    def _save_file(self):
        QMessageBox.information(self, "Save", "This would save the current annotations to the PNG.")

    def _save_file_as(self):
        QMessageBox.information(self, "Save As", "This would open a file dialog to save as a new XLabel PNG.")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About XLabel",
            "<b>XLabel - Annotation Tool</b><br><br>"
            "Version 0.1.0 (GUI Prototype)<br>"
            "Embed and manage image annotations directly within PNG files.<br><br>"
            "Created by VoxleOne & Copilot (AI Collaborator)."
        )
