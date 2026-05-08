import json
import os
from pathlib import Path
import tempfile
from datetime import datetime
from typing import List, Optional, Tuple
from src.models import TimelineAnnotation
import sys
from pathlib import Path

class SessionTracker:
    def __init__(self):
        self._session_start = None
        self._export_count = 0

    def reset(self):
        self._session_start = None
        self._export_count = 0

    def start(self):
        if self._session_start is None:
            self._session_start = datetime.now()

    def stop(self):
        self._session_start = None

    @property
    def is_started(self):
        return self._session_start is not None

    def build_session_data(self, annotations, user_id, user_name):
        if not self.is_started:
            return None

        now = datetime.now()
        duration = (now - self._session_start).total_seconds()
        self._export_count += 1

        first_wall_clock = None
        first_video_pos = None
        last_wall_clock = None
        last_video_pos = None
        total_annotations = len(annotations)

        # Derive first/last annotation by creation datetime from comments meta
        dated_annotations = []
        for ann in annotations:
            if ann.comments:
                meta = ann.comments[0].get("meta", {})
                dt_str = meta.get("datetime")
                if dt_str:
                    try:
                        dt = datetime.fromisoformat(dt_str)
                        dated_annotations.append((dt, ann))
                    except (ValueError, TypeError):
                        pass

        if dated_annotations:
            dated_annotations.sort(key=lambda x: x[0])
            first_dt, first_ann = dated_annotations[0]
            last_dt, last_ann = dated_annotations[-1]
            first_wall_clock = first_dt.isoformat()
            first_video_pos = first_ann.start_time
            last_wall_clock = last_dt.isoformat()
            last_video_pos = last_ann.start_time

        # Footage covered: span from earliest start_time to latest end_time
        footage_covered = 0.0
        if annotations:
            earliest_start = min(a.start_time for a in annotations)
            latest_end = max(a.end_time for a in annotations)
            footage_covered = latest_end - earliest_start

        data = {
            "session_start": self._session_start.isoformat(),
            "session_end": now.isoformat(),
            "session_duration_seconds": round(duration, 2),
            "annotator_user_id": user_id,
            "annotator_user_name": user_name,
            "first_annotation": {
                "wall_clock": first_wall_clock,
                "video_position_seconds": first_video_pos,
            },
            "last_annotation": {
                "wall_clock": last_wall_clock,
                "video_position_seconds": last_video_pos,
            },
            "total_annotations": total_annotations,
            "footage_covered_seconds": footage_covered,
            "export_count": self._export_count,
        }
        return data


class AutosaveManager:
    def __init__(self, interval: int = 300000) -> None:
        """Initialize autosave manager"""
        self.interval = interval
        self.autosave_dir = os.path.join(tempfile.gettempdir(), 'paaws_annotation_software_autosave')
        os.makedirs(self.autosave_dir, exist_ok=True)

    def calculate_video_hash(self, file_path: str) -> int:
        """Calculate hash from video file size"""
        try:
            file_size = os.path.getsize(file_path)
            size_str = str(file_size)
            video_hash = 0
            for char in size_str:
                video_hash = ((video_hash << 5) - video_hash + ord(char)) & 0xFFFFFFFF  # force 32-bit
            if video_hash & 0x80000000:
                video_hash = -((~video_hash & 0xFFFFFFFF) + 1)
            
            return video_hash
        except Exception as e:
            print(f"Error calculating video hash: {str(e)}")
            return 0

    def delete_autosave(self, video_path: str) -> None:
        """Delete autosave file for the given video"""
        if not video_path:
            return
            
        try:
            video_name = Path(video_path).stem
            autosave_path = os.path.join(self.autosave_dir, f"{video_name}_autosave.json")
            if os.path.exists(autosave_path):
                os.remove(autosave_path)
        except Exception as e:
            print(f"Error deleting autosave: {str(e)}")

    def save_annotations(self, video_path: str, annotations: List[TimelineAnnotation], *, video_hash: int = 0) -> None:
        """Save annotations to autosave file"""
        print(f"Autosaving annotations for {video_path}...")
        if not video_path:
            return
            
        try:
            video_name = Path(video_path).stem
            autosave_path = os.path.join(self.autosave_dir, f"{video_name}_autosave.json")
            
            annotations_data = {
                "annotations": [],
                "videoHash": video_hash,
                "video_path": video_path
            }
            
            for annotation in annotations:
                annotations_data["annotations"].append({
                    "id": annotation.id,
                    "range": {
                        "start": annotation.start_time,
                        "end": annotation.end_time
                    },
                    "shape": annotation.shape,
                    "comments": annotation.comments
                })
                
            with open(autosave_path, 'w') as f:
                json.dump(annotations_data, f, indent=4)
        except Exception as e:
            print(f"Autosave failed: {str(e)}")
            
    def check_for_autosave(self, video_path: str, current_hash: int) -> Tuple[Optional[dict], bool]:
        """
        Check for and load autosave file
        Returns: Tuple of (data dict, hash_matches)
                data dict is None if no autosave found
                hash_matches is True if video hash matches autosave
        """
        if not video_path:
            return None, False
            
        video_name = Path(video_path).stem
        autosave_path = os.path.join(self.autosave_dir, f"{video_name}_autosave.json")
        
        if os.path.exists(autosave_path):
            try:
                with open(autosave_path, 'r') as f:
                    data = json.load(f)
                if data.get("video_path") == video_path:
                    saved_hash = data.get("videoHash", data.get("videohash", 0))
                    return data, saved_hash == current_hash
            except Exception as e:
                print(f"Failed to load autosave: {str(e)}")
        
        return None, False
    
def autosave(func):
    """
    Decorator to handle autosaving
    """
    def wrapper(self, *args, **kwargs):
        # Call the original function
        func(self, *args, **kwargs)
        
        # Save annotations after the function call
        if hasattr(self, 'app') and hasattr(self.app, 'autosave_manager'):
            # Call the autosave method in the app
            self.app.autosave()

    return wrapper


def resource_path(relative_path: str) -> str:
    try:
        base_path = getattr(sys, '_MEIPASS', None)
    except Exception:
        base_path = None

    if base_path:
        return str(Path(base_path) / relative_path)
    here = Path(__file__).resolve().parent
    repo_root = here.parent
    candidate = repo_root / relative_path
    return str(candidate)
