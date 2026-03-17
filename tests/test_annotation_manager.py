import pytest
import json
from unittest.mock import MagicMock, patch
from src.annotation_manager import AnnotationManager
from src.models import TimelineAnnotation

class MockApp:
    def __init__(self):
        self.annotations = []
        self.current_annotation = None
        self.media_player = {'_position': 0}
        self.updateAnnotationTimeline = MagicMock()
        self.setPosition = MagicMock()
        self.annotator_user_id = "test-uuid-1234"
        self.annotator_user_name = "Test User"

@pytest.fixture
def mock_app():
    return MockApp()

@pytest.fixture
def manager(mock_app):
    return AnnotationManager(mock_app)

def get_comment_value(comments, category_name):
    if not comments:
        return None
    try:
        comment_dict = comments[0]
        body_list = json.loads(comment_dict.get('body', '[]'))
        for item in body_list:
            if item.get('category') == category_name:
                return item.get('selectedValue')
    except (json.JSONDecodeError, IndexError, AttributeError):
        return None
    return None

def test_initialization(manager):
    assert manager.app is not None
    assert isinstance(manager.last_used_labels, dict)
    assert manager.last_used_labels["posture"] == ""
    assert isinstance(manager.posture_colors, dict)

def test_get_posture_color(manager):
    color1 = manager.get_posture_color("Sitting")
    assert color1.startswith("#")
    color2 = manager.get_posture_color("Sitting")
    assert color1 == color2
    color3 = manager.get_posture_color("Standing")
    assert color3 != color1
    assert manager.get_posture_color(None) == "#808080"
    assert manager.get_posture_color("") == "#808080"

def test_check_overlap(manager):
    manager.app.annotations = [TimelineAnnotation(start_time=10, end_time=20)]
    assert not manager.check_overlap(5, 10)
    assert manager.check_overlap(12, 18)
    existing_annotation = manager.app.annotations[0]
    assert not manager.check_overlap(12, 18, exclude_annotation=existing_annotation)

def test_get_current_annotation_index(manager):
    manager.app.annotations = [
        TimelineAnnotation(start_time=10, end_time=20),
        TimelineAnnotation(start_time=30, end_time=40)
    ]
    manager.app.media_player['_position'] = 15000
    assert manager.get_current_annotation_index() == 0
    manager.app.media_player['_position'] = 25000
    assert manager.get_current_annotation_index() == -1

@patch('src.annotation_manager.QMessageBox')
def test_toggle_annotation_start_and_finish(mock_qmessagebox, manager):
    manager.app.media_player['_position'] = 10000
    manager.toggleAnnotation()
    assert isinstance(manager.app.current_annotation, TimelineAnnotation)
    manager.app.media_player['_position'] = 25000
    manager.toggleAnnotation()
    assert manager.app.current_annotation is None
    assert len(manager.app.annotations) == 1
    assert manager.app.annotations[0].end_time == 25.0

@patch('src.annotation_manager.QMessageBox')
def test_toggle_annotation_finish_invalid_time(mock_qmessagebox, manager):
    manager.app.media_player['_position'] = 10000
    manager.toggleAnnotation()
    manager.app.media_player['_position'] = 5000
    manager.toggleAnnotation()
    assert manager.app.current_annotation is not None
    mock_qmessagebox.warning.assert_called_with(manager.app, "Invalid End Time", "End time must be after the start time.")

def test_cancel_annotation(manager):
    manager.app.media_player['_position'] = 10000
    manager.toggleAnnotation()
    manager.cancelAnnotation()
    assert manager.app.current_annotation is None

@patch('src.annotation_manager.QMessageBox')
def test_delete_current_label(mock_qmessagebox, manager):
    manager.app.annotations = [TimelineAnnotation(start_time=10, end_time=20)]
    manager.app.media_player['_position'] = 15000
    mock_qmessagebox.question.return_value = mock_qmessagebox.StandardButton.Yes
    manager.deleteCurrentLabel()
    assert len(manager.app.annotations) == 0

