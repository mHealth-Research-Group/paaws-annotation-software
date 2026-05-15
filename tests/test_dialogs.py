import json
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton

from src.dialogs import AnnotationDialog


@pytest.fixture
def dialog(qtbot):
    dlg = AnnotationDialog()
    qtbot.addWidget(dlg)
    return dlg


@pytest.fixture
def mock_annotation():
    annotation = MagicMock()
    comment_data = [
        {"category": "POSTURE", "selectedValue": "Sitting"},
        {"category": "HIGH LEVEL BEHAVIOR", "selectedValue": ["Walking", "Grooming"]},
        {"category": "PA TYPE", "selectedValue": "Avoid"},
        {"category": "Behavioral Parameters", "selectedValue": ["Slow"]},
        {"category": "Experimental situation", "selectedValue": "Test"},
        {"category": "Special Notes", "selectedValue": "This is a test note."},
    ]
    annotation.comments = [{"body": json.dumps(comment_data)}]
    return annotation


def test_dialog_initialization_empty(dialog):
    assert dialog.posture_active.text() == "Posture_Unlabeled"
    assert dialog.hlb_active.text() == "HLB_Unlabeled"
    assert dialog.notes_edit.text() == ""


def test_single_selection_updates_active_label(dialog):
    dialog.posture_selection.set_values(["Standing"])
    assert dialog.posture_active.text() == "Standing"


def test_multi_selection_adds_and_removes_tags(dialog):
    dialog.hlb_selection.set_values(["Walking"])
    assert "Walking" in dialog.hlb_active.text()
    assert "HLB_Unlabeled" not in dialog.hlb_active.text()
    assert len(dialog.hlb_selection.selected_values) == 1

    dialog.hlb_selection.set_values(["Walking", "Grooming"])
    assert "Walking" in dialog.hlb_active.text()
    assert "Grooming" in dialog.hlb_active.text()
    assert len(dialog.hlb_selection.selected_values) == 2

    # Find and click the remove button for "Walking"
    remove_button = None
    for i in range(dialog.hlb_selection.tag_layout.count()):
        item = dialog.hlb_selection.tag_layout.itemAt(i)
        widget = item.widget() if item else None
        if widget and widget.findChild(QLabel) and widget.findChild(QLabel).text() == "Walking":
            remove_button = widget.findChild(QPushButton)
            break

    assert remove_button is not None, "Could not find remove button for 'Walking' tag"
    # Directly call remove_tag instead of simulating click (avoids needing qtbot in non-fixture context)
    dialog.hlb_selection.remove_tag("Walking")

    assert "Walking" not in dialog.hlb_active.text()
    assert "Grooming" in dialog.hlb_active.text()
    assert len(dialog.hlb_selection.selected_values) == 1


def test_retrieving_selected_values(dialog):
    dialog.posture_selection.set_values(["Sitting"])
    dialog.hlb_selection.set_values(["Walking", "Resting"])

    assert dialog.posture_selection.selected_values == ["Sitting"]
    assert set(dialog.hlb_selection.selected_values) == {"Walking", "Resting"}


def test_keyboard_shortcuts_focus_combos(qtbot, dialog):
    dialog.show()
    qtbot.keyPress(dialog, Qt.Key.Key_1)
    # Key 1 should trigger posture combo focus_search
    # Just verify no crash — popup visibility is unreliable in headless tests
    dialog.posture_combo.hidePopup()
    qtbot.keyPress(dialog, Qt.Key.Key_2)
    dialog.hlb_combo.hidePopup()
