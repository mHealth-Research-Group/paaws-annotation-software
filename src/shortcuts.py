from PyQt6.QtGui import QAction


class ShortcutManager:
    def __init__(self, app):
        self.app = app
        self.setupShortcuts()

    def setupShortcuts(self):
        # Video control shortcuts
        self.spacebar_shortcut = QAction("Play/Pause", self.app)
        self.spacebar_shortcut.setShortcut("Space")
        self.spacebar_shortcut.triggered.connect(self.app.togglePlayPause)
        self.app.addAction(self.spacebar_shortcut)

        # Frame rate controls
        self.reset_rate = QAction("Reset Frame Rate", self.app)
        self.reset_rate.setShortcut("r")
        self.reset_rate.triggered.connect(lambda: self.setPlaybackRate(1.0))
        self.app.addAction(self.reset_rate)

        self.increase_rate = QAction("Increase Frame Rate", self.app)
        self.increase_rate.setShortcut("Up")
        self.increase_rate.triggered.connect(lambda: self.adjustPlaybackRate(0.25))
        self.app.addAction(self.increase_rate)

        self.decrease_rate = QAction("Decrease Frame Rate", self.app)
        self.decrease_rate.setShortcut("Down")
        self.decrease_rate.triggered.connect(lambda: self.adjustPlaybackRate(-0.25))
        self.app.addAction(self.decrease_rate)

        # Time skip controls
        self.skip_forward = QAction("Skip Forward", self.app)
        self.skip_forward.setShortcut("Right")
        self.skip_forward.triggered.connect(lambda: self.skipTime(10000))
        self.app.addAction(self.skip_forward)

        self.skip_backward = QAction("Skip Backward", self.app)
        self.skip_backward.setShortcut("Left")
        self.skip_backward.triggered.connect(lambda: self.skipTime(-10000))
        self.app.addAction(self.skip_backward)

        # Labelling shortcuts
        self.start_label = QAction("Start/Stop Labelling", self.app)
        self.start_label.setShortcut("a")
        self.start_label.triggered.connect(self.app.toggleAnnotation)
        self.app.addAction(self.start_label)

        self.cancel_label = QAction("Cancel Labelling", self.app)
        self.cancel_label.setShortcut("z")
        self.cancel_label.triggered.connect(self.app.cancelAnnotation)
        self.app.addAction(self.cancel_label)

        self.delete_label = QAction("Delete Label", self.app)
        self.delete_label.setShortcut("s")
        self.delete_label.triggered.connect(self.app.deleteCurrentLabel)
        self.app.addAction(self.delete_label)

        # Label navigation
        self.prev_label_start = QAction("Previous Label Start", self.app)
        self.prev_label_start.setShortcut("Shift+Left")
        self.prev_label_start.triggered.connect(self.app.moveToPreviousLabel)
        self.app.addAction(self.prev_label_start)

        self.next_label_start = QAction("Next Label Start", self.app)
        self.next_label_start.setShortcut("Shift+Right")
        self.next_label_start.triggered.connect(self.app.moveToNextLabel)
        self.app.addAction(self.next_label_start)

        # Label merging
        self.merge_prev = QAction("Merge with Previous", self.app)
        self.merge_prev.setShortcut("n")
        self.merge_prev.triggered.connect(self.app.mergeWithPrevious)
        self.app.addAction(self.merge_prev)

        self.merge_next = QAction("Merge with Next", self.app)
        self.merge_next.setShortcut("m")
        self.merge_next.triggered.connect(self.app.mergeWithNext)
        self.app.addAction(self.merge_next)

        # Advanced preview controls
        self.increase_preview = QAction("Increase Preview Skip", self.app)
        self.increase_preview.setShortcut("Shift+Up")
        self.increase_preview.triggered.connect(lambda: self.adjustPreviewSkip(2))
        self.app.addAction(self.increase_preview)

        self.decrease_preview = QAction("Decrease Preview Skip", self.app)
        self.decrease_preview.setShortcut("Shift+Down")
        self.decrease_preview.triggered.connect(lambda: self.adjustPreviewSkip(-2))
        self.app.addAction(self.decrease_preview)

        # Split label
        self.split_label = QAction("Split Label", self.app)
        self.split_label.setShortcut("p")
        self.split_label.triggered.connect(self.app.splitCurrentLabel)
        self.app.addAction(self.split_label)

        # Dialog control
        self.toggle_dialog = QAction("Toggle Dialog", self.app)
        self.toggle_dialog.setShortcut("g")
        self.toggle_dialog.triggered.connect(self.app.editAnnotation)
        self.app.addAction(self.toggle_dialog)

    def setPlaybackRate(self, rate):
        """Tell the main app to set the playback rate."""
        if hasattr(self.app, "setPlaybackRate"):  # Check if method exists on app
            self.app.setPlaybackRate(rate)  # Call the app's method
        else:
            print("ShortcutManager: Error - self.app has no setPlaybackRate method.")

    def adjustPlaybackRate(self, delta):
        """Tell the main app to adjust the playback rate."""
        if hasattr(self.app, "changePlaybackRate"):  # Check if method exists on app
            # Note: We call changePlaybackRate which handles getting current rate
            self.app.changePlaybackRate(delta)
        else:
            print("ShortcutManager: Error - self.app has no changePlaybackRate method.")

    # Keep skipTime method, but make it call app's seek method
    def skipTime(self, ms):
        """Tell the main app to skip time."""
        if hasattr(self.app, "qml_root_main") and self.app.qml_root_main:
            current = self.app.media_player["_position"]  # Use tracked position
            duration = self.app.media_player["_duration"]  # Use tracked duration
            target_pos = max(0, min(current + ms, duration if duration > 0 else current + ms))  # Basic clamping
            print(f"ShortcutManager: Seeking main player to {target_pos}")
            self.app.qml_root_main.seek(target_pos)
            # Also sync preview immediately after shortcut seek
            self.app._sync_preview_qml_position(target_pos)
        else:
            print("ShortcutManager: Cannot skip time, QML player not ready.")

    # adjustPreviewSkip might need similar adaptation if PREVIEW_OFFSET is dynamic
    def adjustPreviewSkip(self, seconds_delta):
        # This requires PREVIEW_OFFSET to be adjustable in VideoPlayerApp
        if hasattr(self.app, "adjustPreviewOffset"):
            self.app.adjustPreviewOffset(seconds_delta * 1000)  # Convert s to ms
        else:
            print("ShortcutManager: self.app has no adjustPreviewOffset method.")
