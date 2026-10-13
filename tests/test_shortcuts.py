from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow

from src.shortcuts import ShortcutManager


class MockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mock App")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(200, 100)
        self.togglePlayPause = MagicMock()
        self.toggleAnnotation = MagicMock()
        self.cancelAnnotation = MagicMock()
        self.deleteCurrentLabel = MagicMock()
        self.moveToPreviousLabel = MagicMock()
        self.moveToNextLabel = MagicMock()
        self.mergeWithPrevious = MagicMock()
        self.mergeWithNext = MagicMock()
        self.splitCurrentLabel = MagicMock()
        self.editAnnotation = MagicMock()
        self.toggleShortcutsWidget = MagicMock()
        self.setPlaybackRate = MagicMock()
        self.changePlaybackRate = MagicMock()
        self.adjustPreviewOffset = MagicMock()
        self._sync_preview_qml_position = MagicMock()
        self.qml_root_main = MagicMock()
        self.qml_root_main.seek = MagicMock()
        self.media_player = {"_position": 10000, "_duration": 60000}


@pytest.fixture
def mock_app(qtbot):
    app = MockApp()
    app.show()
    qtbot.addWidget(app)
    return app


@pytest.fixture
def manager(mock_app):
    return ShortcutManager(mock_app)


def test_initialization(manager, mock_app):
    assert manager.app == mock_app
    assert manager.spacebar_shortcut is not None
    assert manager.start_label is not None
    assert manager.skip_forward is not None


def test_play_pause_shortcut(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, Qt.Key.Key_Space)
    mock_app.togglePlayPause.assert_called_once()


def test_playback_rate_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, Qt.Key.Key_Up)
    mock_app.changePlaybackRate.assert_called_once_with(0.25)
    mock_app.changePlaybackRate.reset_mock()

    qtbot.keyClick(mock_app, Qt.Key.Key_Down)
    mock_app.changePlaybackRate.assert_called_once_with(-0.25)
    mock_app.changePlaybackRate.reset_mock()

    qtbot.keyClick(mock_app, "r")
    mock_app.setPlaybackRate.assert_called_once_with(1.0)


def test_time_skip_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, Qt.Key.Key_Right)
    mock_app.qml_root_main.seek.assert_called_once_with(20000)
    mock_app.qml_root_main.seek.reset_mock()

    qtbot.keyClick(mock_app, Qt.Key.Key_Left)
    mock_app.qml_root_main.seek.assert_called_once_with(0)


def test_annotation_action_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, "a")
    mock_app.toggleAnnotation.assert_called_once()

    qtbot.keyClick(mock_app, "z")
    mock_app.cancelAnnotation.assert_called_once()

    qtbot.keyClick(mock_app, "s")
    mock_app.deleteCurrentLabel.assert_called_once()


def test_annotation_navigation_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
    mock_app.moveToPreviousLabel.assert_called_once()

    qtbot.keyClick(mock_app, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    mock_app.moveToNextLabel.assert_called_once()


def test_annotation_merge_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, "m")
    mock_app.mergeWithNext.assert_called_once()

    qtbot.keyClick(mock_app, "n")
    mock_app.mergeWithPrevious.assert_called_once()


def test_split_and_edit_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, "p")
    mock_app.splitCurrentLabel.assert_called_once()

    qtbot.keyClick(mock_app, "g")
    mock_app.editAnnotation.assert_called_once()


def test_toggle_shortcuts_panel_shortcut(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, "h")
    mock_app.toggleShortcutsWidget.assert_called_once()


def test_preview_offset_shortcuts(manager, mock_app, qtbot):
    qtbot.keyClick(mock_app, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier)
    mock_app.adjustPreviewOffset.assert_called_once_with(2000)
    mock_app.adjustPreviewOffset.reset_mock()

    qtbot.keyClick(mock_app, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    mock_app.adjustPreviewOffset.assert_called_once_with(-2000)
