# xlabel_gui.py — MIT License
# Author: VoxleOne & Eraldo Marques (AI Collaborator)
# Created: 2025-06-17 (GUI Inception)
# This file is part of the XLabel project.
# See LICENSE.txt for full license terms. This header should be retained.

import sys
import os
import logging

# Attempt to import PySide6
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, 
        QMenuBar, QStatusBar, QFileDialog, QMessageBox, QDockWidget,
        QListWidget, QListWidgetItem
    )
    from PySide6.QtGui import QAction, QPixmap, QPainter, QColor, QPen, QIcon
    from PySide6.QtCore import Qt, QRect, QSize
except ImportError:
    print("PySide6 is not installed. Please install it: pip install PySide6")
    sys.exit(1)

# Import XLabel core modules (assuming they are in the same directory or Python path)
try:
    import xreader 
    import xcreator
    # import xlabel_format_converters # We'll use this later
except ImportError as e:
    print(f"Could not import XLabel core modules: {e}. Ensure they are in the Python path.")
    sys.exit(1)

# --- Setup Logger for GUI ---
gui_logger = logging.getLogger("xlabel_gui")
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')


# --- Main Application Window ---
class XLabelMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XLabel - Annotation Tool")
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        self.current_image_path = None
        self.current_xlabel_metadata = None
        self.original_pixmap = None # To store the loaded image without annotations

        self._create_widgets()
        self._create_layouts()
        self._create_actions()
        self._create_menus()
        self._create_status_bar()
        self._create_docks()
        
        self.statusBar().showMessage("Welcome to XLabel! Open an XLabel PNG to begin.")

    def _create_widgets(self):
        gui_logger.debug("Creating widgets...")
        # Central image display area
        self.image_label = QLabel("Open an XLabel PNG file to view.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #333; color: white; border: 1px solid #555; }")
        
        # For listing annotations (will be in a dock)
        self.annotation_list_widget = QListWidget()
        self.class_list_widget = QListWidget() # For displaying class names

    def _create_layouts(self):
        gui_logger.debug("Creating layouts...")
        # Central widget
        central_widget = QWidget() # QMainWindow requires a central widget
        # For now, image_label is directly set as central. We might use a layout later for scrollbars.
        self.setCentralWidget(self.image_label) 

    def _create_actions(self):
        gui_logger.debug("Creating actions...")
        # File actions
        self.open_action = QAction(QIcon.fromTheme("document-open", QIcon(":/icons/open.png")), "&Open XLabel PNG...", self)
        self.open_action.setStatusTip("Open an existing XLabel PNG file")
        self.open_action.triggered.connect(self.open_file_dialog)

        self.save_action = QAction(QIcon.fromTheme("document-save", QIcon(":/icons/save.png")), "&Save XLabel PNG", self)
        self.save_action.setStatusTip("Save the current XLabel PNG (modifications)")
        self.save_action.setEnabled(False) # Enabled when an image is loaded and modified
        self.save_action.triggered.connect(self.save_file) # Placeholder

        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), "Save XLabel PNG &As...", self)
        self.save_as_action.setStatusTip("Save the current XLabel data to a new PNG file")
        self.save_as_action.setEnabled(False) # Enabled when an image is loaded
        self.save_as_action.triggered.connect(self.save_file_as) # Placeholder

        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "&Exit", self)
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close)

        # Help actions
        self.about_action = QAction("&About XLabel", self)
        self.about_action.setStatusTip("Show information about XLabel")
        self.about_action.triggered.connect(self.show_about_dialog)


    def _create_menus(self):
        gui_logger.debug("Creating menus...")
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def _create_status_bar(self):
        gui_logger.debug("Creating status bar...")
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready")

    def _create_docks(self):
        gui_logger.debug("Creating docks...")
        # Annotations Dock
        annotations_dock = QDockWidget("Annotations", self)
        annotations_dock.setWidget(self.annotation_list_widget)
        annotations_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, annotations_dock)

        # Class List Dock
        class_list_dock = QDockWidget("Class Names", self)
        class_list_dock.setWidget(self.class_list_widget)
        class_list_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, class_list_dock)

    # --- Action Handlers ---
    def open_file_dialog(self):
        gui_logger.info("Open file dialog triggered.")
        # Assuming xreader and xcreator are in the same directory or Python path
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open XLabel PNG File", 
            "", # Start directory (empty means current or last used)
            "XLabel PNG Files (*.png);;All Files (*)"
        )
        
        if file_path:
            gui_logger.info(f"File selected: {file_path}")
            self.load_xlabel_png(file_path)

    def load_xlabel_png(self, file_path):
        try:
            self.current_xlabel_metadata = xreader.read_xlabel_metadata_from_png(file_path)
            if self.current_xlabel_metadata:
                self.statusBar().showMessage(f"Loaded: {os.path.basename(file_path)} - XLabel v{self.current_xlabel_metadata.get('xlabel_version', 'Unknown')}")
                
                self.original_pixmap = QPixmap(file_path)
                if self.original_pixmap.isNull():
                    QMessageBox.warning(self, "Load Error", f"Could not load image data from '{file_path}'.")
                    self.current_image_path = None
                    self.current_xlabel_metadata = None
                    self.original_pixmap = None
                    return

                self.current_image_path = file_path
                self.display_image_with_annotations()
                self.update_annotation_list()
                self.update_class_list()
                self.save_as_action.setEnabled(True)
                # self.save_action will be enabled on modification
            else:
                # Check if it's a regular PNG without XLabel data
                try:
                    pm = QPixmap(file_path)
                    if not pm.isNull():
                         QMessageBox.information(self, "No XLabel Data", 
                                                f"'{os.path.basename(file_path)}' is a valid PNG but does not contain XLabel metadata (xlDa chunk).")
                         self.image_label.setPixmap(pm.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                         self.clear_lists_and_metadata()
                    else: # Not even a valid image
                        QMessageBox.warning(self, "Load Error", f"Could not load '{os.path.basename(file_path)}' as an image or XLabel PNG.")
                        self.clear_lists_and_metadata()
                except Exception as e_img: # Should be caught by xreader if it's trying to parse PNG structure
                    QMessageBox.warning(self, "Load Error", f"Error loading '{os.path.basename(file_path)}': {e_img}")
                    self.clear_lists_and_metadata()
                    
        except xreader.XLabelError as e:
            QMessageBox.critical(self, "XLabel Read Error", f"Error reading XLabel metadata from '{file_path}':\n{e}")
            self.clear_lists_and_metadata()
            gui_logger.error(f"XLabel read error: {e}", exc_info=True)
        except FileNotFoundError: # Should be caught by QFileDialog, but as a fallback
            QMessageBox.critical(self, "Error", f"File not found: {file_path}")
            self.clear_lists_and_metadata()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred while loading '{file_path}':\n{e}")
            self.clear_lists_and_metadata()
            gui_logger.error(f"Unexpected load error: {e}", exc_info=True)

    def display_image_with_annotations(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.image_label.setText("No image loaded.")
            return

        # Create a mutable copy to draw on
        pixmap_to_display = self.original_pixmap.copy()
        painter = QPainter(pixmap_to_display)
        
        if self.current_xlabel_metadata and self.current_xlabel_metadata.get("annotations"):
            pen = QPen(QColor("red")) # Default color for bboxes
            pen.setWidth(2)
            painter.setPen(pen)
            
            class_names = self.current_xlabel_metadata.get("class_names", [])

            for ann in self.current_xlabel_metadata["annotations"]:
                bbox = ann.get("bbox")
                if bbox and len(bbox) == 4:
                    x, y, w, h = bbox
                    painter.drawRect(QRect(int(x), int(y), int(w), int(h)))
                    
                    # Draw class name label near the bbox
                    class_id = ann.get("class_id")
                    label_text = f"Obj {ann_idx}" # Fallback
                    if class_id is not None and 0 <= class_id < len(class_names):
                        label_text = class_names[class_id]
                    
                    painter.drawText(int(x), int(y) - 5, label_text) # Draw text above the box
        
        painter.end()
        self.image_label.setPixmap(pixmap_to_display.scaled(
            self.image_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))

    def update_annotation_list(self):
        self.annotation_list_widget.clear()
        if self.current_xlabel_metadata and self.current_xlabel_metadata.get("annotations"):
            class_names = self.current_xlabel_metadata.get("class_names", [])
            for idx, ann in enumerate(self.current_xlabel_metadata["annotations"]):
                class_id = ann.get("class_id")
                class_name = "Unknown"
                if class_id is not None and 0 <= class_id < len(class_names):
                    class_name = class_names[class_id]
                
                bbox_str = "N/A"
                if ann.get("bbox"):
                    bbox_str = ", ".join(map(str, ann["bbox"]))
                
                item_text = f"[{idx}] {class_name} - BBox: [{bbox_str}]"
                if "score" in ann:
                    item_text += f" (Score: {ann['score']:.2f})"
                
                self.annotation_list_widget.addItem(QListWidgetItem(item_text))
    
    def update_class_list(self):
        self.class_list_widget.clear()
        if self.current_xlabel_metadata and self.current_xlabel_metadata.get("class_names"):
            for idx, name in enumerate(self.current_xlabel_metadata.get("class_names", [])):
                self.class_list_widget.addItem(QListWidgetItem(f"[{idx}] {name}"))

    def clear_lists_and_metadata(self):
        self.current_image_path = None
        self.current_xlabel_metadata = None
        self.original_pixmap = None
        self.image_label.setText("Open an XLabel PNG file to view.")
        self.annotation_list_widget.clear()
        self.class_list_widget.clear()
        self.save_action.setEnabled(False)
        self.save_as_action.setEnabled(False)
        self.statusBar().showMessage("Ready")


    def save_file(self):
        # Placeholder - To be implemented
        # This should save modifications to self.current_image_path
        if not self.current_image_path or not self.current_xlabel_metadata:
            QMessageBox.information(self, "Save Error", "No XLabel data loaded to save.")
            return
        gui_logger.info(f"Placeholder: Save triggered for {self.current_image_path}")
        QMessageBox.information(self, "Save", "Save functionality not yet fully implemented.")
        # Call xcreator.add_xlabel_metadata_to_png(self.current_image_path, self.current_image_path, self.current_xlabel_metadata, overwrite=True)
        # Need to handle image source if original was not PNG. For now, assume we save over the loaded PNG.

    def save_file_as(self):
        # Placeholder - To be implemented
        if not self.current_xlabel_metadata: # Check metadata, not just path, as a regular PNG might be loaded
            QMessageBox.information(self, "Save As Error", "No XLabel data loaded to save.")
            return

        # Determine the source image for pixel data.
        # If original was not PNG, we need to save a new PNG.
        # If original was XLabel PNG, we use its path as a basis.
        source_image_for_pixels = self.current_image_path # This is the path to the currently loaded XLabel PNG
        if not source_image_for_pixels: # Should not happen if save_as_action is enabled correctly
             QMessageBox.critical(self, "Save As Error", "Internal error: No source image path available.")
             return

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save XLabel PNG As...", 
            os.path.basename(self.current_image_path if self.current_image_path else "untitled.png"), # Suggest current name
            "XLabel PNG Files (*.png);;All Files (*)"
        )
        
        if file_path:
            gui_logger.info(f"Placeholder: Save As triggered for: {file_path}")
            try:
                # Ensure the output path has a .png extension
                if not file_path.lower().endswith(".png"):
                    file_path += ".png"
                
                # In a real scenario:
                # 1. If the original loaded image (self.current_image_path) was NOT a PNG,
                #    we'd need to load its pixel data again (e.g. from a JPG) to embed into the new PNG.
                #    For this MVP, we assume self.current_image_path IS the image with pixels.
                # 2. We use self.current_xlabel_metadata which holds the annotation data.
                
                # The xcreator function needs the path to the *source image for pixels*.
                # And the metadata to embed.
                xcreator.add_xlabel_metadata_to_png(
                    source_image_for_pixels, # Path of the image whose pixels will be used
                    file_path,               # New output path for the XLabel PNG
                    self.current_xlabel_metadata, 
                    overwrite=True # QFileDialog for save usually implies overwrite intention
                )
                self.statusBar().showMessage(f"Saved XLabel data to: {file_path}")
                # Optionally, update current_image_path to the new path if we want "Save" to now use it
                # self.current_image_path = file_path 
                # self.save_action.setEnabled(False) # If we consider "Save As" to clear modified state
            except xcreator.XLabelError as e:
                QMessageBox.critical(self, "Save Error", f"Could not save XLabel PNG to '{file_path}':\n{e}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"An unexpected error occurred while saving to '{file_path}':\n{e}")


    def show_about_dialog(self):
        QMessageBox.about(
            self, 
            "About XLabel",
            "<b>XLabel - Annotation Tool</b><br><br>"
            "Version 0.1.0 (GUI Prototype)<br>"
            "Embed and manage image annotations directly within PNG files.<br><br>"
            "Created by VoxleOne & Copilot (AI Collaborator).<br>"
            "Based on the XLabel Python CLI and core libraries."
        )

    # Override closeEvent to confirm exit if there are unsaved changes (later)
    # def closeEvent(self, event):
    #     if self.is_modified: # Need a flag for this
    #         reply = QMessageBox.question(self, 'Confirm Exit', 
    #                                      "There are unsaved changes. Are you sure you want to exit?",
    #                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
    #                                      QMessageBox.StandardButton.No)
    #         if reply == QMessageBox.StandardButton.Yes:
    #             event.accept()
    #         else:
    #             event.ignore()
    #     else:
    #         event.accept()

    # Override resizeEvent to rescale the image (if needed, or handle in a layout)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.display_image_with_annotations() # Re-scale and re-draw


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Basic styling (optional, can be expanded)
    # app.setStyle("Fusion") # Or "Windows", "macOS" depending on platform for more native look
    # You can also use QSS (Qt Style Sheets) for custom styling
    # Example: app.setStyleSheet("QMainWindow { background-color: #f0f0f0; } QLabel { font-size: 10pt; }")

    main_window = XLabelMainWindow()
    main_window.show()
    sys.exit(app.exec())
