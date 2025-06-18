from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QDockWidget, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
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
        self.annotations_dock.setMinimumWidth(200)
        self.addDockWidget(Qt.RightDockWidgetArea, self.annotations_dock)

        # Class list dock
        self.class_list = ClassList(self)
        self.class_dock = QDockWidget("Class Names", self)
        self.class_dock.setWidget(self.class_list)
        self.class_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.class_dock.setMinimumWidth(150)
        self.addDockWidget(Qt.RightDockWidgetArea, self.class_dock)

        self._create_menu()
        self._create_status_bar()

        # Connect annotation selection
        self.annotation_list.annotation_selected.connect(self._on_annotation_selected)

    def _create_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        open_action = QAction("Open XLabel PNG...", self)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        # Placeholders for Save, Save As
        save_action = QAction("Save", self)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)

        help_menu = menu.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        status = QStatusBar(self)
        status.showMessage("Ready")
        self.setStatusBar(status)

    # --- Menu Action Handlers ---

    def _open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open XLabel PNG",
            "",
            "PNG Images (*.png)"
        )
        if not file_name:
            return  # User cancelled

        from PySide6.QtGui import QPixmap
        pixmap = QPixmap(file_name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Open Error", "Failed to load the selected PNG image.")
            return

        self.image_viewer.set_image(pixmap)
        self.statusBar().showMessage(f"Loaded {file_name}")
        self.annotation_list.set_annotations(self.image_viewer.get_rectangles())

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

    def _on_annotation_selected(self, idx):
        self.image_viewer.set_selected_rect(idx)
