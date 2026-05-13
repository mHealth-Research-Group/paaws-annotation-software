from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class CustomSlider(QWidget):
    """A custom slider widget to replace QSlider for more control over appearance."""

    sliderMoved = pyqtSignal(int)
    sliderPressed = pyqtSignal()
    sliderReleased = pyqtSignal()
    valueChanged = pyqtSignal(int)

    def __init__(self, orientation, show_handle=True, parent=None):
        super().__init__(parent)
        self._orientation = orientation
        self._show_handle = show_handle
        self._min = 0
        self._max = 100
        self._value = 0
        self._is_dragging = False

        self.setMinimumHeight(20)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.groove_color = QColor("#404040")
        self.progress_color = QColor("#4a90e2")
        self.handle_color = QColor("#4a90e2")
        self.handle_border_color = QColor("#2b2b2b")
        self.handle_radius = 8
        self.groove_height = 4

    def value(self):
        return self._value

    def minimum(self):
        return self._min

    def maximum(self):
        return self._max

    def isSliderDown(self):
        return self._is_dragging

    def setRange(self, min_val, max_val):
        self._min = min_val
        self._max = max_val if max_val > min_val else min_val + 1
        self.setValue(self._value)
        self.update()

    def setValue(self, value):
        clamped_value = max(self._min, min(value, self._max))
        if self._value != clamped_value:
            self._value = clamped_value
            self.valueChanged.emit(self._value)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        groove_y = (rect.height() - self.groove_height) // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.groove_color))
        painter.drawRoundedRect(0, groove_y, rect.width(), self.groove_height, 2, 2)
        progress_width = self._pos_from_value()
        if progress_width > 0:
            painter.setBrush(QBrush(self.progress_color))
            painter.drawRoundedRect(0, groove_y, progress_width, self.groove_height, 2, 2)
        if self._show_handle:
            handle_x = progress_width
            handle_y = rect.height() // 2
            painter.setPen(QPen(self.handle_border_color, 2))
            painter.setBrush(QBrush(self.handle_color))
            painter.drawEllipse(QPoint(handle_x, handle_y), self.handle_radius, self.handle_radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.sliderPressed.emit()
            self._is_dragging = True
            self._update_value_from_pos(event.position())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._update_value_from_pos(event.position())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.sliderReleased.emit()
            event.accept()

    def _pos_from_value(self):
        """Converts slider value to the center position of the handle."""
        duration = self._max - self._min
        if duration == 0:
            return 0

        ratio = (self._value - self._min) / duration
        position = ratio * self.width()
        return int(position)

    # --- MODIFIED ---
    def _value_from_pos(self, pos):
        width = self.width()
        ratio = pos.x() / width if width > 0 else 0
        ratio = max(0.0, min(1.0, ratio))
        duration = self._max - self._min
        value = self._min + ratio * duration
        return int(value)

    def _update_value_from_pos(self, pos):
        new_value = self._value_from_pos(pos)
        if self.value() != new_value:
            self.setValue(new_value)
            self.sliderMoved.emit(new_value)
