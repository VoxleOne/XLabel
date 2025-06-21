from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QDockWidget, QFileDialog, QMessageBox, QToolBar
)
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QAction, QIcon, QActionGroup, QColor, QPixmap, QPainter, QFont
from .image_viewer import ImageViewer
from .annotation_list import AnnotationList
from .class_list import ClassList
from .panels import BoundingBoxPanel, PolygonPanel, MaskPanel, KeypointsPanel

class XLabelMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLabel - Annotation Tool")
        self.setGeometry(100, 100, 1200, 800)

        self.image_viewer = ImageViewer(self)
        self.setCentralWidget(self.image_viewer)
        
        self.bbox_panel = BoundingBoxPanel(self.image_viewer)
        self.bbox_panel.set_ribbon_color(QColor("deepskyblue"))
        self.bbox_panel.new_annotation.connect(self._on_new_annotation)

        self.polygon_panel = PolygonPanel(self.image_viewer)
        self.polygon_panel.set_ribbon_color(QColor("mediumseagreen"))
        self.polygon_panel.new_annotation.connect(self._on_new_annotation)
        
        self.mask_panel = MaskPanel(self.image_viewer)
        self.mask_panel.set_ribbon_color(QColor("gold"))
        self.mask_panel.new_annotation.connect(self._on_new_annotation)

        self.keypoints_panel = KeypointsPanel(self.image_viewer)
        self.keypoints_panel.set_ribbon_color(QColor("orange"))

        self.annotation_list = AnnotationList(self)
        self.annotations_dock = QDockWidget("Annotations", self)
        self.annotations_dock.setWidget(self.annotation_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.annotations_dock)

        self.image_viewer.set_annotation_list(self.annotation_list)

        self.class_list = ClassList(self)
        self.class_dock = QDockWidget("Class Names", self)
        self.class_dock.setWidget(self.class_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.class_dock)

        self._create_menu()
        self._create_status_bar()
        self._create_mode_toolbar()

        self.annotation_list.annotation_selected.connect(self.image_viewer.set_selected_rect)
        self.annotation_list.annotation_deleted.connect(self._on_delete_annotation)

    def _set_active_mode(self, panel):
        for action in self.contextual_actions:
            action.setVisible(False)

        if isinstance(panel, MaskPanel):
            self.brush_action.setVisible(True)
            self.eraser_action.setVisible(True)

        self.statusBar().showMessage(f"Mode changed to: {panel.__class__.__name__}")
        self.image_viewer.transition_to(panel)

    # --- THE FIX: This slot is now much simpler. It just triggers a refresh. ---
    def _on_new_annotation(self):
        active_panel = self.image_viewer._active_panel
        if not active_panel:
            return
        
        status_message = "Annotation added."
        if isinstance(active_panel, MaskPanel):
            status_message = "Mask completed and added to list."
        elif isinstance(active_panel, BoundingBoxPanel):
            status_message = "Bounding Box added to list."
        elif isinstance(active_panel, PolygonPanel):
            status_message = "Polygon added to list."
        
        self.statusBar().showMessage(status_message, 3000)
        self.image_viewer.update_annotations_display()

    def _on_delete_annotation(self, index):
        active_panel = self.image_viewer._active_panel
        if active_panel and hasattr(active_panel, 'delete_annotation'):
            if active_panel.delete_annotation(index):
                self.statusBar().showMessage(f"Annotation {index + 1} deleted.", 3000)
                self.image_viewer.set_selected_rect(None)
                self.image_viewer.update_annotations_display()

    def _open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open XLabel PNG", "", "PNG Images (*.png)")
        if not file_name: return
        pixmap = QPixmap(file_name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Open Error", "Failed to load image.")
            return

        self.bbox_panel.clear_annotations()
        self.polygon_panel.clear_annotations()
        self.mask_panel.clear_annotations()
        self.keypoints_panel.clear_annotations()

        self.image_viewer.set_image(pixmap)
        self.image_viewer.clear_active_panel()
        
        for action in self.mode_actions:
            action.setEnabled(True)
        
        self.statusBar().showMessage(f"Loaded {file_name}")

    def _create_colored_icon(self, color: QColor, text:str = "", size=QSize(32, 32)) -> QIcon:
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if isinstance(color, QColor):
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(pixmap.rect(), 4, 4)
        
        if text:
            painter.setPen(Qt.black if color.lightness() > 127 else Qt.white)
            font = QFont()
            font.setPixelSize(size.height() * 0.6)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text)

        painter.end()
        return QIcon(pixmap)
    
    def _create_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        open_action = QAction("Open XLabel PNG...", self)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
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
        mode_toolbar = QToolBar("Annotation Tools", self)
        mode_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.LeftToolBarArea, mode_toolbar)
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        
        self.mode_actions = []

        bbox_action = QAction(self._create_colored_icon(QColor("deepskyblue")), "Bounding Box (B)", self)
        bbox_action.setCheckable(True)
        bbox_action.triggered.connect(lambda: self._set_active_mode(self.bbox_panel))
        mode_toolbar.addAction(bbox_action)
        mode_group.addAction(bbox_action)
        self.mode_actions.append(bbox_action)

        polygon_action = QAction(self._create_colored_icon(QColor("mediumseagreen")), "Polygon (P)", self)
        polygon_action.setCheckable(True)
        polygon_action.triggered.connect(lambda: self._set_active_mode(self.polygon_panel))
        mode_toolbar.addAction(polygon_action)
        mode_group.addAction(polygon_action)
        self.mode_actions.append(polygon_action)

        mask_action = QAction(self._create_colored_icon(QColor("gold")), "Mask (M)", self)
        mask_action.setCheckable(True)
        mask_action.triggered.connect(lambda: self._set_active_mode(self.mask_panel))
        mode_toolbar.addAction(mask_action)
        mode_group.addAction(mask_action)
        self.mode_actions.append(mask_action)

        keypoints_action = QAction(self._create_colored_icon(QColor("orange")), "Keypoints (K)", self)
        keypoints_action.setCheckable(True)
        keypoints_action.triggered.connect(lambda: self._set_active_mode(self.keypoints_panel))
        mode_toolbar.addAction(keypoints_action)
        mode_group.addAction(keypoints_action)
        self.mode_actions.append(keypoints_action)

        for action in self.mode_actions:
            action.setEnabled(False)

        mode_toolbar.addSeparator()

        self.contextual_actions = []
        mask_tool_group = QActionGroup(self)
        mask_tool_group.setExclusive(True)

        self.brush_action = QAction(self._create_colored_icon(QColor(210, 210, 210), "B"), "Brush", self)
        self.brush_action.setCheckable(True)
        self.brush_action.setChecked(True)
        self.brush_action.triggered.connect(self.mask_panel.set_brush_mode)
        mode_toolbar.addAction(self.brush_action)
        mask_tool_group.addAction(self.brush_action)
        self.contextual_actions.append(self.brush_action)

        self.eraser_action = QAction(self._create_colored_icon(QColor(210, 210, 210), "E"), "Eraser", self)
        self.eraser_action.setCheckable(True)
        self.eraser_action.triggered.connect(self.mask_panel.set_eraser_mode)
        mode_toolbar.addAction(self.eraser_action)
        mask_tool_group.addAction(self.eraser_action)
        self.contextual_actions.append(self.eraser_action)

        for action in self.contextual_actions:
            action.setVisible(False)

    def _save_file(self):
        QMessageBox.information(self, "Save", "This would save the current annotations.")

    def _save_file_as(self):
        QMessageBox.information(self, "Save As", "This would save to a new file.")

    def _show_about(self):
        QMessageBox.about(self, "About XLabel", "<b>XLabel</b><br>Created by VoxleOne & Copilot.")