@patch('src.annotation_manager.QMessageBox')
def test_delete_current_label_no_selection(mock_qmessagebox, manager):
    manager.app.annotations = [TimelineAnnotation(start_time=10, end_time=20)]
    manager.app.media_player['_position'] = 25000
    manager.deleteCurrentLabel()
    assert len(manager.app.annotations) == 1
    mock_qmessagebox.information.assert_called_once()

@patch('src.annotation_manager.QMessageBox')
def test_split_current_label(mock_qmessagebox, manager):
    original_annotation = TimelineAnnotation(start_time=10, end_time=30)
    original_annotation.update_comment_body(posture="Sitting")
    manager.app.annotations = [original_annotation]
    manager.app.media_player['_position'] = 20000
    manager.splitCurrentLabel()
    assert len(manager.app.annotations) == 2
    part1, part2 = manager.app.annotations
    assert part1.start_time == 10 and part1.end_time == 20
    assert part2.start_time == 20 and part2.end_time == 30
    assert get_comment_value(part1.comments, "POSTURE") == "Sitting"
    assert get_comment_value(part2.comments, "POSTURE") == "Sitting"
    manager.app.updateAnnotationTimeline.assert_called_once()
    mock_qmessagebox.warning.assert_not_called()

@patch('src.annotation_manager.QMessageBox')
def test_merge_with_previous(mock_qmessagebox, manager):
    prev_ann = TimelineAnnotation(start_time=10, end_time=20)
    curr_ann = TimelineAnnotation(start_time=20, end_time=30)
    curr_ann.update_comment_body(posture="MergedPosture")
    manager.app.annotations = [prev_ann, curr_ann]
    manager.app.media_player['_position'] = 25000
    manager.mergeWithPrevious()
    assert len(manager.app.annotations) == 1
    merged = manager.app.annotations[0]
    assert merged.start_time == 10 and merged.end_time == 30
    assert get_comment_value(merged.comments, "POSTURE") == "MergedPosture"
    manager.app.updateAnnotationTimeline.assert_called_once()

@patch('src.annotation_manager.QMessageBox')
def test_merge_with_next(mock_qmessagebox, manager):
    curr_ann = TimelineAnnotation(start_time=10, end_time=20)
    curr_ann.update_comment_body(posture="MergedPosture")
    next_ann = TimelineAnnotation(start_time=20, end_time=30)
    manager.app.annotations = [curr_ann, next_ann]
    manager.app.media_player['_position'] = 15000
    manager.mergeWithNext()
    assert len(manager.app.annotations) == 1
    merged = manager.app.annotations[0]
    assert merged.start_time == 10 and merged.end_time == 30
    assert get_comment_value(merged.comments, "POSTURE") == "MergedPosture"
    manager.app.updateAnnotationTimeline.assert_called_once()

@patch('src.annotation_manager.QMessageBox')
def test_merge_fails_if_not_adjacent(mock_qmessagebox, manager):
    prev_ann = TimelineAnnotation(start_time=10, end_time=20)
    curr_ann = TimelineAnnotation(start_time=22, end_time=30)
    manager.app.annotations = [prev_ann, curr_ann]
    manager.app.media_player['_position'] = 25000
    manager.mergeWithPrevious()
    assert len(manager.app.annotations) == 2
    mock_qmessagebox.warning.assert_called_once()

def test_move_to_next_label(manager):
    manager.app.annotations = [
        TimelineAnnotation(start_time=10, end_time=20),
        TimelineAnnotation(start_time=30, end_time=40)
    ]
    manager.app.media_player['_position'] = 15000
    manager.moveToNextLabel()
    manager.app.setPosition.assert_called_with(20000)

def test_move_to_previous_label(manager):
    manager.app.annotations = [
        TimelineAnnotation(start_time=10, end_time=20),
        TimelineAnnotation(start_time=30, end_time=40)
    ]
    manager.app.media_player['_position'] = 35000
    manager.moveToPreviousLabel()
    manager.app.setPosition.assert_called_with(30000)