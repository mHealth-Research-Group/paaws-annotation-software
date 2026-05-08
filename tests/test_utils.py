import os
import json
import pytest
from unittest.mock import MagicMock
from src.utils import AutosaveManager, SessionTracker, autosave

class MockAnnotation:
    def __init__(self, start, end, comments=None, id="mock_id"):
        self.start_time = start
        self.end_time = end
        self.id = id
        self.shape = {}
        self.comments = comments if comments is not None else []

@pytest.fixture
def manager(tmp_path, monkeypatch):
    instance = AutosaveManager()
    monkeypatch.setattr(instance, 'autosave_dir', str(tmp_path))
    return instance

@pytest.fixture
def video_file(tmp_path):
    """Creates a temporary dummy video file and returns its path."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_bytes(b"dummy video content for testing file size")
    return str(video_path)

def test_autosave_manager_initialization(manager, tmp_path):
    """Test that the manager is created and its directory is redirected."""
    assert isinstance(manager, AutosaveManager)
    assert manager.autosave_dir == str(tmp_path)

def test_calculate_video_hash(manager, video_file):
    """Test that a hash is correctly calculated based on file size."""
    video_hash = manager.calculate_video_hash(video_file)
    assert isinstance(video_hash, int)
    assert video_hash != 0

def test_save_and_check_annotations(manager, video_file):
    mock_annotations = [
        MockAnnotation(start=0, end=10, comments=[{"body": "comment 1"}]),
        MockAnnotation(start=10, end=20, comments=[{"body": "comment 2"}])
    ]
    video_hash = manager.calculate_video_hash(video_file)

    manager.save_annotations(video_file, mock_annotations, video_hash=video_hash)
    expected_path = os.path.join(manager.autosave_dir, "test_video_autosave.json")
    assert os.path.exists(expected_path)
    with open(expected_path, 'r') as f:
        saved_data = json.load(f)
        assert saved_data['video_path'] == video_file
        assert saved_data['videoHash'] == video_hash
        assert len(saved_data['annotations']) == 2
        # Check structure of the first saved annotation
        first_saved_ann = saved_data['annotations'][0]
        assert first_saved_ann['range']['start'] == 0
        assert first_saved_ann['range']['end'] == 10
        assert first_saved_ann['comments'][0]['body'] == "comment 1"

def test_delete_autosave(manager, video_file):
    manager.save_annotations(video_file, [])
    expected_path = os.path.join(manager.autosave_dir, "test_video_autosave.json")
    assert os.path.exists(expected_path)
    manager.delete_autosave(video_file)
    assert not os.path.exists(expected_path)

def test_check_for_autosave_positive_match(manager, video_file):
    video_hash = manager.calculate_video_hash(video_file)
    manager.save_annotations(video_file, [], video_hash=video_hash)

    data, hash_matches = manager.check_for_autosave(video_file, video_hash)
    assert data is not None
    assert hash_matches is True
    assert data['video_path'] == video_file

def test_check_for_autosave_hash_mismatch(manager, video_file):
    video_hash = manager.calculate_video_hash(video_file)
    manager.save_annotations(video_file, [], video_hash=video_hash)
    data, hash_matches = manager.check_for_autosave(video_file, 12345)
    assert data is not None
    assert hash_matches is False

def test_check_for_corrupted_autosave(manager, video_file):
    autosave_path = os.path.join(manager.autosave_dir, "test_video_autosave.json")
    with open(autosave_path, 'w') as f:
        f.write("this is not valid json")
    
    data, hash_matches = manager.check_for_autosave(video_file, 123)
    assert data is None
    assert hash_matches is False

def test_autosave_decorator():
    mock_app = MagicMock()
    mock_app.autosave = MagicMock()
    class DummyClass:
        def __init__(self, app):
            self.app = app
        
        @autosave
        def mock_method(self):
            pass
            
    instance = DummyClass(mock_app)
    
    instance.mock_method()
    mock_app.autosave.assert_called_once()


class TestSessionTracker:
    def test_initial_state(self):
        tracker = SessionTracker()
        assert tracker.is_started is False
        assert tracker.build_session_data([], "uid", "name") is None

    def test_start_records_time_and_is_idempotent(self):
        tracker = SessionTracker()
        tracker.start()
        assert tracker.is_started is True
        first_start = tracker._session_start
        tracker.start()
        assert tracker._session_start is first_start

    def test_reset_clears_state(self):
        tracker = SessionTracker()
        tracker.start()
        tracker.build_session_data([], "uid", "name")
        tracker.reset()
        assert tracker.is_started is False
        assert tracker._export_count == 0

    def test_stop_clears_active_session_without_resetting_export_count(self):
        tracker = SessionTracker()
        tracker.start()
        tracker.build_session_data([], "uid", "name")
        tracker.stop()
        assert tracker.is_started is False
        assert tracker._export_count == 1

    def test_build_session_data_no_annotations(self):
        tracker = SessionTracker()
        tracker.start()
        data = tracker.build_session_data([], "uid", "Jane")
        assert data is not None
        assert data["annotator_user_id"] == "uid"
        assert data["annotator_user_name"] == "Jane"
        assert data["total_annotations"] == 0
        assert data["footage_covered_seconds"] == 0.0
        assert data["first_annotation"]["wall_clock"] is None
        assert data["last_annotation"]["wall_clock"] is None
        assert data["export_count"] == 1

    def test_build_session_data_with_annotations(self):
        tracker = SessionTracker()
        tracker.start()
        annotations = [
            MockAnnotation(
                start=10.0, end=50.0,
                comments=[{"meta": {"datetime": "2026-03-17T10:08:12"}, "body": "[]"}],
            ),
            MockAnnotation(
                start=60.0, end=120.0,
                comments=[{"meta": {"datetime": "2026-03-17T11:40:03"}, "body": "[]"}],
            ),
        ]
        data = tracker.build_session_data(annotations, "abc", "Bob")
        assert data["total_annotations"] == 2
        assert data["footage_covered_seconds"] == 110.0  # 120 - 10
        assert data["first_annotation"]["wall_clock"] == "2026-03-17T10:08:12"
        assert data["first_annotation"]["video_position_seconds"] == 10.0
        assert data["last_annotation"]["wall_clock"] == "2026-03-17T11:40:03"
        assert data["last_annotation"]["video_position_seconds"] == 60.0
        assert data["session_duration_seconds"] >= 0

    def test_export_count_increments(self):
        tracker = SessionTracker()
        tracker.start()
        data1 = tracker.build_session_data([], "uid", "name")
        assert data1["export_count"] == 1
        data2 = tracker.build_session_data([], "uid", "name")
        assert data2["export_count"] == 2
        data3 = tracker.build_session_data([], "uid", "name")
        assert data3["export_count"] == 3
