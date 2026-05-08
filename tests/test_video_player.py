import pytest
import json
from zipfile import ZipFile
from unittest.mock import MagicMock

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget
from src.video_player import VideoPlayerApp
from importlib.metadata import version
__version__ = version("paaws-annotation-software")

@pytest.fixture
def app(qtbot, monkeypatch):
    class MockQQuickWidget(QWidget):
        ResizeMode = MagicMock()
        Status = MagicMock()

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            self.mock_root_object = MagicMock()
            self.mock_root_object.setProperty = MagicMock(return_value=True)
            self.mock_root_object.seek = MagicMock()
            self.mock_root_object.play = MagicMock()
            self.mock_root_object.pause = MagicMock()
            
            self.rootObject = lambda: self.mock_root_object
            self.setResizeMode = MagicMock()
            self.setAttribute = MagicMock()
            self.palette = MagicMock()
            self.setPalette = MagicMock()
            self.setAutoFillBackground = MagicMock()
            self.setSource = MagicMock()
            self.statusChanged = MagicMock()
            self.status = MagicMock(return_value=self.Status.Ready)
            self.errors = MagicMock(return_value=[])

    monkeypatch.setattr("src.video_player.QQuickWidget", MockQQuickWidget)
  
    monkeypatch.setattr("src.video_player.ShortcutManager", MagicMock())
    monkeypatch.setattr("src.video_player.AnnotationManager", MagicMock())
    monkeypatch.setattr("src.video_player.AutosaveManager", MagicMock())

    monkeypatch.setattr("src.video_player.QFileDialog", MagicMock())
    video_app = VideoPlayerApp()
    qtbot.addWidget(video_app)

    video_app._qml_main_ready = True
    video_app._qml_preview_ready = True
    video_app.qml_root_main = video_app.quick_widget_main.rootObject()
    video_app.qml_root_preview = video_app.quick_widget_preview.rootObject()
    
    return video_app

def test_initialization(app):
    assert app is not None
    assert app.windowTitle() == f"PAAWS Annotation Software v{__version__}"
    assert app.autosave_manager is not None
    assert app.annotation_manager is not None
    assert app.shortcut_manager is not None

def test_open_file_sets_path_and_source(app, monkeypatch):
    mock_file_dialog = MagicMock()
    mock_file_dialog.getOpenFileName.return_value = ("/fake/path/video.mp4", "Video Files (*.mp4)")
    monkeypatch.setattr("src.video_player.QFileDialog", mock_file_dialog)
    
    app.autosave_manager.check_for_autosave.return_value = (None, False)
    
    app.openFile()
    
    assert app.current_video_path == "/fake/path/video.mp4"
    assert app.session_tracker.is_started is True
    expected_url = QUrl.fromLocalFile("/fake/path/video.mp4")
    app.qml_root_main.setProperty.assert_any_call('source', expected_url)

def test_export_stops_active_session(app, monkeypatch, tmp_path):
    export_path = tmp_path / "labels.zip"
    mock_file_dialog = MagicMock()
    mock_file_dialog.getSaveFileName.return_value = (str(export_path), "ZIP Files (*.zip)")
    monkeypatch.setattr("src.video_player.QFileDialog", mock_file_dialog)
    monkeypatch.setattr("src.video_player.QMessageBox", MagicMock())

    app.session_tracker.start()
    app.saveAnnotations()

    assert app.session_tracker.is_started is False
    with ZipFile(export_path) as zipf:
        labels = json.loads(zipf.read("labels.json"))
    assert "session" in labels
    assert labels["session"]["annotator_user_id"] == app.annotator_user_id

def test_toggle_play_pause(app):
    app.current_video_path = "/fake/video.mp4"
    
    app.media_player['_playback_state'] = 2  # Paused
    app.togglePlayPause()
    app.qml_root_main.play.assert_called_once()
    app.qml_root_preview.play.assert_called_once()
    app.qml_root_main.reset_mock()
    app.qml_root_preview.reset_mock()

    app.media_player['_playback_state'] = 1  # Playing
    app.togglePlayPause()
    app.qml_root_main.pause.assert_called_once()
    app.qml_root_preview.pause.assert_called_once()
    
def test_playback_rate_control(app):
    app.media_player['_playback_rate'] = 1.0
    
    app.changePlaybackRate(0.5)
    app.qml_root_main.setProperty.assert_any_call('playbackRate', 1.5)
    app.qml_root_preview.setProperty.assert_any_call('playbackRate', 1.5)
    assert "1.5x" in app.speed_label.text()

def test_position_control(app):
    app.current_video_path = "/fake/video.mp4"
    
    app.setPosition(15000, from_main=True)
    app.qml_root_main.seek.assert_called_with(15000)
    expected_preview_pos = 15000 + app.PREVIEW_OFFSET
    app.qml_root_preview.seek.assert_called_with(expected_preview_pos)

def test_video_rotation(app):
    app.rotateVideo()
    assert app.current_rotation == 90
    app.qml_root_main.setProperty.assert_any_call('orientation', 90)
    app.qml_root_preview.setProperty.assert_any_call('orientation', 90)
    
    app.rotateVideo()
    assert app.current_rotation == 180
    app.qml_root_main.setProperty.assert_any_call('orientation', 180)
    app.qml_root_preview.setProperty.assert_any_call('orientation', 180)

def test_delegation_to_annotation_manager(app):
    app.toggleAnnotation()
    app.annotation_manager.toggleAnnotation.assert_called_once()
    
    app.deleteCurrentLabel()
    app.annotation_manager.deleteCurrentLabel.assert_called_once()
    
    app.mergeWithNext()
    app.annotation_manager.mergeWithNext.assert_called_once()
