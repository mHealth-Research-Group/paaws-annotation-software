import json

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class TimelineWidget(QWidget):
    def __init__(self, parent=None, show_position=False, is_main_timeline=True):
        super().__init__(parent)
        self.app = parent
        self.show_position = show_position
        self.is_main_timeline = is_main_timeline
        self.setMinimumHeight(60)
        self.dragging = None

        self.hover_edge = None
        self.hover_annotation = None
        self.hover_pos = None

        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if not hasattr(self.app, "media_player"):
            return

        duration = self.app.media_player["_duration"] / 1000 or 1
        x = event.position().x()
        y = event.position().y()

        self.dragging = None

        if self.is_main_timeline:
            zoom_start_x = self.app.zoom_start * self.width()
            zoom_end_x = self.app.zoom_end * self.width()

            if abs(x - zoom_start_x) < 5:
                self.dragging = "zoom_start"
                self.update()
                return
            elif abs(x - zoom_end_x) < 5:
                self.dragging = "zoom_end"
                self.update()
                return

        annotation_bar_height = self.height() * 0.4
        annotation_bar_y = (self.height() - annotation_bar_height) / 2
        if annotation_bar_y <= y <= (annotation_bar_y + annotation_bar_height):
            for annotation in reversed(self.app.annotations):
                start_x, end_x = self._get_annotation_screen_coords(annotation, duration)

                if end_x < 0 or start_x > self.width():
                    continue

                start_x = max(0, min(start_x, self.width()))
                end_x = max(0, min(end_x, self.width()))

                if abs(x - end_x) < 5:
                    self.dragging = ("end", annotation)
                    self.update()
                    return
                elif abs(x - start_x) < 5:
                    self.dragging = ("start", annotation)
                    self.update()
                    return

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseMoveEvent(self, event):
        if not hasattr(self.app, "media_player"):
            return

        duration = self.app.media_player["_duration"] / 1000 or 1
        x = event.position().x()

        if self.dragging:
            if self.dragging in ["zoom_start", "zoom_end"]:
                width_percent = max(0.0, min(1.0, x / self.width()))
                min_zoom_width = 0.01

                if self.dragging == "zoom_start":
                    if width_percent < self.app.zoom_end - min_zoom_width:
                        self.app.zoom_start = width_percent
                    else:
                        self.app.zoom_start = self.app.zoom_end - min_zoom_width
                else:
                    if width_percent > self.app.zoom_start + min_zoom_width:
                        self.app.zoom_end = width_percent
                    else:
                        self.app.zoom_end = self.app.zoom_start + min_zoom_width

                self.app.timeline_widget.update()
                self.app.second_timeline_widget.update()
                return

            elif isinstance(self.dragging, tuple):
                edge, annotation = self.dragging
                if self.is_main_timeline:
                    new_time = (x / self.width()) * duration
                else:
                    visible_duration = (self.app.zoom_end - self.app.zoom_start) * duration
                    visible_start = self.app.zoom_start * duration
                    if visible_duration <= 0:
                        return
                    new_time = visible_start + (x / self.width()) * visible_duration

                sorted_annotations = sorted(self.app.annotations, key=lambda x: x.start_time)
                current_index = -1
                for idx, ann in enumerate(sorted_annotations):
                    if ann.id == annotation.id:
                        current_index = idx
                        break

                if current_index == -1:
                    return

                min_duration = 0.05

                if edge == "start":
                    if annotation.end_time - new_time < min_duration:
                        new_time = annotation.end_time - min_duration

                    if current_index > 0:
                        prev_annotation = sorted_annotations[current_index - 1]
                        if new_time < prev_annotation.end_time:
                            new_time = prev_annotation.end_time

                    annotation.start_time = max(0, new_time)

                else:
                    if new_time - annotation.start_time < min_duration:
                        new_time = annotation.start_time + min_duration

                    if current_index < len(sorted_annotations) - 1:
                        next_annotation = sorted_annotations[current_index + 1]
                        if new_time > next_annotation.start_time:
                            new_time = next_annotation.start_time

                    annotation.end_time = min(duration, new_time)

                self.app.updateAnnotationTimeline()
        else:
            old_hover_edge = self.hover_edge
            old_hover_annotation = self.hover_annotation

            found_edge = None
            found_body = None

            modifiers = event.modifiers()
            is_modifier_pressed = bool(
                modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
            )

            annotation_bar_height = self.height() * 0.4
            annotation_bar_y = (self.height() - annotation_bar_height) / 2
            y = event.position().y()
            is_over_bar = annotation_bar_y <= y <= (annotation_bar_y + annotation_bar_height)

            if is_over_bar:
                for annotation in reversed(self.app.annotations):
                    start_x, end_x = self._get_annotation_screen_coords(annotation, duration)

                    if end_x < 0 or start_x > self.width():
                        continue

                    if abs(x - start_x) < 5:
                        found_edge = ("start", annotation)
                        break
                    if abs(x - end_x) < 5:
                        found_edge = ("end", annotation)
                        break

                    if is_modifier_pressed and start_x <= x <= end_x and not found_body:
                        found_body = annotation

            self.hover_edge = found_edge
            self.hover_annotation = found_body if not self.hover_edge and is_modifier_pressed else None

            if self.hover_edge:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

            if self.hover_annotation:
                self.hover_pos = event.position()
            else:
                self.hover_pos = None

            if old_hover_edge != self.hover_edge or old_hover_annotation != self.hover_annotation:
                self.update()

    def leaveEvent(self, event):
        if self.hover_edge or self.hover_annotation or self.hover_pos:
            self.hover_edge = None
            self.hover_annotation = None
            self.hover_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not hasattr(self.app, "media_player"):
            painter.fillRect(self.rect(), QColor(20, 20, 20))
            return

        duration = self.app.media_player["_duration"] / 1000 or 1

        visible_start = 0.0
        visible_duration = duration
        if not self.is_main_timeline:
            visible_start = self.app.zoom_start * duration
            visible_duration = (self.app.zoom_end - self.app.zoom_start) * duration
            if visible_duration <= 0:
                visible_duration = 1

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 20, 20))
        painter.drawRect(self.rect())

        if duration > 0:
            position_ms = self.app.media_player["_position"]
            if self.is_main_timeline:
                painter.setPen(QPen(QColor(60, 60, 60), 1))
                y_pos = self.height() / 2
                painter.drawLine(QPointF(0, y_pos), QPointF(self.width(), y_pos))
                current_pos_x = (position_ms / (duration * 1000)) * self.width()
            else:
                if visible_duration > 0:
                    relative_pos_percent = (position_ms / 1000 - visible_start) / visible_duration
                    progress_width = relative_pos_percent * self.width()
                    if 0 <= progress_width <= self.width():
                        progress_gradient = QLinearGradient(0, 0, progress_width, 0)
                        progress_gradient.setColorAt(0, QColor(60, 60, 60))
                        progress_gradient.setColorAt(1, QColor(80, 80, 80))
                        painter.setBrush(progress_gradient)
                        painter.drawRect(QRectF(0, 0, progress_width, self.height()))
                current_pos_x = -1

            painter.setPen(QPen(QColor(200, 200, 200), 1))
            if 0 <= current_pos_x <= self.width():
                painter.drawLine(QPointF(current_pos_x, 0), QPointF(current_pos_x, self.height()))

            if self.is_main_timeline:
                zoom_start_x = self.app.zoom_start * self.width()
                zoom_end_x = self.app.zoom_end * self.width()

                painter.setPen(QPen(QColor(255, 0, 0, 150), 2))
                painter.drawLine(QPointF(zoom_start_x, 0), QPointF(zoom_start_x, self.height()))
                painter.drawLine(QPointF(zoom_end_x, 0), QPointF(zoom_end_x, self.height()))

                overlay_color = QColor(0, 0, 0, 80)
                painter.fillRect(QRectF(0, 0, zoom_start_x, self.height()), overlay_color)
                painter.fillRect(QRectF(zoom_end_x, 0, self.width() - zoom_end_x, self.height()), overlay_color)

        def draw_annotation_block(start_x, end_x, annotation=None, is_dragging=False, is_edge_hover=False):
            block_width = max(1, end_x - start_x)

            height = self.height() * 0.4
            y_pos = (self.height() - height) / 2

            base_color = QColor("#808080")
            if annotation and annotation.comments:
                try:
                    comment_data = json.loads(annotation.comments[0]["body"])
                    posture = next(
                        (item.get("selectedValue") for item in comment_data if item.get("category") == "POSTURE"), None
                    )
                    if posture:
                        color_str = self.app.annotation_manager.get_posture_color(posture)
                        base_color = QColor(color_str)
                except Exception as e:
                    print(f"Error getting annotation color: {e}")

            alpha = 180 if is_dragging else (160 if is_edge_hover else 140)
            color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(start_x, y_pos, block_width, height))

            if is_dragging or is_edge_hover:
                painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
                marker_height = 8
                edge_type = None
                if is_dragging and isinstance(self.dragging, tuple):
                    edge_type = self.dragging[0]
                elif is_edge_hover and isinstance(self.hover_edge, tuple):
                    edge_type = self.hover_edge[0]

                if edge_type == "start":
                    painter.drawLine(QPointF(start_x, y_pos - marker_height), QPointF(start_x, y_pos))
                    painter.drawLine(QPointF(start_x, y_pos + height), QPointF(start_x, y_pos + height + marker_height))
                if edge_type == "end":
                    painter.drawLine(QPointF(end_x, y_pos - marker_height), QPointF(end_x, y_pos))
                    painter.drawLine(QPointF(end_x, y_pos + height), QPointF(end_x, y_pos + height + marker_height))

        if hasattr(self.app, "current_annotation") and self.app.current_annotation:
            start_x, _ = self._get_annotation_screen_coords(self.app.current_annotation, duration)
            if 0 <= start_x <= self.width():
                painter.setPen(QPen(QColor(0, 255, 0, 200), 2))
                painter.drawLine(QPointF(start_x, 0), QPointF(start_x, self.height()))

        if hasattr(self.app, "annotations"):
            for annotation in self.app.annotations:
                start_x, end_x = self._get_annotation_screen_coords(annotation, duration)

                if end_x < 0 or start_x > self.width():
                    continue

                clamped_start_x = max(0, start_x)
                clamped_end_x = min(end_x, self.width())
                block_width = clamped_end_x - clamped_start_x

                if block_width >= 0:
                    is_dragging_this = (
                        self.dragging and isinstance(self.dragging, tuple) and self.dragging[1].id == annotation.id
                    )
                    is_hovering_this_edge = (
                        not self.dragging and self.hover_edge and self.hover_edge[1].id == annotation.id
                    )
                    draw_annotation_block(
                        clamped_start_x,
                        clamped_end_x,
                        annotation=annotation,
                        is_dragging=is_dragging_this,
                        is_edge_hover=is_hovering_this_edge,
                    )

                if block_width > 50:
                    painter.setPen(QPen(QColor(255, 255, 255)))
                    try:
                        comment_data = json.loads(annotation.comments[0]["body"])
                        posture = next(
                            (item.get("selectedValue") for item in comment_data if item.get("category") == "POSTURE"),
                            "",
                        )
                        hlb_list = next(
                            (
                                item.get("selectedValue")
                                for item in comment_data
                                if item.get("category") == "HIGH LEVEL BEHAVIOR"
                            ),
                            [],
                        )
                        hlb = hlb_list if isinstance(hlb_list, list) else []

                        text = ", ".join(hlb[:2]) + ("..." if len(hlb) > 2 else "")
                        full_text = f"{posture} - {text}" if posture and text else posture or text

                        block_height = self.height() * 0.4
                        block_y_pos = (self.height() - block_height) / 2
                        text_rect = QRectF(clamped_start_x + 4, block_y_pos, block_width - 8, block_height)
                        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, full_text)
                    except Exception as e:
                        print(f"Error displaying annotation text: {e}")

        if self.hover_annotation and self.hover_pos:
            self._draw_hover_tooltip(painter, self.hover_pos, self.hover_annotation)

    def _get_annotation_screen_coords(self, annotation, duration):
        if duration <= 0:
            return -1, -1

        if self.is_main_timeline:
            start_x = (annotation.start_time / duration) * self.width()
            end_x = (annotation.end_time / duration) * self.width()
        else:
            visible_duration = (self.app.zoom_end - self.app.zoom_start) * duration
            visible_start = self.app.zoom_start * duration
            if visible_duration <= 0:
                return -1, -1
            start_x = ((annotation.start_time - visible_start) / visible_duration) * self.width()
            end_x = ((annotation.end_time - visible_start) / visible_duration) * self.width()
        return start_x, end_x

    def _format_annotation_for_tooltip(self, annotation):
        if not annotation or not annotation.comments:
            return ""

        try:
            comment_list = json.loads(annotation.comments[0]["body"])

            def find_value(category_name):
                return next(
                    (item.get("selectedValue") for item in comment_list if item.get("category") == category_name), None
                )

            tooltip_items = [
                ("Posture", find_value("POSTURE")),
                ("Behavior", find_value("HIGH LEVEL BEHAVIOR")),
                ("PA Type", find_value("PHYSICAL ACTIVITY TYPE")),
                ("Params", find_value("BEHAVIORAL PARAMETERS")),
                ("Situation", find_value("EXPERIMENTAL SITUATION")),
                ("Notes", find_value("SPECIAL NOTES")),
            ]

            parts = []
            for label, value in tooltip_items:
                if not value:
                    continue

                if isinstance(value, list):
                    valid_values = [str(v) for v in value if v]
                    if not valid_values:
                        continue
                    formatted_value = ", ".join(valid_values)
                else:
                    formatted_value = str(value)

                parts.append(f"{label}: {formatted_value}")

            if not parts:
                return "No Labels Set"

            return " | ".join(parts)

        except (json.JSONDecodeError, IndexError, KeyError, TypeError) as e:
            print(f"Error formatting tooltip: {e}")
            return "Invalid Annotation Data"

    def _draw_hover_tooltip(self, painter, position, annotation):
        text = self._format_annotation_for_tooltip(annotation)
        if not text:
            return

        padding = 8
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        text_rect = painter.fontMetrics().boundingRect(text)
        tooltip_rect = text_rect.adjusted(-padding, -padding, padding, padding)

        x = position.x() + 15
        y = position.y() - tooltip_rect.height() - 15

        if x + tooltip_rect.width() > self.width():
            x = self.width() - tooltip_rect.width() - 5
        if x < 5:
            x = 5
        if y < 5:
            y = position.y() + 15

        tooltip_rect.moveTo(int(x), int(y))

        painter.setBrush(QColor(0, 0, 0, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(tooltip_rect, 5, 5)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(tooltip_rect, Qt.AlignmentFlag.AlignCenter, text)
