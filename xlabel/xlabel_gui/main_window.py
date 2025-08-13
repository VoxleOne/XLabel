from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QDockWidget, QFileDialog, QMessageBox, QToolBar,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QColorDialog
)
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QAction, QIcon, QActionGroup, QColor, QPixmap, QPainter, QFont
from .image_viewer import ImageViewer
from .annotation_list import AnnotationList
from .class_list import ClassList
from .panels import BoundingBoxPanel, PolygonPanel, MaskPanel, KeypointsPanel
from xlabel.xlabel_io import MetadataHandler, Exporter
import json
import os

class KeypointsControlWidget(QWidget):
    """A widget to hold the controls for the KeypointsPanel."""
    def __init__(self, keypoints_panel: KeypointsPanel, parent=None):
        super().__init__(parent)
        self.panel = keypoints_panel
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Instructions
        instructions = QLabel("Right-click or press Enter to complete a set.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Point size slider
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Point Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(3, 20)
        self.size_slider.setValue(self.panel.point_radius)
        self.size_slider.valueChanged.connect(self.set_point_size)
        size_layout.addWidget(self.size_slider)
        layout.addLayout(size_layout)
        
        # Color selector
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Point Color:"))
        self.color_btn = QPushButton()
        self.update_color_button()
        self.color_btn.clicked.connect(self.select_color)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)

        # Complete button
        self.complete_btn = QPushButton("Complete Set")
        self.complete_btn.clicked.connect(self.panel.complete_set)
        layout.addWidget(self.complete_btn)
        
        layout.addStretch(1)

    def set_point_size(self, size):
        self.panel.point_radius = size
        self.panel.parent().update()

    def select_color(self):
        color = QColorDialog.getColor(self.panel.point_color, self, "Select Keypoint Color")
        if color.isValid():
            self.panel.point_color = color
            self.update_color_button()
            self.panel.parent().update()
    
    def update_color_button(self):
        self.color_btn.setStyleSheet(f"background-color: {self.panel.point_color.name()}; border: 1px solid #555;")

class XLabelMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLabel - Annotation Tool")
        self.setGeometry(100, 100, 1200, 800)

        self.image_viewer = ImageViewer(self)
        self.setCentralWidget(self.image_viewer)
        
        # --- State ---
        self.current_file_path = None
        self.metadata_handler = MetadataHandler()
        self.exporter = Exporter()
        self.panels = {}

        self.bbox_panel = BoundingBoxPanel(self.image_viewer)
        self.bbox_panel.set_ribbon_color(QColor("deepskyblue"))
        self.bbox_panel.new_annotation.connect(self._on_new_annotation)
        self.panels['bbox'] = self.bbox_panel

        self.polygon_panel = PolygonPanel(self.image_viewer)
        self.polygon_panel.set_ribbon_color(QColor("mediumseagreen"))
        self.polygon_panel.new_annotation.connect(self._on_new_annotation)
        self.panels['polygon'] = self.polygon_panel
        
        self.mask_panel = MaskPanel(self.image_viewer)
        self.mask_panel.set_ribbon_color(QColor("gold"))
        self.mask_panel.new_annotation.connect(self._on_new_annotation)
        self.panels['mask'] = self.mask_panel

        self.keypoints_panel = KeypointsPanel(self.image_viewer)
        self.keypoints_panel.set_ribbon_color(QColor("orange"))
        self.keypoints_panel.new_annotation.connect(self._on_new_annotation)
        self.panels['keypoints'] = self.keypoints_panel

        self.annotation_list = AnnotationList(self)
        self.annotations_dock = QDockWidget("Annotations", self)
        self.annotations_dock.setWidget(self.annotation_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.annotations_dock)

        self.image_viewer.set_annotation_list(self.annotation_list)

        self.class_list = ClassList(self)
        self.class_dock = QDockWidget("Class Names", self)
        self.class_dock.setWidget(self.class_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.class_dock)

        # --- NEW: Keypoints control dock ---
        self.keypoints_controls = KeypointsControlWidget(self.keypoints_panel, self)
        self.keypoints_dock = QDockWidget("Keypoint Controls", self)
        self.keypoints_dock.setWidget(self.keypoints_controls)
        self.addDockWidget(Qt.RightDockWidgetArea, self.keypoints_dock)
        self.keypoints_dock.hide()
        # -----------------------------------

        self._create_menu()
        self._create_status_bar()
        self._create_mode_toolbar()

        self.annotation_list.annotation_selected.connect(self.image_viewer.set_selected_rect)
        self.annotation_list.annotation_deleted.connect(self._on_delete_annotation)

    def _set_active_mode(self, panel):
        # Hide all contextual docks/toolbars first
        self.keypoints_dock.hide()
        for action in self.contextual_actions:
            action.setVisible(False)

        # Show contextual items for the selected panel
        if isinstance(panel, MaskPanel):
            self.brush_action.setVisible(True)
            self.eraser_action.setVisible(True)
        elif isinstance(panel, KeypointsPanel):
            self.keypoints_dock.show()

        self.statusBar().showMessage(f"Mode changed to: {panel.__class__.__name__.replace('Panel', '')}")
        self.image_viewer.transition_to(panel)

    def _on_new_annotation(self):
        active_panel = self.image_viewer._active_panel
        if not active_panel: return
        
        mode_name = active_panel.__class__.__name__.replace('Panel', '')
        self.statusBar().showMessage(f"{mode_name} annotation added.", 3000)
        self.image_viewer.update_annotations_display()

    def _on_delete_annotation(self, index):
        active_panel = self.image_viewer._active_panel
        if active_panel and hasattr(active_panel, 'delete_annotation'):
            if active_panel.delete_annotation(index):
                self.statusBar().showMessage(f"Annotation {index + 1} deleted.", 3000)
                self.image_viewer.set_selected_rect(None)
                self.image_viewer.update_annotations_display()

    def _open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg)")
        if not file_name: return
        
        self.current_file_path = file_name
        pixmap = QPixmap(file_name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Open Error", "Failed to load image.")
            self.current_file_path = None
            return

        for panel in self.panels.values():
            panel.clear_annotations()

        self.image_viewer.set_image(pixmap)
        self.image_viewer.clear_active_panel()

        self._load_annotations_from_file()
        
        for action in self.mode_actions:
            action.setEnabled(True)
        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)
        self.export_as_action.setEnabled(True)
        
        self.setWindowTitle(f"XLabel - {self.current_file_path}")
        self.statusBar().showMessage(f"Loaded {file_name}")

    def _load_annotations_from_file(self):
        if not self.current_file_path: return
        
        all_annotations = self.metadata_handler.load_annotations(self.current_file_path)
        if not all_annotations:
            self.statusBar().showMessage("No annotations found in image metadata.", 3000)
            return

        # Here we would need a more robust way to deserialize the data
        # back into Qt objects (QRect, QPixmap, etc.). For now, this is a simplification.
        if 'bbox' in all_annotations and hasattr(self.bbox_panel, '_annotations'):
             self.bbox_panel._annotations = [QRect(*r) for r in all_annotations['bbox']['completed']]
        if 'polygon' in all_annotations and hasattr(self.polygon_panel, '_annotations'):
             self.polygon_panel._annotations = [[QPoint(*p) for p in poly] for poly in all_annotations['polygon']['completed']]
        
        # Mask and Keypoints loading would be more complex and is omitted for this sprint.

        self.image_viewer.update_annotations_display()
        self.statusBar().showMessage(f"Loaded annotations from {self.current_file_path}", 4000)

    def _get_all_annotations(self) -> dict:
        """Collects annotations from all panels into a single dictionary."""
        all_annotations = {}
        for name, panel in self.panels.items():
            # A more robust solution would be needed to serialize custom Qt objects
            # like QRect, QPixmap, QPoint. This is a simplified example.
            ann_data = panel.get_annotations()
            
            # Simple serialization for BBox (list of lists)
            if name == 'bbox' and ann_data.get('completed'):
                all_annotations[name] = {
                    'completed': [
                        [r.x(), r.y(), r.width(), r.height()] for r in ann_data['completed']
                    ]
                }
            # Simple serialization for Polygon (list of lists of lists)
            elif name == 'polygon' and ann_data.get('completed'):
                 all_annotations[name] = {
                    'completed': [
                        [[p.x(), p.y()] for p in poly] for poly in ann_data['completed']
                    ]
                }
            # Other types would need their own serialization logic
            # For now, we just store what we can easily serialize.
        return all_annotations

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
        
        open_action = QAction("Open Image...", self)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        self.save_action = QAction("Save Annotations", self)
        self.save_action.triggered.connect(self._save_file)
        self.save_action.setEnabled(False)
        file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction("Save Annotations As...", self)
        self.save_as_action.triggered.connect(self._save_file_as)
        self.save_as_action.setEnabled(False)
        file_menu.addAction(self.save_as_action)
        
        file_menu.addSeparator()

        self.export_as_action = QAction("Export As...", self)
        self.export_as_action.triggered.connect(self._export_file_as)
        self.export_as_action.setEnabled(False)
        file_menu.addAction(self.export_as_action)

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
        if not self.current_file_path:
            self._save_file_as()
            return

        all_annotations = self._get_all_annotations()
        if not all_annotations:
            QMessageBox.information(self, "Save", "There are no annotations to save.")
            return
        
        # Saving to PNG metadata requires the file to be PNG.
        # We can offer to convert it.
        if not self.current_file_path.lower().endswith('.png'):
            reply = QMessageBox.question(self, "Save to PNG",
                                         "Saving annotations to metadata requires converting the image to PNG format. "
                                         "A new file will be created. Continue?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        new_path, success = self.metadata_handler.save_annotations(self.current_file_path, all_annotations)

        if success:
            self.current_file_path = new_path
            self.setWindowTitle(f"XLabel - {self.current_file_path}")
            self.statusBar().showMessage(f"Annotations saved to {self.current_file_path}", 4000)
        else:
            QMessageBox.warning(self, "Save Error", "Could not save annotations to the image file.")

    def _save_file_as(self):
        if not self.current_file_path: return
        
        all_annotations = self._get_all_annotations()
        if not all_annotations:
            QMessageBox.information(self, "Save As", "There are no annotations to save.")
            return

        # Propose a new filename based on the old one, but as a PNG
        base_path = self.current_file_path.rsplit('.', 1)[0]
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Annotations As...", f"{base_path}_annotated.png", "PNG Image (*.png)")
        
        if not file_name: return

        new_path, success = self.metadata_handler.save_annotations(self.current_file_path, all_annotations)
        
        if success:
            # Since we are saving "as", we need to copy the image content to the new path
            # The metadata_handler already does this. We just need to update our state.
            self.current_file_path = new_path
            self.setWindowTitle(f"XLabel - {self.current_file_path}")
            self.statusBar().showMessage(f"Annotations saved to {self.current_file_path}", 4000)
        else:
            QMessageBox.warning(self, "Save Error", "Could not save annotations to the new image file.")

    def _export_file_as(self):
        if not self.current_file_path or not self.image_viewer._pixmap:
            QMessageBox.warning(self, "Export Error", "Please open an image first.")
            return

        all_annotations = self._get_all_annotations()
        if not all_annotations:
            QMessageBox.information(self, "Export", "There are no annotations to export.")
            return

        # Define the supported formats
        formats = [
            "YOLO (*.txt)",
            "COCO (*.json)",
            "Pascal VOC (*.xml)",
        ]
        file_filter = ";;".join(formats)
        
        base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        
        file_name, selected_filter = QFileDialog.getSaveFileName(self, "Export Annotations As...", base_name, file_filter)
        
        if not file_name:
            return

        try:
            pixmap = self.image_viewer._pixmap
            img_w, img_h = pixmap.width(), pixmap.height()
            
            output_content = ""
            if selected_filter == "YOLO (*.txt)":
                output_content = self.exporter.to_yolo(all_annotations, img_w, img_h)
                if not output_content:
                    QMessageBox.information(self, "Export Info", "No bounding box annotations found to export for YOLO.")
                    return
            elif selected_filter == "COCO (*.json)":
                QMessageBox.information(self, "Not Implemented", "COCO export is not yet available.")
                return
            elif selected_filter == "Pascal VOC (*.xml)":
                QMessageBox.information(self, "Not Implemented", "Pascal VOC export is not yet available.")
                return

            with open(file_name, 'w') as f:
                f.write(output_content)
            
            self.statusBar().showMessage(f"Annotations exported to {file_name}", 4000)

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred during export:\n{e}")

    def _show_about(self):
        QMessageBox.about(self, "About XLabel", "<b>XLabel</b><br>Created by VoxleOne ebmarques & Copilot.")
