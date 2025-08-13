from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QColorDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ..panels import KeypointsPanel


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
