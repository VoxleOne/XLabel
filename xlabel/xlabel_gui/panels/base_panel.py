from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect, Property

class BasePanel(QWidget):
    """
    A base widget that provides a physics-based slide-in/slide-out animation.
    Panels for specific annotation modes should inherit from this class.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hide()  # Start hidden

        # The animation will target the panel's geometry
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(450)  # Animation duration in milliseconds
        # This easing curve starts fast and decelerates, creating the "gentle stop" effect
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    def slide_in(self):
        """Animates the panel sliding into view from the right."""
        if self.isVisible():
            return

        parent_rect = self.parent().rect()
        # Start the panel off-screen to the right
        start_geom = QRect(parent_rect.width(), 0, parent_rect.width(), parent_rect.height())
        # The final position is filling the parent widget
        end_geom = parent_rect

        self.setGeometry(start_geom)
        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        self.show()
        self.animation.start()

    def slide_out(self):
        """Animates the panel sliding out of view to the right."""
        if not self.isVisible():
            return

        parent_rect = self.parent().rect()
        start_geom = self.geometry()
        end_geom = QRect(parent_rect.width(), 0, parent_rect.width(), parent_rect.height())

        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        # When the animation finishes, hide the widget
        self.animation.finished.connect(self.hide)
        self.animation.start()