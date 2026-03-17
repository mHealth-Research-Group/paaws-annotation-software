from dataclasses import dataclass
import json
import uuid
from datetime import datetime

@dataclass
class TimelineAnnotation:
    def __init__(self, start_time=0, end_time=0, user_id="NA", user_name="NA"):
        self.id = str(uuid.uuid4())
        self.start_time = start_time
        self.end_time = end_time
        self.user_id = user_id
        self.user_name = user_name
        self.shape = {
            "x1": None,
            "x2": None,
            "y1": None,
            "y2": None
        }
        self.comments = []
        self._add_initial_comment()
        
    def _add_initial_comment(self):
        comment = {
            "id": str(uuid.uuid4()),
            "meta": {
                "datetime": datetime.now().isoformat(),
                "user_id": self.user_id,
                "user_name": self.user_name
            },
            "body": "[]"
        }
        self.comments.append(comment)
        
    def copy_comments_from(self, source_annotation):
        """Deep copy comments from another annotation with new UUIDs"""
        self.comments = []
        for comment in source_annotation.comments:
            new_comment = {
                "id": str(uuid.uuid4()),
                "meta": comment["meta"].copy(),
                "body": comment["body"]
            }
            self.comments.append(new_comment)
            
    def update_comment_body(self, posture="", hlb=None, pa_type="", behavioral_params=None, exp_situation="", special_notes=""):
        if hlb is None:
            hlb = []
        if behavioral_params is None:
            behavioral_params = []
            
        comment_data = [
            {"category": "POSTURE", "selectedValue": posture},
            {"category": "HIGH LEVEL BEHAVIOR", "selectedValue": hlb},
            {"category": "PA TYPE", "selectedValue": pa_type},
            {"category": "Behavioral Parameters", "selectedValue": behavioral_params},
            {"category": "Experimental situation", "selectedValue": exp_situation},
            {"category": "Special Notes", "selectedValue": special_notes}
        ]
        self.comments[0]["body"] = json.dumps(comment_data)

    def __str__(self):
        return f"Annotation {self.id}: {self.start_time} - {self.end_time}"
