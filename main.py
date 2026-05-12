# main.py

import sys
import os
from PyQt6.QtWidgets import QApplication

# Ensure the 'src' directory is in the Python path
# This allows importing modules from src like 'from src.video_player import VideoPlayerApp'
script_dir = os.path.dirname(__file__)
src_dir = os.path.join(script_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    # Import the main application class from the src directory
    from src.video_player import VideoPlayerApp
except ImportError as e:
    print(f"Error importing VideoPlayerApp: {e}", file=sys.stderr)
    print("Please ensure 'src' directory exists and contains 'video_player.py'", file=sys.stderr)
    print("Also check dependencies like PyQt6.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    # Check for the essential QML file
    qml_file = "VideoPlayer.qml"
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = script_dir

    qml_file_path = os.path.join(base_path, "src", qml_file)

    if not os.path.exists(qml_file_path):
        print(f"ERROR: {qml_file} not found at: {qml_file_path}", file=sys.stderr)
        print("Video playback requires this QML file.", file=sys.stderr)

    app = QApplication(sys.argv)
    player = VideoPlayerApp()
    player.show()
    print("--- Application Started ---")
    sys.exit(app.exec())
