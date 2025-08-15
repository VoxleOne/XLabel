from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider, QDoubleSpinBox, QGroupBox
)
from PySide6.QtCore import Qt
from xlabel.model import ModelManager

class ModelSettingsDialog(QDialog):
    """
    A dialog for configuring the model manager's parameters.
    """
    def __init__(self, model_manager: ModelManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Settings")
        self.setMinimumWidth(400)
        
        self.model_manager = model_manager

        # --- Create Widgets ---
        # Model Selection
        model_group = QGroupBox("Model Selection")
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Active Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(self.model_manager.available_models.keys())
        self.model_combo.setCurrentText(self.model_manager.selected_model_name)
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)

        # Thresholds
        threshold_group = QGroupBox("Inference Parameters")
        threshold_layout = QVBoxLayout()
        
        # Confidence Threshold
        self.conf_label = QLabel(f"Confidence Threshold: {self.model_manager.confidence_threshold:.2f}")
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(int(self.model_manager.confidence_threshold * 100))
        
        # IOU Threshold
        self.iou_label = QLabel(f"IOU Threshold: {self.model_manager.iou_threshold:.2f}")
        self.iou_slider = QSlider(Qt.Horizontal)
        self.iou_slider.setRange(0, 100)
        self.iou_slider.setValue(int(self.model_manager.iou_threshold * 100))

        threshold_layout.addWidget(self.conf_label)
        threshold_layout.addWidget(self.conf_slider)
        threshold_layout.addWidget(self.iou_label)
        threshold_layout.addWidget(self.iou_slider)
        threshold_group.setLayout(threshold_layout)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(model_group)
        main_layout.addWidget(threshold_group)
        main_layout.addStretch()
        main_layout.addWidget(self.button_box)
        
        # --- Connections ---
        self.conf_slider.valueChanged.connect(lambda val: self.conf_label.setText(f"Confidence Threshold: {val/100:.2f}"))
        self.iou_slider.valueChanged.connect(lambda val: self.iou_label.setText(f"IOU Threshold: {val/100:.2f}"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def accept(self):
        """Apply the settings to the model manager."""
        # Set new values on the manager
        new_model = self.model_combo.currentText()
        if new_model != self.model_manager.selected_model_name:
            self.model_manager.load_model(new_model)
            
        self.model_manager.set_confidence_threshold(self.conf_slider.value() / 100.0)
        self.model_manager.set_iou_threshold(self.iou_slider.value() / 100.0)
        
        super().accept()
