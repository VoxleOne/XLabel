from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QPainter, QPen, QPolygonF, QResizeEvent, QColor, QBrush
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
        
        # --- START REFACTORED DRAWING LOGIC ---
        completed_annotations = self._annotations_to_draw.get('completed', [])
        
        # Keypoint-specific data
        completed_colors = self._annotations_to_draw.get('completed_colors', [])
        point_radius = self._annotations_to_draw.get('point_radius', 5)

        for i, annotation in enumerate(completed_annotations):
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            is_selected = (i == self._selected_rect_index)

            if isinstance(annotation, QPixmap): # MASK
                painter.drawPixmap(0, 0, annotation)
                if is_selected:
                    highlight_pixmap = QPixmap(annotation.size())
                    highlight_pixmap.fill(Qt.transparent)
                    p = QPainter(highlight_pixmap)
                    p.drawPixmap(0, 0, annotation)
                    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
                    p.fillRect(highlight_pixmap.rect(), QColor(255, 255, 0, 100))
                    p.end()
                    painter.drawPixmap(0, 0, highlight_pixmap)
            else: # BBOX, POLYGON, KEYPOINTS
                pen_width = 3 if is_selected else 2
                pen_color = Qt.yellow if is_selected else Qt.red
                pen = QPen(pen_color, pen_width / max(scale_x, scale_y))
                painter.setPen(pen)

                if isinstance(annotation, QRect): # BBOX
                    painter.drawRect(annotation)
                elif isinstance(annotation, list) and annotation and isinstance(annotation[0], QPoint): # POLYGON
                    painter.drawPolygon(QPolygonF(annotation))
                elif isinstance(annotation, list) and annotation and isinstance(annotation[0], dict): # KEYPOINTS (new)
                    # For completed keypoints, we draw them with their stored colors
                    point_colors = completed_colors[i] if i < len(completed_colors) else []
                    for p_idx, point_data in enumerate(annotation):
                        color = point_colors[p_idx] if p_idx < len(point_colors) else QColor(Qt.green)
                        painter.setBrush(QBrush(color))
                        painter.setPen(QPen(Qt.black, 1 / max(scale_x, scale_y)))
                        painter.drawEllipse(point_data['pos'], point_radius, point_radius)

        active_annotation = self._annotations_to_draw.get('active')
        if active_annotation:
            pen = QPen(Qt.cyan, 2 / max(scale_x, scale_y))
            painter.setPen(pen)

            if isinstance(active_annotation, QPixmap): # MASK
                painter.drawPixmap(0, 0, active_annotation)
            elif isinstance(active_annotation, QRect): # BBOX
                painter.drawRect(active_annotation)
            elif isinstance(active_annotation, list) and active_annotation and isinstance(active_annotation[0], QPoint): # POLYGON
                painter.drawPoints(active_annotation)
                if len(active_annotation) > 1:
                    painter.drawPolyline(QPolygonF(active_annotation))
                cursor_pos = self._annotations_to_draw.get('cursor_pos')
                if cursor_pos:
                    painter.drawLine(active_annotation[-1], cursor_pos)
            elif isinstance(active_annotation, list): # KEYPOINTS (active)
                active_colors = self._annotations_to_draw.get('active_colors', [])
                selected_idx = self._annotations_to_draw.get('selected_point_idx', -1)
                for i, point_data in enumerate(active_annotation):
                    color = active_colors[i] if i < len(active_colors) else self.point_color
                    painter.setBrush(QBrush(color))
                    
                    pen_color = Qt.yellow if i == selected_idx else Qt.black
                    painter.setPen(QPen(pen_color, 2 / max(scale_x, scale_y)))
                    painter.drawEllipse(point_data['pos'], point_radius, point_radius)
        # --- END REFACTORED DRAWING LOGIC ---

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