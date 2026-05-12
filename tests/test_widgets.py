import pytest
import json
from unittest.mock import MagicMock

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QWidget
from src.widgets import TimelineWidget

_mock_annotation_counter = 0


class MockAnnotation:
    def __init__(self, start, end, comments=None):
        global _mock_annotation_counter
        _mock_annotation_counter += 1
        self.id = _mock_annotation_counter
        self.start_time = start
        self.end_time = end
        self.comments = comments if comments is not None else []


class MockApp(QWidget):
    def __init__(self):
        super().__init__()
        self.media_player = {"_duration": 600000, "_position": 0}
        self.zoom_start = 0.0
        self.zoom_end = 1.0
        self.annotations = []
        self.current_annotation = None
        self.annotation_manager = MagicMock()
        self.annotation_manager.get_posture_color.return_value = "#ff0000"
        self.timeline_widget = MagicMock()
        self.second_timeline_widget = MagicMock()
        self.updateAnnotationTimeline = MagicMock()


@pytest.fixture
def mock_app():
    return MockApp()


@pytest.fixture
def main_timeline(qtbot, mock_app):
    widget = TimelineWidget(parent=mock_app, is_main_timeline=True)
    qtbot.addWidget(widget)
    widget.resize(800, 60)
    return widget


@pytest.fixture
def zoomed_timeline(qtbot, mock_app):
    widget = TimelineWidget(parent=mock_app, is_main_timeline=False)
    qtbot.addWidget(widget)
    widget.resize(800, 60)
    return widget


def test_timeline_widget_initialization(main_timeline, mock_app):
    assert main_timeline.app == mock_app
    assert main_timeline.is_main_timeline is True


def test_paint_event_runs_without_error(main_timeline, mock_app):
    posture_comment_data = [{"category": "POSTURE", "selectedValue": "Standing"}]
    comment_body_string = json.dumps(posture_comment_data)
    full_comment_structure = [{"body": comment_body_string}]
    mock_app.annotations = [MockAnnotation(10, 20, comments=full_comment_structure)]
    mock_app.media_player["_position"] = 15000
    main_timeline.update()


def test_drag_annotation_start_edge(qtbot, zoomed_timeline, mock_app):
    duration_sec = mock_app.media_player["_duration"] / 1000
    annotation = MockAnnotation(start=100, end=200)
    mock_app.annotations = [annotation]
    mock_app.zoom_start = 0.0
    mock_app.zoom_end = 0.5
    start_x = int(800 * (100 / (duration_sec * 0.5)))
    drag_to_x = start_x - 60
    qtbot.mousePress(zoomed_timeline, Qt.MouseButton.LeftButton, pos=QPoint(start_x, 30))
    qtbot.mouseMove(zoomed_timeline, pos=QPoint(drag_to_x, 30))
    qtbot.mouseRelease(zoomed_timeline, Qt.MouseButton.LeftButton, pos=QPoint(drag_to_x, 30))
    assert annotation.start_time == pytest.approx(77.25, abs=1)
    mock_app.updateAnnotationTimeline.assert_called()


def test_drag_zoom_handle(qtbot, main_timeline, mock_app):
    assert mock_app.zoom_end == 1.0
    start_x = 800
    drag_to_x = 400
    qtbot.mousePress(main_timeline, Qt.MouseButton.LeftButton, pos=QPoint(start_x, 30))
    qtbot.mouseMove(main_timeline, pos=QPoint(drag_to_x, 30))
    qtbot.mouseRelease(main_timeline, Qt.MouseButton.LeftButton, pos=QPoint(drag_to_x, 30))
    assert mock_app.zoom_end == pytest.approx(0.5)
