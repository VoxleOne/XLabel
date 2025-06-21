from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QPainter, QPen, QPolygonF, QResizeEvent, QColor
from PySide6.QtCore import Qt, QRect, QPoint

class ImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._annotations_to_draw = {}
        self._selected_rect_index = None
        self.setMinimumSize(400, 300)

        self._drawing_offset = QPoint(0, 0)
        self._active_panel = None
        self._transitioning = False
        self._annotation_list_widget = None
        
        self._panel_in_transition = None

    def set_annotation_list(self, list_widget):
        self._annotation_list_widget = list_widget

    def update_annotations_display(self):
        if not self._active_panel:
            return
        
        current_annotations = self._active_panel.get_annotations()
        if self._annotation_list_widget:
            self._annotation_list_widget.set_annotations(current_annotations)
        
        self.update()

    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def clear_active_panel(self):
        if self._active_panel:
            self._active_panel.hide()
        self._active_panel = None
        self._transitioning = False
        self.set_annotations_to_draw({})
        if self._annotation_list_widget:
            self._annotation_list_widget.set_annotations({})

    def set_selected_rect(self, idx):
        self._selected_rect_index = idx
        self.update()

    def set_drawing_offset(self, offset: QPoint):
        self._drawing_offset = offset
        self.update()

    def set_annotations_to_draw(self, annotations):
        self._annotations_to_draw.clear()
        if isinstance(annotations, list):
            self._annotations_to_draw = {'completed': annotations}
        elif isinstance(annotations, dict):
            self._annotations_to_draw = annotations
        self.update()

    def transition_to(self, new_panel):
        if self._transitioning or self._active_panel is new_panel:
            return
        self._transitioning = True

        old_panel = self._active_panel
        self._panel_in_transition = old_panel
        self._active_panel = new_panel

        if old_panel:
            old_panel.animation_finished.connect(self._start_slide_in)
            old_panel.moved.connect(self.set_drawing_offset)
            old_panel.slide_out()
        else:
            self._start_slide_in()
            
    def _start_slide_in(self):
        self._panel_in_transition = None
        self.set_annotations_to_draw({})
        if self._annotation_list_widget:
            self._annotation_list_widget.set_annotations({})

        if self.sender():
            self.sender().animation_finished.disconnect(self._start_slide_in)
            self.sender().moved.disconnect(self.set_drawing_offset)

        new_panel = self._active_panel
        if new_panel:
            new_panel.animation_finished.connect(self._on_transition_finished)
            new_panel.moved.connect(self.set_drawing_offset)
            new_panel.slide_in()
        else:
            self._on_transition_finished()

    def _on_transition_finished(self):
        if self.sender():
            self.sender().animation_finished.disconnect(self._on_transition_finished)
            self.sender().moved.disconnect(self.set_drawing_offset)
        
        self.set_drawing_offset(QPoint(0, 0))
        self._transitioning = False
        self.update_annotations_display()

        if self._active_panel:
            self._active_panel.setFocus()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self._active_panel and self._active_panel.isVisible():
            self._active_panel.setGeometry(self.rect())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if not self._pixmap: return

        panel_to_draw = self._panel_in_transition if self._panel_in_transition else self._active_panel

        if panel_to_draw:
            self._annotations_to_draw = panel_to_draw.get_annotations()
        else:
            self._annotations_to_draw = {}

        pixmap_scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset = QPoint((self.width() - pixmap_scaled.width()) // 2, (self.height() - pixmap_scaled.height()) // 2)
        painter.drawPixmap(offset, pixmap_scaled)
        
        painter.save()
        painter.translate(offset)
        scale_x = pixmap_scaled.width() / self._pixmap.width() if self._pixmap.width() > 0 else 1
        scale_y = pixmap_scaled.height() / self._pixmap.height() if self._pixmap.height() > 0 else 1
        painter.scale(scale_x, scale_y)
        
        painter.translate(self._drawing_offset)
        
        completed_annotations = self._annotations_to_draw.get('completed', [])
        
        for i, annotation in enumerate(completed_annotations):
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            if isinstance(annotation, QPixmap):
                painter.drawPixmap(0, 0, annotation)
                if i == self._selected_rect_index:
                    highlight_pixmap = QPixmap(annotation.size())
                    highlight_pixmap.fill(Qt.transparent)
                    p = QPainter(highlight_pixmap)
                    p.drawPixmap(0, 0, annotation)
                    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
                    p.fillRect(highlight_pixmap.rect(), QColor(255, 255, 0, 100))
                    p.end()
                    painter.drawPixmap(0, 0, highlight_pixmap)
            else:
                pen_width = 3 if i == self._selected_rect_index else 2
                pen_color = Qt.yellow if i == self._selected_rect_index else Qt.red
                pen = QPen(pen_color, pen_width / max(scale_x, scale_y))
                painter.setPen(pen)
                if isinstance(annotation, QRect):
                    painter.drawRect(annotation)
                elif isinstance(annotation, list) and annotation:
                    painter.drawPolygon(QPolygonF(annotation))
        
        active_annotation = self._annotations_to_draw.get('active')
        pen = QPen(Qt.cyan, 2 / max(scale_x, scale_y))
        painter.setPen(pen)

        if isinstance(active_annotation, QPixmap):
            painter.drawPixmap(0, 0, active_annotation)
        elif isinstance(active_annotation, QRect):
            painter.drawRect(active_annotation)
        elif isinstance(active_annotation, list) and active_annotation:
            painter.drawPoints(active_annotation)
            if len(active_annotation) > 1:
                painter.drawPolyline(QPolygonF(active_annotation))
            cursor_pos = self._annotations_to_draw.get('cursor_pos')
            if cursor_pos:
                painter.drawLine(active_annotation[-1], cursor_pos)

        painter.restore()
            
    def map_to_image(self, widget_point: QPoint):
        if not self._pixmap: return None
        pixmap_scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - pixmap_scaled.width()) // 2
        offset_y = (self.height() - pixmap_scaled.height()) // 2
        if not QRect(offset_x, offset_y, pixmap_scaled.width(), pixmap_scaled.height()).contains(widget_point):
            return None
        x = widget_point.x() - offset_x
        y = widget_point.y() - offset_y
        scale_x = self._pixmap.width() / pixmap_scaled.width() if pixmap_scaled.width() > 0 else 1
        scale_y = self._pixmap.height() / pixmap_scaled.height() if pixmap_scaled.height() > 0 else 1
        return QPoint(int(x * scale_x), int(y * scale_y))