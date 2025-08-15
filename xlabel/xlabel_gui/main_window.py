from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QDockWidget, QFileDialog, QMessageBox, QToolBar,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QColorDialog
)
from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtGui import QAction, QIcon, QActionGroup, QColor, QPixmap, QPainter, QFont
from xlabel.xlabel_gui.image_viewer import ImageViewer
from xlabel.xlabel_gui.annotation_list import AnnotationList
from xlabel.xlabel_gui.class_list import ClassList
from xlabel.xlabel_gui.panels import BoundingBoxPanel, PolygonPanel, MaskPanel, KeypointsPanel
# --- UPDATED: Import new dialog ---
from xlabel.xlabel_gui.widgets import KeypointsControlWidget, ModelSettingsDialog
from xlabel.xlabel_io import MetadataHandler, Exporter
from xlabel.model import ModelManager
import json
import os

class XLabelMainWindow(QMainWindow):
    # ... (__init__ and other methods remain the same) ...
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLabel - Annotation Tool")
        self.setGeometry(100, 100, 1200, 800)

        self.image_viewer = ImageViewer(self)
        self.setCentralWidget(self.image_viewer)
        
        self.current_file_path = None
        self.metadata_handler = MetadataHandler()
        self.exporter = Exporter()
        self.panels = {}
        self.model_manager = ModelManager()

        self.bbox_panel = BoundingBoxPanel(self.image_viewer)
        self.panels['bbox'] = self.bbox_panel
        self.polygon_panel = PolygonPanel(self.image_viewer)
        self.panels['polygon'] = self.polygon_panel
        self.mask_panel = MaskPanel(self.image_viewer)
        self.panels['mask'] = self.mask_panel
        self.keypoints_panel = KeypointsPanel(self.image_viewer)
        self.panels['keypoints'] = self.keypoints_panel
        
        for panel in self.panels.values():
            panel.new_annotation.connect(self._on_new_annotation)
        
        self.bbox_panel.set_ribbon_color(QColor("deepskyblue"))
        self.polygon_panel.set_ribbon_color(QColor("mediumseagreen"))
        self.mask_panel.set_ribbon_color(QColor("gold"))
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

        self.keypoints_controls = KeypointsControlWidget(self.keypoints_panel, self)
        self.keypoints_dock = QDockWidget("Keypoint Controls", self)
        self.keypoints_dock.setWidget(self.keypoints_controls)
        self.addDockWidget(Qt.RightDockWidgetArea, self.keypoints_dock)
        self.keypoints_dock.hide()

        self._create_menu()
        self._create_status_bar()
        self._create_mode_toolbar()

        self.annotation_list.annotation_selected.connect(self.image_viewer.set_selected_rect)
        self.annotation_list.annotation_deleted.connect(self._on_delete_annotation)
        
    def _set_active_mode(self, panel):
        self.keypoints_dock.hide()
        for action in self.contextual_actions:
            action.setVisible(False)

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
        self.run_auto_annotate_action.setEnabled(True)
        self.model_settings_action.setEnabled(True)
        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)
        self.export_as_action.setEnabled(True)
        
        self.setWindowTitle(f"XLabel - {os.path.basename(self.current_file_path)}")
        self.statusBar().showMessage(f"Loaded {file_name}")

    def _load_annotations_from_file(self):
        if not self.current_file_path: return
        
        all_annotations = self.metadata_handler.load_annotations(self.current_file_path)
        if not all_annotations:
            self.statusBar().showMessage("No annotations found in image metadata.", 3000)
            return

        if 'bbox' in all_annotations and hasattr(self.bbox_panel, '_annotations'):
             for ann_data in all_annotations.get('bbox', {}).get('completed', []):
                 self.bbox_panel.add_annotation(
                     QRect(*ann_data['rect']), 
                     source=ann_data.get('source', 'manual'),
                     class_id=ann_data.get('class_id', 0)
                 )

        if 'polygon' in all_annotations and hasattr(self.polygon_panel, '_annotations'):
             self.polygon_panel._annotations = [[QPoint(*p) for p in poly] for poly in all_annotations.get('polygon', {}).get('completed', [])]
        
        self.image_viewer.update_annotations_display()
        self.statusBar().showMessage(f"Loaded annotations from {self.current_file_path}", 4000)
    
    def _run_model_inference(self):
        if not self.current_file_path or not self.image_viewer._pixmap:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        self.statusBar().showMessage("Running model inference...", 5000)
        
        img_width = self.image_viewer._pixmap.width()
        img_height = self.image_viewer._pixmap.height()

        predictions = self.model_manager.predict(self.current_file_path, img_width, img_height)

        if not predictions:
            self.statusBar().showMessage("No objects detected with current settings.", 3000)
            return

        for pred in predictions:
            x, y, w, h = pred['bbox']
            self.bbox_panel.add_annotation(
                QRect(x, y, w, h), 
                source=pred.get('source', 'model'), 
                class_id=pred.get('class_id', 0)
            )

        self.bbox_action.setChecked(True)
        self._set_active_mode(self.bbox_panel)
        
        self.image_viewer.update_annotations_display()
        self.statusBar().showMessage(f"Found {len(predictions)} objects.", 3000)

    # --- UPDATED: This now opens our new dialog ---
    def _open_model_settings(self):
        """Opens the model settings dialog and applies changes if accepted."""
        dialog = ModelSettingsDialog(self.model_manager, self)
        
        # The exec() method shows the dialog modally
        if dialog.exec():
            self.statusBar().showMessage("Model settings updated.", 3000)
        else:
            self.statusBar().showMessage("Model settings change cancelled.", 3000)

    def _get_all_annotations(self) -> dict:
        all_annotations = {}
        for name, panel in self.panels.items():
            ann_data = panel.get_annotations()
            
            if name == 'bbox' and ann_data.get('completed'):
                all_annotations[name] = {
                    'completed': [
                        {
                            'rect': [d['rect'].x(), d['rect'].y(), d['rect'].width(), d['rect'].height()],
                            'source': d.get('source', 'manual'),
                            'class_id': d.get('class_id', 0)
                        } for d in ann_data['completed']
                    ]
                }
            elif name == 'polygon' and ann_data.get('completed'):
                 all_annotations[name] = {
                    'completed': [
                        [[p.x(), p.y()] for p in poly] for poly in ann_data['completed']
                    ]
                }
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

        model_menu = menu.addMenu("&Model")
        
        self.run_auto_annotate_action = QAction("Run Auto-Annotate", self)
        self.run_auto_annotate_action.triggered.connect(self._run_model_inference)
        self.run_auto_annotate_action.setEnabled(False)
        model_menu.addAction(self.run_auto_annotate_action)
        
        self.model_settings_action = QAction("Model Settings...", self)
        self.model_settings_action.triggered.connect(self._open_model_settings)
        self.model_settings_action.setEnabled(False)
        model_menu.addAction(self.model_settings_action)
        
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

        self.bbox_action = QAction(self._create_colored_icon(QColor("deepskyblue")), "Bounding Box (B)", self)
        self.bbox_action.setCheckable(True)
        self.bbox_action.triggered.connect(lambda: self._set_active_mode(self.bbox_panel))
        mode_toolbar.addAction(self.bbox_action)
        mode_group.addAction(self.bbox_action)
        self.mode_actions.append(self.bbox_action)

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
        
        save_path = self.current_file_path
        if not save_path.lower().endswith('.png'):
            reply = QMessageBox.question(self, "Save to PNG",
                                         "Saving annotations requires a PNG file. Would you like to save as a new PNG?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.No:
                return
            base_path = save_path.rsplit('.', 1)[0]
            save_path = f"{base_path}_annotated.png"

        new_path, success = self.metadata_handler.save_annotations(save_path, all_annotations, source_image_path=self.current_file_path)

        if success:
            self.current_file_path = new_path
            self.setWindowTitle(f"XLabel - {os.path.basename(self.current_file_path)}")
            self.statusBar().showMessage(f"Annotations saved to {self.current_file_path}", 4000)
        else:
            QMessageBox.warning(self, "Save Error", f"Could not save annotations to {self.current_file_path}.")

    def _save_file_as(self):
        if not self.current_file_path: return
        all_annotations = self._get_all_annotations()
        if not all_annotations:
            QMessageBox.information(self, "Save As", "There are no annotations to save.")
            return

        base_path = self.current_file_path.rsplit('.', 1)[0]
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Annotations As...", f"{base_path}_annotated.png", "PNG Image (*.png)")
        
        if not file_name: return

        new_path, success = self.metadata_handler.save_annotations(file_name, all_annotations, source_image_path=self.current_file_path)
        
        if success:
            self.current_file_path = new_path
            self.setWindowTitle(f"XLabel - {os.path.basename(self.current_file_path)}")
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
        formats = ["YOLO (*.txt)", "COCO (*.json)", "Pascal VOC (*.xml)"]
        file_filter = ";;".join(formats)
        base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        file_name, selected_filter = QFileDialog.getSaveFileName(self, "Export Annotations As...", base_name, file_filter)
        if not file_name: return
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
                output_content = self.exporter.to_coco(all_annotations, self.current_file_path, img_w, img_h)
                if not json.loads(output_content)['annotations']:
                    QMessageBox.information(self, "Export Info", "No annotations found to export for COCO.")
                    return
            elif selected_filter == "Pascal VOC (*.xml)":
                QMessageBox.information(self, "Not Implemented", "Pascal VOC export is not yet available.")
                return
            with open(file_name, 'w') as f: f.write(output_content)
            self.statusBar().showMessage(f"Annotations exported to {file_name}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred during export:\n{e}")

    def _show_about(self):
        QMessageBox.about(self, "About XLabel", "<b>XLabel</b><br>Created by VoxleOne ebmarques & Copilot.")
