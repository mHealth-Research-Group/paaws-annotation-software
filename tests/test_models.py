"""Tests for models module."""

import json

from src.models import TimelineAnnotation


def test_timeline_annotation_initialization():
    annotation = TimelineAnnotation()

    assert annotation.start_time == 0
    assert annotation.end_time == 0
    assert annotation.id is not None
    assert len(annotation.id) > 0
    assert annotation.shape == {"x1": None, "x2": None, "y1": None, "y2": None}
    assert len(annotation.comments) == 1

    comment = annotation.comments[0]
    assert "id" in comment
    assert "meta" in comment
    assert "body" in comment
    assert comment["body"] == "[]"


def test_timeline_annotation_with_times():
    start = 10.5
    end = 20.5
    annotation = TimelineAnnotation(start_time=start, end_time=end)

    assert annotation.start_time == start
    assert annotation.end_time == end


def test_copy_comments():
    source = TimelineAnnotation()
    target = TimelineAnnotation()

    source.update_comment_body(
        posture="Standing",
        hlb=["Walking"],
        pa_type="Moderate",
        behavioral_params=["Normal pace"],
        exp_situation="Indoor",
        special_notes="Test note",
    )

    target.copy_comments_from(source)

    assert len(target.comments) == len(source.comments)
    assert target.comments[0]["body"] == source.comments[0]["body"]
    assert target.comments[0]["id"] != source.comments[0]["id"]


def test_update_comment_body():
    """Test updating comment body with new values."""
    annotation = TimelineAnnotation()

    test_data = {
        "posture": "Standing",
        "hlb": ["Walking", "Talking"],
        "pa_type": "Moderate",
        "behavioral_params": ["Normal pace"],
        "exp_situation": "Indoor",
        "special_notes": "Test note",
    }

    annotation.update_comment_body(**test_data)

    comment_data = json.loads(annotation.comments[0]["body"])

    assert len(comment_data) == 6
    assert any(item["category"] == "POSTURE" and item["selectedValue"] == "Standing" for item in comment_data)
    assert any(
        item["category"] == "HIGH LEVEL BEHAVIOR" and item["selectedValue"] == ["Walking", "Talking"]
        for item in comment_data
    )
    assert any(item["category"] == "PA TYPE" and item["selectedValue"] == "Moderate" for item in comment_data)
    assert any(
        item["category"] == "Behavioral Parameters" and item["selectedValue"] == ["Normal pace"]
        for item in comment_data
    )
    assert any(
        item["category"] == "Experimental situation" and item["selectedValue"] == "Indoor" for item in comment_data
    )
    assert any(item["category"] == "Special Notes" and item["selectedValue"] == "Test note" for item in comment_data)


def test_string_representation():
    annotation = TimelineAnnotation(start_time=10.5, end_time=20.5)
    expected = f"Annotation {annotation.id}: 10.5 - 20.5"
    assert str(annotation) == expected


def test_timeline_annotation_with_user_info():
    annotation = TimelineAnnotation(start_time=5, end_time=15, user_id="abc-123", user_name="Jane Doe")
    assert annotation.user_id == "abc-123"
    assert annotation.user_name == "Jane Doe"
    meta = annotation.comments[0]["meta"]
    assert meta["user_id"] == "abc-123"
    assert meta["user_name"] == "Jane Doe"


def test_timeline_annotation_default_user_info():
    annotation = TimelineAnnotation()
    assert annotation.user_id == "NA"
    assert annotation.user_name == "NA"
    meta = annotation.comments[0]["meta"]
    assert meta["user_id"] == "NA"
    assert meta["user_name"] == "NA"


def test_update_comment_body_with_defaults():
    annotation = TimelineAnnotation()
    annotation.update_comment_body()

    comment_data = json.loads(annotation.comments[0]["body"])
    assert any(item["category"] == "POSTURE" and item["selectedValue"] == "" for item in comment_data)
    assert any(item["category"] == "HIGH LEVEL BEHAVIOR" and item["selectedValue"] == [] for item in comment_data)
    assert any(item["category"] == "PA TYPE" and item["selectedValue"] == "" for item in comment_data)
    assert any(item["category"] == "Behavioral Parameters" and item["selectedValue"] == [] for item in comment_data)
    assert any(item["category"] == "Experimental situation" and item["selectedValue"] == "" for item in comment_data)
    assert any(item["category"] == "Special Notes" and item["selectedValue"] == "" for item in comment_data)
