from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QDockWidget, QFileDialog, QMessageBox, QToolBar, QButtonGroup
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QAction, QIcon
from .image_viewer import ImageViewer
from .annotation_list import AnnotationList
from .class_list import ClassList
from .panels import BoundingBoxPanel # Import the new panel

class XLabelMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLabel - Annotation Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Central image viewer
        self.image_viewer = ImageViewer(self)
        self.setCentralWidget(self.image_viewer)
        
        # --- Panels ---
        self.bbox_panel = BoundingBoxPanel(self.image_viewer)
        # Connect the panel's signal to a slot in the main window
        self.bbox_panel.new_annotation.connect(self._on_new_annotation)
        self.active_panel = None

        # --- Docks ---
        self.annotation_list = AnnotationList(self)
        self.annotations_dock = QDockWidget("Annotations", self)
        self.annotations_dock.setWidget(self.annotation_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.annotations_dock)

        self.class_list = ClassList(self)
        self.class_dock = QDockWidget("Class Names", self)
        self.class_dock.setWidget(self.class_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.class_dock)

        # --- Setup UI ---
        self._create_menu()
        self._create_status_bar()
        self._create_mode_toolbar()

        self.annotation_list.annotation_selected.connect(self.image_viewer.set_selected_rect)

    def _create_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        open_action = QAction("Open XLabel PNG...", self)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        # ... (rest of menu is the same)
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

    def _create_mode_toolbar(self):
        mode_toolbar = QToolBar("Annotation Modes", self)
        self.addToolBar(Qt.LeftToolBarArea, mode_toolbar)
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)

        bbox_action = QAction("Bounding Box", self)
        bbox_action.setCheckable(True)
        bbox_action.setChecked(True)
        bbox_action.triggered.connect(lambda: self._set_active_mode(self.bbox_panel))
        mode_toolbar.addAction(bbox_action)
        mode_group.addButton(bbox_action)
        
        # Add other mode buttons here later...
        polygon_action = QAction("Polygon", self)
        polygon_action.setCheckable(True)
        mode_toolbar.addAction(polygon_action)
        mode_group.addButton(polygon_action)

    def _set_active_mode(self, panel):
        """Generic handler to switch between annotation panels."""
        if self.active_panel:
            self.active_panel.slide_out()
        
        self.active_panel = panel
        if self.active_panel:
            self.active_panel.slide_in()
            self.statusBar().showMessage(f"Mode changed to: {panel.__class__.__name__}")

    # --- Action Handlers & Slots ---

    def _on_new_annotation(self, rect: QRect):
        """Slot to receive a new annotation from a panel."""
        self.image_viewer.add_rectangle(rect)
        self.annotation_list.set_annotations(self.image_viewer.get_rectangles())
        # The viewer needs to repaint to show the new, permanent rectangle
        self.image_viewer.update()

    def _open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open XLabel PNG", "", "PNG Images (*.png)")
        if not file_name:
            return

        from PySide6.QtGui import QPixmap
        pixmap = QPixmap(file_name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Open Error", "Failed to load image.")
            return

        self.image_viewer.set_image(pixmap)
        self.statusBar().showMessage(f"Loaded {file_name}")
        self.annotation_list.set_annotations(self.image_viewer.get_rectangles())
        
        # Automatically activate the default mode when an image is loaded
        self._set_active_mode(self.bbox_panel)

    def _save_file(self):
        QMessageBox.information(self, "Save", "This would save the current annotations.")

    def _save_file_as(self):
        QMessageBox.information(self, "Save As", "This would save to a new file.")

    def _show_about(self):
        QMessageBox.about(self, "About XLabel", "<b>XLabel</b><br>Created by VoxleOne & Copilot.")