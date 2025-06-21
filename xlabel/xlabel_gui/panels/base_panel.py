from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, QRect, Property, Signal, QPoint, 
    QSequentialAnimationGroup
)
from PySide6.QtGui import QColor, QMoveEvent, QPainter

class BasePanel(QWidget):
    moved = Signal(QPoint)
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hide()

        self.ribbon_color = QColor("transparent")
        self.ribbon_width = 5
        
        self.sliding_background_color = QColor(80, 80, 80, 38)
        self.final_background_color = QColor(80, 80, 80, 8)
        self._background_color = self.final_background_color

        self.slide_anim = QPropertyAnimation(self, b"geometry")
        self.slide_anim.setDuration(700)
        self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_in_anim = QPropertyAnimation(self, b"background")
        self.fade_in_anim.setDuration(400)
        
        self.fade_out_anim = QPropertyAnimation(self, b"background")
        self.fade_out_anim.setDuration(200)

        self.current_anim_group = None

    def _get_background_color(self): return self._background_color
    def _set_background_color(self, color: QColor):
        self._background_color = color
        self.update()
    background = Property(QColor, _get_background_color, _set_background_color)

    def paintEvent(self, event):
        """
        --- THE FIX ---
        This method is essential for making the panel visible. It draws the
        semi-transparent background and the colored ribbon. Without this,
        the widget is effectively invisible, which can cause Qt to handle
        its animations and events unreliably.
        """
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Draw the semi-transparent background that fades in/out
        painter.fillRect(self.rect(), self._background_color)
        
        # Draw the colored ribbon on the left edge
        if self.ribbon_color.isValid():
            painter.fillRect(0, 0, self.ribbon_width, self.height(), self.ribbon_color)

    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        self.moved.emit(self.pos())

    def set_ribbon_color(self, color: QColor):
        self.ribbon_color = color

    def slide_in(self):
        if self.isVisible():
            self.animation_finished.emit()
            return
        
        parent_rect = self.parent().rect()
        start_geom = QRect(parent_rect.width(), 0, parent_rect.width(), parent_rect.height())
        end_geom = parent_rect

        self.setGeometry(start_geom)
        self.background = self.sliding_background_color
        self.show()

        self.slide_anim.setStartValue(start_geom)
        self.slide_anim.setEndValue(end_geom)
        self.fade_in_anim.setStartValue(self.sliding_background_color)
        self.fade_in_anim.setEndValue(self.final_background_color)

        self.current_anim_group = QSequentialAnimationGroup(self)
        self.current_anim_group.addAnimation(self.slide_anim)
        self.current_anim_group.addAnimation(self.fade_in_anim)
        self.current_anim_group.finished.connect(self.animation_finished)
        self.current_anim_group.start()

    def slide_out(self):
        if not self.isVisible():
            self.animation_finished.emit()
            return

        parent_rect = self.parent().rect()
        start_geom = self.geometry()
        end_geom = QRect(parent_rect.width(), 0, self.width(), self.height())
        
        self.fade_out_anim.setStartValue(self._background_color)
        self.fade_out_anim.setEndValue(self.sliding_background_color)
        self.slide_anim.setStartValue(start_geom)
        self.slide_anim.setEndValue(end_geom)

        self.current_anim_group = QSequentialAnimationGroup(self)
        self.current_anim_group.addAnimation(self.fade_out_anim)
        self.current_anim_group.addAnimation(self.slide_anim)
        self.current_anim_group.finished.connect(self.hide)
        self.current_anim_group.finished.connect(self.animation_finished)
        self.current_anim_group.start()