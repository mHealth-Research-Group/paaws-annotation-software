# --- Imports ---
import json
import io
import csv
from zipfile import ZipFile
import os
import sys

# PyQt6 imports
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QLabel, QMessageBox,
                             QMenu)
from PyQt6.QtCore import Qt, QUrl, QTime, QTimer
from PyQt6.QtGui import QAction, QPalette, QGuiApplication
from PyQt6.QtQuickWidgets import QQuickWidget
from src.slider import CustomSlider
from src.models import TimelineAnnotation
from src.widgets import TimelineWidget
from src.dialogs import AnnotationDialog
from src.shortcuts import ShortcutManager
from src.annotation_manager import AnnotationManager
from src.utils import AutosaveManager
class VideoPlayerApp(QMainWindow):
    SYNC_THRESHOLD = 150
    MIN_ZOOM_DURATION = 600000 # 10 minutes in ms
    BASE_PREVIEW_OFFSET = 2000  # 2 seconds in ms

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PAAWS Annotation Software")
        screen = QGuiApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            self.resize(int(available_geometry.width() * 0.85), int(available_geometry.height() * 0.9))
            self.move(available_geometry.center() - self.rect().center())
        else:
            self.setGeometry(100, 100, 1280, 1000)

        
        self.autosave_manager = AutosaveManager(60000) 
        self.current_video_path = None
        self.video_hash = 0
        self.current_rotation = 0
        self.annotations = []
        self.current_annotation = None 
        self.zoom_start = 0.0 
        self.zoom_end = 1.0 
        self._is_navigating = False
        self.PREVIEW_OFFSET = self.BASE_PREVIEW_OFFSET

        
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(self.autosave_manager.interval)
        self.autosave_timer.timeout.connect(self.autosave)

        
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QLabel { color: #ffffff; font-size: 12px; }
        """)

        
        self.qml_root_main = None
        self.qml_root_preview = None
        self._qml_main_ready = False
        self._qml_preview_ready = False
        self._pending_source_url = None

        self.media_player = {
            '_playback_state': 0, 
            '_duration': 0,       
            '_position': 0,       
            '_playback_rate': 1.0,
        }

        
        self.setupUI()

        
        if hasattr(self, 'quick_widget_main'):
            print("--- Connecting main statusChanged signal...")
            self.quick_widget_main.statusChanged.connect(self.onQmlMainStatusChanged)
            print(f"--- Initial main status check: {self.quick_widget_main.status()}")
            self.onQmlMainStatusChanged(self.quick_widget_main.status())
        else:
             print("--- ERROR: quick_widget_main not found after setupUI!")

        if hasattr(self, 'quick_widget_preview'):
            print("--- Connecting preview statusChanged signal...")
            self.quick_widget_preview.statusChanged.connect(self.onQmlPreviewStatusChanged)
            print(f"--- Initial preview status check: {self.quick_widget_preview.status()}")
            self.onQmlPreviewStatusChanged(self.quick_widget_preview.status())
        else:
             print("--- ERROR: quick_widget_preview not found after setupUI!")

        
        self.loadQmlSources()

        
        
        self.annotation_manager = AnnotationManager(self)
        self.shortcut_manager = ShortcutManager(self) 

        
        self.checkQmlReadyAndLoadPending() 
        


    def setupUI(self):
        print("--- setupUI: Starting UI creation...")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        
        video_container = QWidget()
        video_container.setStyleSheet("QWidget { background-color: #1a1a1a; border: 2px solid #3a3a3a; border-radius: 8px; margin: 10px; }")
        video_container.setMinimumHeight(400)
        video_container_layout = QHBoxLayout(video_container)
        video_container_layout.setContentsMargins(10, 10, 10, 10); video_container_layout.setSpacing(10)

        
        print("--- setupUI: Creating QQuickWidgets...")
        left_video_container = QWidget(); left_video_layout = QVBoxLayout(left_video_container); left_video_layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget_main = QQuickWidget(self)
        self.quick_widget_main.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        
        self.quick_widget_main.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, False)
        self.quick_widget_main.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        palette_main = self.quick_widget_main.palette()
        palette_main.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black) 
        self.quick_widget_main.setPalette(palette_main)
        self.quick_widget_main.setAutoFillBackground(True)
        
        left_video_layout.addWidget(self.quick_widget_main)

        right_video_container = QWidget(); 
        right_video_layout = QVBoxLayout(right_video_container); 
        right_video_layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget_preview = QQuickWidget(self)
        self.quick_widget_preview.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        
        self.quick_widget_preview.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, False)
        self.quick_widget_preview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        palette_preview = self.quick_widget_preview.palette()
        palette_preview.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black) 
        self.quick_widget_preview.setPalette(palette_preview)
        self.quick_widget_preview.setAutoFillBackground(True)
        
        right_video_layout.addWidget(self.quick_widget_preview)

        video_container_layout.addWidget(left_video_container)
        video_container_layout.addWidget(right_video_container)
        layout.addWidget(video_container, stretch=2)
        print("--- setupUI: QQuickWidgets added to layout.")

        
        print("--- setupUI: Setting up timelines...")
        timelines_container = QWidget()
        timelines_container.setMinimumHeight(100)
        timelines_container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
        """)
        timelines_layout = QVBoxLayout(timelines_container)
        timelines_layout.setSpacing(8); 
        timelines_layout.setContentsMargins(12, 12, 12, 12)
        
        main_timeline_container = QWidget(); 
        main_timeline_container.setMinimumHeight(50)

        self.timeline = CustomSlider(Qt.Orientation.Horizontal, show_handle=True)
        self.timeline.sliderMoved.connect(lambda pos: self.setPosition(pos, from_main=True))
        self.timeline.sliderPressed.connect(self.sliderPressed)
        self.timeline.sliderReleased.connect(self.sliderReleased)
        self.timeline.setEnabled(False) 
        self.timeline_widget = TimelineWidget(self, show_position=False, is_main_timeline=True)
        main_timeline_layout = QVBoxLayout(main_timeline_container); 
        main_timeline_layout.setSpacing(20); 
        main_timeline_layout.setContentsMargins(0, 0, 0, 0)
        main_timeline_layout.addWidget(self.timeline_widget)
        main_timeline_layout.addWidget(self.timeline)
        timelines_layout.addWidget(main_timeline_container)
        
        second_timeline_container = QWidget(); 
        second_timeline_container.setMinimumHeight(50)
        second_timeline_container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: none;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                padding: 4px;
                background: none;
                margin: 2px;
            }
        """)
        second_timeline_layout = QVBoxLayout(second_timeline_container); 
        second_timeline_layout.setSpacing(2); 
        second_timeline_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- REPLACEMENT: Use CustomSlider instead of QSlider ---
        self.second_timeline = CustomSlider(Qt.Orientation.Horizontal, show_handle=True)
        self.second_timeline.sliderMoved.connect(lambda pos: self.setPosition(pos, from_main=False))
        self.second_timeline.sliderPressed.connect(self.sliderPressed)
        self.second_timeline.sliderReleased.connect(self.sliderReleased)
        self.second_timeline.setEnabled(False) 
        
        self.second_timeline_widget = TimelineWidget(self, show_position=True, is_main_timeline=False)
        second_timeline_layout.addWidget(self.second_timeline_widget)
        second_timeline_layout.addWidget(self.second_timeline)
        self.time_label = QLabel("00:00:00 / 00:00:00"); 
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        second_timeline_layout.addWidget(self.time_label)
        timelines_layout.addWidget(second_timeline_container)
        layout.addWidget(timelines_container, stretch=0)

        
        print("--- setupUI: Setting up shortcuts display...")
        self.shortcuts_container = QWidget()
        self.shortcuts_container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 15px;
                margin: 8px;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
                padding: 4px 8px;
                selection-background-color: transparent;
                selection-color: #ffffff;
            }
            QLabel[isHeader="true"] {
                color: #4a90e2;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                margin-bottom: 8px;
                border-bottom: 2px solid #4a90e2;
            }
            QLabel[isShortcut="true"] {
                background-color: #2a2a2a;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QLabel[isShortcut="true"]:hover {
                background-color: #353535;
            }
            QWidget[isColumn="true"] {
                background-color: #222222;
                border-radius: 6px;
                padding: 10px;
                margin: 5px;
            }
        """)
        shortcuts_layout = QHBoxLayout(self.shortcuts_container)
        shortcuts_layout.setSpacing(15)
        self._populate_shortcuts(shortcuts_layout) 
        layout.addWidget(self.shortcuts_container, stretch=0)

        
        print("--- setupUI: Setting up controls...")
        controls_container = QWidget()
        controls_container.setStyleSheet("""
            QWidget { background-color: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 6px; margin: 8px; }
            QPushButton { padding: 8px 16px; background-color: #4a90e2; color: white; border: none; border-radius: 4px; min-width: 100px; }
            QPushButton:hover { background-color: #357abd; } QPushButton:pressed { background-color: #2a5f9e; }
            QPushButton:disabled { background-color: #555; color: #999; }
        """)
        controls_layout = QHBoxLayout(controls_container); controls_layout.setSpacing(10); 
        controls_layout.setContentsMargins(12, 8, 12, 8)
        
        left_controls = QWidget(); left_layout = QHBoxLayout(left_controls); 
        left_layout.setSpacing(10); left_layout.setContentsMargins(0, 0, 0, 0)
        self.play_pause_button = QPushButton("Play")
        self.play_pause_button.setToolTip("Play/Pause the video (Spacebar)")
        self.play_pause_button.setEnabled(False)
        
        self.speed_label = QLabel("1.0x")
        self.speed_label.setStyleSheet("QLabel { color: white; padding: 8px; background-color: #2a2a2a; border-radius: 4px; min-width: 50px; text-align: center; }")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_offset_label = QLabel(f"Skip: {self.PREVIEW_OFFSET / 1000:.1f}s")
        self.preview_offset_label.setStyleSheet("QLabel { color: white; padding: 8px; background-color: #2a2a2a; border-radius: 4px; text-align: center; }")
        self.preview_offset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addWidget(self.play_pause_button)
        left_layout.addWidget(self.speed_label)
        left_layout.addWidget(self.preview_offset_label)
        
        right_controls = QWidget(); right_layout = QHBoxLayout(right_controls); right_layout.setSpacing(10); right_layout.setContentsMargins(0, 0, 0, 0)
        self.open_button = QPushButton("Open Video"); self.open_button.setToolTip("Open a video file for annotation")
        self.gear_button = QPushButton("⚙")
        self.gear_button.setToolTip("Settings")
        self.gear_button.setStyleSheet("""
            QPushButton {
                padding: 8px 12px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                min-width: 40px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a5f9e;
            }
            QPushButton::menu-indicator {
                width: 0px;
            }
        """)
        right_layout.addWidget(self.open_button); right_layout.addWidget(self.gear_button)
        controls_layout.addWidget(left_controls); controls_layout.addStretch(); controls_layout.addWidget(right_controls)
        layout.addWidget(controls_container)

        
        print("--- setupUI: Connecting UI signals...")
        
        
        
        
        
        
        
        self.play_pause_button.clicked.connect(self.togglePlayPause)
        self.open_button.clicked.connect(self.openFile)
        
        self.settings_menu = QMenu(self); self.settings_menu.setStyleSheet("QMenu { background-color: #2b2b2b; border: 1px solid #3a3a3a; } QMenu::item { padding: 8px 20px; color: white; } QMenu::item:selected { background-color: #4a90e2; }")
        load_action = QAction("Load JSON", self); load_action.triggered.connect(self.loadAnnotations)
        export_action = QAction("Export Labels", self); export_action.triggered.connect(self.saveAnnotations)
        new_video_action = QAction("New Video", self); new_video_action.triggered.connect(self.openFile)
        self.rotate_action = QAction("Rotate Video", self); self.rotate_action.setEnabled(False); self.rotate_action.triggered.connect(self.rotateVideo) 
        self.toggle_shortcuts_action = QAction("Hide Shortcuts", self); self.toggle_shortcuts_action.triggered.connect(self.toggleShortcutsWidget)
        self.settings_menu.addAction(load_action); self.settings_menu.addAction(export_action); self.settings_menu.addAction(new_video_action)
        self.settings_menu.addSeparator(); self.settings_menu.addAction(self.rotate_action); self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.toggle_shortcuts_action)
        self.gear_button.setMenu(self.settings_menu)
        print("--- setupUI: Finished.")


    def _populate_shortcuts(self, parent_layout):
        """Helper to create the shortcut display columns."""
        
        shortcut_data = {
            "🎥 Video Controls": [
                "⎵ Spacebar - Play/Pause", "←/→ - Skip 10s backward/forward",
                "↑/↓ - Increase/decrease speed", "R - Reset speed to 1x"
            ],
            "🏷️ Labeling Controls": [
                "A - Start/Stop labeling", "Z - Cancel labeling", "S - Delete label",
                "G - Open label dialog", "P - Split label"
            ],
            "🔍 Navigation": [
                "Shift+←/→ - Previous/Next label", "N - Merge with previous",
                "M - Merge with next", "Shift+↑/↓ - Adjust preview skip"
            ],
            "📝 Dialog Controls": [
                "1 - Select Posture", "2 - Select High Level Behavior", "3 - Select PA Type",
                "4 - Select Behavioral Parameters", "5 - Select Experimental Situation"
            ]
        }
        for header_text, shortcuts in shortcut_data.items():
            col_widget = QWidget(); col_widget.setProperty("isColumn", True)
            col_layout = QVBoxLayout(col_widget)
            header = QLabel(header_text); header.setProperty("isHeader", True)
            col_layout.addWidget(header)
            for sc_text in shortcuts:
                label = QLabel(sc_text); label.setProperty("isShortcut", True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
                col_layout.addWidget(label)
            col_layout.addStretch()
            parent_layout.addWidget(col_widget)


    def loadQmlSources(self):
        """Loads the QML source file into the QuickWidgets."""
    
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            base_path = os.path.join(sys._MEIPASS, 'src')
        else:
            # Running in development
            base_path = os.path.dirname(__file__)
        
        qml_file_path = os.path.join(base_path, 'VideoPlayer.qml')

        print(f"--- [LOAD] Attempting QML load from: {qml_file_path}")
        if not os.path.exists(qml_file_path):
            print(f"--- [LOAD] ERROR: QML file not found at {qml_file_path}")
            QMessageBox.critical(self, "QML Error", f"Cannot find QML file:\n{qml_file_path}")
            return

        if hasattr(self, 'quick_widget_main'):
            print(f"--- [LOAD] Setting main source...")
            self.quick_widget_main.setSource(QUrl.fromLocalFile(qml_file_path))

        if hasattr(self, 'quick_widget_preview'):
            print(f"--- [LOAD] Setting preview source...")
            self.quick_widget_preview.setSource(QUrl.fromLocalFile(qml_file_path))


    
    
    def onQmlMainStatusChanged(self, status):
        is_already_ready = self._qml_main_ready
        if status == QQuickWidget.Status.Ready and is_already_ready:
             print("--- onQmlMainStatusChanged: Already marked as ready, skipping.")
             return
        if status == QQuickWidget.Status.Null and is_already_ready:
             print("--- onQmlMainStatusChanged: Status changed back to Null, resetting ready flag.")
             self._qml_main_ready = False
             self.checkQmlReadyAndLoadPending() 

        print(f"--- onQmlMainStatusChanged received status: {status} (Enum: {QQuickWidget.Status(status).name}) (Current ready flag: {self._qml_main_ready})")
        if status == QQuickWidget.Status.Ready:
            if not is_already_ready: 
                print("QML Main changing status to Ready")
                self.qml_root_main = self.quick_widget_main.rootObject()
                if self.qml_root_main:
                    self._qml_main_ready = True
                    print("--- Connecting QML signals for Main...")
                    # try: 
                    #     self.qml_root_main.qmlPositionChanged.disconnect(self.qmlPositionChanged)
                    #     self.qml_root_main.qmlDurationChanged.disconnect(self.qmlDurationChanged)
                    #     self.qml_root_main.qmlPlaybackStateChanged.disconnect(self.qmlPlaybackStateChanged)
                    #     self.qml_root_main.qmlMediaStatusChanged.disconnect(self.qmlMediaStatusChanged)
                    #     self.qml_root_main.qmlErrorOccurred.disconnect(self.qmlErrorOccurred)
                    #     self.qml_root_main.qmlPlaybackRateChanged.disconnect(self.qmlPlaybackRateChanged)
                    # except RuntimeError: pass 
                    self.qml_root_main.qmlPositionChanged.connect(self.qmlPositionChanged)
                    self.qml_root_main.qmlDurationChanged.connect(self.qmlDurationChanged)
                    self.qml_root_main.qmlPlaybackStateChanged.connect(self.qmlPlaybackStateChanged)
                    self.qml_root_main.qmlMediaStatusChanged.connect(self.qmlMediaStatusChanged)
                    self.qml_root_main.qmlErrorOccurred.connect(self.qmlErrorOccurred)
                    self.qml_root_main.qmlPlaybackRateChanged.connect(self.qmlPlaybackRateChanged)
                    self.qml_root_main.setProperty('orientation', self.current_rotation)
                    self.checkQmlReadyAndLoadPending()
                else:
                    print("Error: QML Main rootObject is null after Ready status")
                    self._qml_main_ready = False 
        elif status == QQuickWidget.Status.Error:
            print("--- Error status received for main QML:")
            for error in self.quick_widget_main.errors(): print(f"    {error.toString()}")
            QMessageBox.critical(self, "QML Error", "Failed to load main video player QML component.")
            self._qml_main_ready = False

    
    def onQmlPreviewStatusChanged(self, status):
        is_already_ready = self._qml_preview_ready
        if status == QQuickWidget.Status.Ready and is_already_ready:
            print("--- onQmlPreviewStatusChanged: Already marked as ready, skipping.")
            return
        if status == QQuickWidget.Status.Null and is_already_ready:
            print("--- onQmlPreviewStatusChanged: Status changed back to Null, resetting ready flag.")
            self._qml_preview_ready = False
            self.checkQmlReadyAndLoadPending() 

        print(f"--- onQmlPreviewStatusChanged received status: {status} (Enum: {QQuickWidget.Status(status).name}) (Current ready flag: {self._qml_preview_ready})")
        if status == QQuickWidget.Status.Ready:
             if not is_already_ready:
                print("QML Preview changing status to Ready")
                self.qml_root_preview = self.quick_widget_preview.rootObject()
                if self.qml_root_preview:
                    self._qml_preview_ready = True
                    self.qml_root_preview.setProperty('isPreview', True)
                    self.qml_root_preview.setProperty('orientation', self.current_rotation)
                    self.checkQmlReadyAndLoadPending()
                else:
                    print("Error: QML Preview rootObject is null after Ready status")
                    self._qml_preview_ready = False
        elif status == QQuickWidget.Status.Error:
            print("--- Error status received for preview QML:")
            for error in self.quick_widget_preview.errors(): print(f"    {error.toString()}")
            QMessageBox.critical(self, "QML Error", "Failed to load preview video player QML component.")
            self._qml_preview_ready = False


    def checkQmlReadyAndLoadPending(self):
        """Checks if both QML instances are ready, enables UI, and loads pending source."""
        qml_is_fully_ready = self._qml_main_ready and self._qml_preview_ready
        print(f"--- checkQmlReadyAndLoadPending called. Fully Ready: {qml_is_fully_ready}")

        
        self.play_pause_button.setEnabled(qml_is_fully_ready and self.media_player['_duration'] > 0)
        self.rotate_action.setEnabled(qml_is_fully_ready)
        self.timeline.setEnabled(qml_is_fully_ready and self.media_player['_duration'] > 0)
        self.second_timeline.setEnabled(qml_is_fully_ready and self.media_player['_duration'] > 0)
        

        if qml_is_fully_ready:
            print("--- Both QML instances ready.")
            if self._pending_source_url:
                print(f"--- Found pending URL: {self._pending_source_url.toString()}. Calling setQmlSource.")
                url_to_load = self._pending_source_url
                self._pending_source_url = None
                self.setQmlSource(url_to_load)
            else:
                self._update_ui_from_state()
        else:
            print("--- One or both QML instances not ready yet.")


    def setQmlSource(self, source_url: QUrl):
         """Sets the source property on both QML players."""
         print(f"--- setQmlSource called with URL: {source_url.toString()}")
         if not (self.qml_root_main and self.qml_root_preview):
              print("--- Warning: setQmlSource called but QML root object(s) missing.")
              self._pending_source_url = source_url 
              return

         
         self.media_player['_duration'] = 0
         self.media_player['_position']
         self.media_player['_playback_state'] = 0 
         self.media_player['_playback_rate'] = 1.0
         self._update_ui_from_state() 

         print(f"--- Setting source property on QML Main...")
         success_main = self.qml_root_main.setProperty('source', source_url)
         print(f"--- Set main source success: {success_main}")
         print(f"--- Setting source property on QML Preview...")
         success_preview = self.qml_root_preview.setProperty('source', source_url)
         print(f"--- Set preview source success: {success_preview}")

         
         self.play_pause_button.setEnabled(False)
         self.timeline.setEnabled(False)
         self.second_timeline.setEnabled(False)

    def qmlPositionChanged(self, position):
        if self.media_player['_duration'] <= 0:
            return

        self.media_player['_position'] = int(position)
        current_pos_percent = position / self.media_player['_duration']
        zoom_width = self.zoom_end - self.zoom_start
        edge_threshold = 0.2
        smoothing_factor = 0.05
        target_zoom_start = self.zoom_start
        scroll_trigger_right = self.zoom_end - (zoom_width * edge_threshold)
        scroll_trigger_left = self.zoom_start + (zoom_width * edge_threshold)

        if current_pos_percent > scroll_trigger_right:
            target_zoom_start = current_pos_percent - (zoom_width * (1 - edge_threshold))
        elif current_pos_percent < scroll_trigger_left:
            target_zoom_start = current_pos_percent - (zoom_width * edge_threshold)

        target_zoom_start = max(0.0, min(target_zoom_start, 1.0 - zoom_width))
        self.zoom_start += (target_zoom_start - self.zoom_start) * smoothing_factor
        self.zoom_start = max(0.0, min(self.zoom_start, 1.0 - zoom_width))
        self.zoom_end = self.zoom_start + zoom_width

        if not self.timeline.isSliderDown():
            self.timeline.setValue(self.media_player['_position'])

        if not self.second_timeline.isSliderDown():
            zoom_duration_ms = zoom_width * self.media_player['_duration']
            zoom_start_ms = self.zoom_start * self.media_player['_duration']
            max_slider_val = self.second_timeline.maximum()

            if position >= zoom_start_ms and position <= (zoom_start_ms + zoom_duration_ms) and zoom_duration_ms > 0 and max_slider_val > 0:
                relative_pos_in_zoom = (position - zoom_start_ms) / zoom_duration_ms
                slider_value = int(relative_pos_in_zoom * max_slider_val)
                self.second_timeline.setValue(slider_value)
            elif position < zoom_start_ms:
                self.second_timeline.setValue(0)
            else:
                self.second_timeline.setValue(max_slider_val)

        current_time = QTime(0, 0).addMSecs(self.media_player['_position']).toString('hh:mm:ss')
        total_time = QTime(0, 0).addMSecs(self.media_player['_duration']).toString('hh:mm:ss')
        self.time_label.setText(f"{current_time} / {total_time}")

        if hasattr(self, 'timeline_widget'):
            self.timeline_widget.update()
        if hasattr(self, 'second_timeline_widget'):
            self.second_timeline_widget.update()

        
        

    
    def qmlDurationChanged(self, duration):
        new_duration = int(duration) 
        if new_duration != self.media_player['_duration']:
            print(f"--- Duration changed: {new_duration} ms")
            self.media_player['_duration'] = new_duration
            has_duration = self.media_player['_duration'] > 0
            
            self.timeline.setRange(0, self.media_player['_duration'] if has_duration else 0)
            self.second_timeline.setRange(0, self.media_player['_duration'] if has_duration else 0)
            self.timeline.setEnabled(has_duration)
            self.second_timeline.setEnabled(has_duration)

            if has_duration:
                self._setup_timeline_zoom()
                
                current_time = QTime(0, 0).addMSecs(self.media_player['_position']).toString('hh:mm:ss')
                total_time = QTime(0, 0).addMSecs(self.media_player['_duration']).toString('hh:mm:ss')
                self.time_label.setText(f"{current_time} / {total_time}")
            else:
                self.time_label.setText("00:00:00 / 00:00:00")
            
            if hasattr(self, 'timeline_widget'): self.timeline_widget.update()
            if hasattr(self, 'second_timeline_widget'): self.second_timeline_widget.update()


    
    def qmlPlaybackStateChanged(self, state):
        
        if state != self.media_player['_playback_state']:
             
             state_str_map = {0:'Stopped', 1:'Playing', 2:'Paused'}
             print(f"--- Playback state changed: {state} ({state_str_map.get(state, 'Unknown')})")
             self.media_player['_playback_state'] = state
             self.updatePlayPauseButton(state)

    
    def _calculate_preview_offset(self):
        """Calculates the preview offset based on current playback speed."""
        return int(self.BASE_PREVIEW_OFFSET * self.media_player['_playback_rate'])

    def qmlPlaybackRateChanged(self, rate):
        if rate != self.media_player['_playback_rate']:
             print(f"--- Playback rate changed (from QML): {rate}")
             self.media_player['_playback_rate'] = rate
             self.updateSpeedLabel(rate)
             # Update preview offset based on new speed
             self.PREVIEW_OFFSET = self._calculate_preview_offset()
             self._sync_preview_qml_position(self.media_player['_position'])
             self.preview_offset_label.setText(f"Skip: {self.PREVIEW_OFFSET / 1000:.1f}s")

    
    def qmlMediaStatusChanged(self, status):
        
        status_map = {0:"NoMedia", 1:"LoadingMedia", 2:"LoadedMedia", 3:"Prepared", 4:"BufferingMedia", 5:"StalledMedia", 6:"EndOfMedia", 7:"InvalidMedia"}
        print(f"--- QML Media Status Changed: {status} ({status_map.get(status, 'Unknown')})")
        media_is_ready = (status == 2 or status == 3) 
        media_is_invalid = (status == 7)
        media_has_ended = (status == 6)

        if media_is_ready:
             if self.media_player['_duration'] == 0:  # Only setup zoom on initial load
                 self._setup_timeline_zoom()
             print("--- Media loaded/prepared (QML), enabling controls & updating UI state")
             
             self.qmlDurationChanged(self.qml_root_main.property('duration'))
             self.qmlPositionChanged(self.qml_root_main.property('position'))
             self.play_pause_button.setEnabled(True)
                          
        elif media_has_ended:
             print("--- End of Media (QML)")
             
        elif media_is_invalid:
             error_str = self.qml_root_main.property('errorString') if self.qml_root_main else "Unknown error"
             source_str = self.qml_root_main.property('source').toString() if self.qml_root_main else "N/A"
             QMessageBox.critical(self, "Media Error", f"QML MediaPlayer reported Invalid Media.\nError: {error_str}\nSource: {source_str}")
             self.current_video_path = None
             if self.autosave_timer.isActive(): self.autosave_timer.stop()
             self.play_pause_button.setEnabled(False)
             self.timeline.setEnabled(False)
             self.second_timeline.setEnabled(False)


    
    def qmlErrorOccurred(self, error, errorString):
        
        
        if error != 0:
            print(f"--- QML MediaPlayer Error: {error} - {errorString}")
            QMessageBox.critical(self, "QML Playback Error", f"Error: {errorString} (Code: {error})")
            self.play_pause_button.setEnabled(False)
            self.timeline.setEnabled(False)
            self.second_timeline.setEnabled(False)


    def _update_ui_from_state(self):
         """Update Python UI based on tracked state. Call when QML might not emit signals (e.g., init)."""
         print("--- _update_ui_from_state called")
         self.updatePlayPauseButton(self.media_player['_playback_state'])
         self.updateSpeedLabel(self.media_player['_playback_rate'])
         self.qmlDurationChanged(self.media_player['_duration']) 
         self.qmlPositionChanged(self.media_player['_position']) 


    

    
    def openFile(self):
        print("--- openFile triggered")
        
        self.current_rotation = 0
        if self._qml_main_ready: self.qml_root_main.setProperty('orientation', 0)
        if self._qml_preview_ready: self.qml_root_preview.setProperty('orientation', 0)

        filename, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if filename:
            print(f"--- User selected file: {filename}")
            self.current_video_path = filename
            try: self.video_hash = self.autosave_manager.calculate_video_hash(filename)
            except Exception as e: self.video_hash = 0; print(f"Warn: Hash failed {e}")

            
            self.annotations = [] 
            autosave_data, hash_matches = self.autosave_manager.check_for_autosave(filename, self.video_hash)
            if autosave_data:
                message = "An autosaved version of the annotations was found."
                if self.video_hash != 0 and not hash_matches:
                    message += "\nWarning: The video file appears to have changed since the autosave."
                message += "\nWould you like to restore from autosave or start over?"
                reply = QMessageBox.question(self, "Autosave Found", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                    try: 
                        print("--- Restoring annotations from autosave...")
                        loaded_count = 0
                        for ann_data in autosave_data.get("annotations", []):
                             
                             if "id" in ann_data and "range" in ann_data and "start" in ann_data["range"] and "end" in ann_data["range"]:
                                 annotation = TimelineAnnotation()
                                 annotation.id = ann_data["id"]
                                 annotation.start_time = ann_data["range"]["start"] 
                                 annotation.end_time = ann_data["range"]["end"] 
                                 annotation.shape = ann_data.get("shape", {})
                                 annotation.comments = ann_data.get("comments", [])
                                 self.annotations.append(annotation)
                                 loaded_count += 1
                             else:
                                 print(f"--- Warning: Skipping invalid autosave annotation data: {ann_data}")
                        self.updateAnnotationTimeline()
                        print(f"--- Loaded {loaded_count} annotations from autosave.")
                    except Exception as e: QMessageBox.critical(self, "Autosave Error", f"Failed to load autosave: {e}"); self.annotations = []
                else:
                    print("--- User chose not to restore autosave. Deleting...")
                    self.autosave_manager.delete_autosave(filename)
                    self.updateAnnotationTimeline() 
            else:
                print("--- No autosave data found.")
                self.updateAnnotationTimeline() 

            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle - ensure proper URL format
                from urllib.parse import quote
                filename = quote(filename)
                if not filename.startswith('/'):
                    filename = '/' + filename
                url = QUrl('file://' + filename)
            else:
                # Running in development
                url = QUrl.fromLocalFile(filename)
            
            if not url.isValid():
                print(f"--- Error: Invalid URL generated for file: {filename}")
                QMessageBox.critical(self, "File Error", f"Invalid file URL generated:\n{url.toString()}")
                return
            
            print(f"--- Converted to QUrl: {url.toString()}")

            
            if self._qml_main_ready and self._qml_preview_ready:
                 print("--- QML ready, calling setQmlSource immediately.")
                 self.setQmlSource(url)
            else:
                 print("--- QML not ready, storing URL in _pending_source_url.")
                 self._pending_source_url = url

            if not self.autosave_timer.isActive():
                print("--- Starting autosave timer.")
                self.autosave_timer.start()
        else:
             print("--- File selection cancelled.")


    
    def togglePlayPause(self):
        if not self.qml_root_main or not self.current_video_path:
             print("--- togglePlayPause: Aborted (QML main root missing or no video path)")
             return

        
        print(f"--- togglePlayPause: Current state = {self.media_player['_playback_state']}")
        if self.media_player['_playback_state'] == 1:
            print("--- Commanding QML Pause...")
            self.qml_root_main.pause()
            self.qml_root_preview.pause()
        else: 
            print("--- Commanding QML Play...")
            self._sync_preview_qml_position(self.media_player['_position']) 
            self.qml_root_main.play()
            self.qml_root_preview.play()


    
    def updatePlayPauseButton(self, state):
        
        self.play_pause_button.setText("Pause" if state == 1 else "Play")
        
        media_has_duration = self.media_player['_duration'] > 0
        qml_ready = self._qml_main_ready and self._qml_preview_ready
        self.play_pause_button.setEnabled(media_has_duration and qml_ready)
    
    def adjustPreviewOffset(self, offset):
        """Adjusts the base preview offset for the QML player."""
        base_offset_change = offset / self.media_player['_playback_rate']  # Compensate for speed scaling
        self.BASE_PREVIEW_OFFSET = max(0, self.BASE_PREVIEW_OFFSET + base_offset_change)
        self.PREVIEW_OFFSET = self._calculate_preview_offset()
        if self.qml_root_preview:
            self._sync_preview_qml_position(self.media_player['_position'])
            print(f"--- Adjusted base preview offset to: {self.BASE_PREVIEW_OFFSET} ms (effective: {self.PREVIEW_OFFSET} ms)")
            self.preview_offset_label.setText(f"Skip: {self.PREVIEW_OFFSET / 1000:.1f}s")
        else:
            print("--- adjustPreviewOffset: QML preview root missing.")


    
    def updateSpeedLabel(self, rate):
        self.speed_label.setText(f"{rate:.1f}x")

    def setPlaybackRate(self, rate):
        """Sets the playback rate on the QML player."""
        if self.qml_root_main:            
             clamped_rate = max(0.1, min(rate, 16.0)) 
             if clamped_rate != self.media_player['_playback_rate']:
                 print(f"--- Setting playback rate via Python: {clamped_rate}")
                 self.qml_root_main.setProperty('playbackRate', clamped_rate)
                 self.updateSpeedLabel(clamped_rate)
                 # Update preview offset based on new speed
                 self.PREVIEW_OFFSET = self._calculate_preview_offset()
                 self._sync_preview_qml_position(self.media_player['_position'])
        if self.qml_root_preview:
            
            self.qml_root_preview.setProperty('playbackRate', clamped_rate)
        else:
            print("--- setPlaybackRate: QML not ready.")


    def changePlaybackRate(self, delta):
         """Adjusts playback rate by delta."""
         
         new_rate = self.media_player['_playback_rate'] + delta
         self.setPlaybackRate(new_rate)

    def resetPlaybackRate(self):
         """Resets playback rate to 1.0x."""
         self.setPlaybackRate(1.0)

    def resetPreviewOffset(self):
        """Resets the preview offset to default."""
        if self.qml_root_preview:
            self._sync_preview_qml_position(self.media_player['_position'])
            print(f"--- Reset preview offset to default: {self.BASE_PREVIEW_OFFSET} ms (effective: {self.PREVIEW_OFFSET} ms)")
            self.preview_offset_label.setText(f"Skip: {self.PREVIEW_OFFSET / 1000:.1f}s")
        else:
            print("--- resetPreviewOffset: QML preview root missing.")
    

    def setPosition(self, position, from_main=True):
        """Sets the position of the QML player."""
        if not self.qml_root_main or not self.current_video_path: return

        # Calculate target position based on which timeline was used
        if from_main:
            target_position = position
        else:
            # Convert zoomed timeline position to full timeline position
            zoom_duration = (self.zoom_end - self.zoom_start) * self.media_player['_duration']
            zoom_start = self.zoom_start * self.media_player['_duration']
            max_slider_val = self.second_timeline.maximum()
            relative_pos_in_zoom = position / max_slider_val if max_slider_val > 0 else 0
            target_position = int(zoom_start + (relative_pos_in_zoom * zoom_duration))
        
        print(f"--- Seeking main player to: {target_position} ms")
        self.qml_root_main.seek(target_position)
        self.qml_root_preview.seek(target_position + self.PREVIEW_OFFSET)
        self.media_player['_position'] = target_position

        self.timeline.setValue(target_position)
        
        if self.media_player['_duration'] > 0:
            zoom_duration = (self.zoom_end - self.zoom_start) * self.media_player['_duration']
            zoom_start = self.zoom_start * self.media_player['_duration']
            if target_position >= zoom_start and target_position <= (zoom_start + zoom_duration):
                relative_pos = (target_position - zoom_start) / zoom_duration
                self.second_timeline.setValue(int(relative_pos * self.second_timeline.maximum()))
            elif target_position < zoom_start:
                self.second_timeline.setValue(0)
            else:
                self.second_timeline.setValue(self.second_timeline.maximum())

    def _setup_timeline_zoom(self):
         """Sets timeline zoom state variables based on duration."""
         if self.media_player['_duration'] <= 0: return
         if self.media_player['_duration'] < self.MIN_ZOOM_DURATION:
             self.zoom_start = 0.0; self.zoom_end = 1.0
         else:
             self.zoom_start = 0.0; self.zoom_end = 0.2 
         print(f"--- Timeline zoom set: start={self.zoom_start}, end={self.zoom_end}")
         

    
    def updateAnnotationTimeline(self):
        print("--- updateAnnotationTimeline called ---")
        if hasattr(self, 'timeline_widget'): self.timeline_widget.update()
        if hasattr(self, 'second_timeline_widget'): self.second_timeline_widget.update()
    
    # In VideoPlayerApp class
    def _sync_preview_qml_position(self, main_position):
        """Seeks the preview player to main_position + offset."""
        if not self.qml_root_preview or self.media_player['_duration'] <= 0: return

        # If we are navigating, sync exactly. Otherwise, add the offset.
        if self._is_navigating:
            target_preview_pos = main_position
        else:
            target_preview_pos = main_position + self.PREVIEW_OFFSET

        target_preview_pos = max(0, min(target_preview_pos, self.media_player['_duration']))
        current_preview_pos = self.qml_root_preview.property('position')

        is_seeking = self.timeline.isSliderDown() or self.second_timeline.isSliderDown()

        if abs(target_preview_pos - current_preview_pos) > self.SYNC_THRESHOLD or is_seeking or self._is_navigating:
            self.qml_root_preview.seek(target_preview_pos)

    def saveAnnotations(self):
        from zipfile import ZipFile
        import csv
        import io
        from datetime import datetime, timedelta

        filename, _ = QFileDialog.getSaveFileName(self, "Export Annotations", "", "ZIP Files (*.zip)")
        if filename:
            try:
                with ZipFile(filename, 'w') as zipf:
                    annotations_data = {
                        "annotations": [],
                        "videoHash": self.video_hash
                    }
                    
                    for annotation in self.annotations:
                        annotations_data["annotations"].append({
                            "id": annotation.id,
                            "range": {
                                "start": annotation.start_time,
                                "end": annotation.end_time
                            },
                            "shape": annotation.shape,
                            "comments": annotation.comments
                        })
                    
                    zipf.writestr('labels.json', json.dumps(annotations_data, indent=4))

                    if self.current_video_path and os.path.exists(self.current_video_path):
                        video_timestamp = os.path.getmtime(self.current_video_path)
                        video_date = datetime.fromtimestamp(video_timestamp)
                    else:
                        video_date = datetime.now()
                    
                    date_only = video_date.replace(hour=0, minute=0, second=0, microsecond=0)

                    headers = {
                        'POSTURE.csv': [],
                        'HIGH LEVEL BEHAVIOR.csv': [],
                        'PA TYPE.csv': [],
                        'Behavioral Parameters.csv': [],
                        'Experimental situation.csv': [],
                        'Special Notes.csv': []
                    }

                    for annotation in self.annotations:
                        try:
                            comment_data = json.loads(annotation.comments[0]["body"])
                            start_offset = timedelta(seconds=annotation.start_time)
                            end_offset = timedelta(seconds=annotation.end_time)

                            start_datetime = video_date + start_offset
                            end_datetime = video_date + end_offset
                            
                            video_start_datetime = date_only + start_offset
                            video_end_datetime = date_only + end_offset
                            
                            start_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
                            end_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")
                            video_start_str = video_start_datetime.strftime("%Y-%m-%d %H:%M:%S")
                            video_end_str = video_end_datetime.strftime("%Y-%m-%d %H:%M:%S")
                           
                            category_values = {}
                            for item in comment_data:
                                category = item["category"]
                                selected_value = item["selectedValue"]
                                
                                if isinstance(selected_value, list):
                                    values = [v for v in selected_value if v and not v.endswith("_Unlabeled")]
                                else:
                                    values = [selected_value] if selected_value and not selected_value.endswith("_Unlabeled") else []
                                
                                if values:
                                    category_values[category] = values
                            
                            # Create CSV rows - one row per category
                            labelset_map = {
                                "POSTURE": "Posture",
                                "HIGH LEVEL BEHAVIOR": "High Level Behavior",
                                "PA TYPE": "PA Type",
                                "Behavioral Parameters": "Behavioral Parameters",
                                "Experimental situation": "Experimental Situation",
                                "Special Notes": "Special Notes"
                            }
                            
                            for category, csv_file in [
                                ("POSTURE", 'POSTURE.csv'),
                                ("HIGH LEVEL BEHAVIOR", 'HIGH LEVEL BEHAVIOR.csv'),
                                ("PA TYPE", 'PA TYPE.csv'),
                                ("Behavioral Parameters", 'Behavioral Parameters.csv'),
                                ("Experimental situation", 'Experimental situation.csv'),
                                ("Special Notes", 'Special Notes.csv')
                            ]:
                                if category in category_values and category_values[category]:
                                    prediction = ", ".join(category_values[category])
                                    headers[csv_file].append([
                                        start_str, end_str,
                                        prediction, 'Expert', labelset_map[category],
                                        video_start_str, video_end_str
                                    ])
                        except Exception as e:
                            print(f"Error processing annotation {annotation.id}: {str(e)}")

                    csv_header = ['START_TIME','STOP_TIME','PREDICTION','SOURCE','LABELSET','VIDEO_START_TIME','VIDEO_END_TIME']
                    for filename, data in headers.items():
                        if data:  
                            output = io.StringIO()
                            writer = csv.writer(output)
                            writer.writerow(csv_header)
                            writer.writerows(data)
                            zipf.writestr(filename, output.getvalue())
                            output.close()

                QMessageBox.information(self, "Success", "Annotations exported successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export annotations: {str(e)}")
    
    
    def autosave(self):
        """Trigger autosave of current annotations"""
        if hasattr(self, 'current_video_path') and self.current_video_path:
            self.autosave_manager.save_annotations(
                self.current_video_path,
                self.annotations,
                video_hash=self.video_hash
            )
    
    
    def rotateVideo(self):
        """Rotates the video display using QML orientation."""
        if not self.qml_root_main or not self.qml_root_preview:
            print("--- rotateVideo: Aborted (QML not ready)")
            return

        self.current_rotation = (self.current_rotation + 90) % 360
        print(f"--- Setting orientation to: {self.current_rotation}")
        self.qml_root_main.setProperty('orientation', self.current_rotation)
        self.qml_root_preview.setProperty('orientation', self.current_rotation)
    
    
    def toggleShortcutsWidget(self):
        print("--- toggleShortcutsWidget called ---")
        if hasattr(self, 'shortcuts_container'):
            visible = self.shortcuts_container.isVisible()
            self.shortcuts_container.setVisible(not visible)
            self.toggle_shortcuts_action.setText("Show Shortcuts" if visible else "Hide Shortcuts")
    
    def loadAnnotations(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Annotations", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
       
                if self.current_video_path:
                    saved_hash = data.get("videoHash", 0)
                    if saved_hash != self.video_hash:
                        reply = QMessageBox.question(
                            self,
                            "Hash Mismatch",
                            "The video file used to create these annotations appears to be different.\n"
                            "Loading annotations from a different video may result in incorrect timings.\n"
                            "Would you like to continue loading anyway?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.No:
                            return
                
                self.annotations = []
                for ann_data in data.get("annotations", []):
                    annotation = TimelineAnnotation()
                    annotation.id = ann_data["id"]
                    annotation.start_time = ann_data["range"]["start"]
                    annotation.end_time = ann_data["range"]["end"]
                    annotation.shape = ann_data["shape"]
                    annotation.comments = ann_data["comments"]
                    self.annotations.append(annotation)
                
                self.updateAnnotationTimeline()
                if self.current_video_path:
                    self.autosave()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load annotations: {str(e)}")

    
    
    def sliderPressed(self):
        
        pass 

    
    def sliderReleased(self):
        
        pass

    
    
    
    def toggleAnnotation(self): self.annotation_manager.toggleAnnotation()
    
    def editAnnotation(self): 
        # Pause the video if it's playing else continue
        if self.media_player and self.media_player['_playback_state'] == 1:
            self.play_pause_button.click()
        self.annotation_manager.editAnnotation()
    
    def cancelAnnotation(self): self.annotation_manager.cancelAnnotation()
    
    def deleteCurrentLabel(self): self.annotation_manager.deleteCurrentLabel()
    
    def moveToPreviousLabel(self): 
        self._is_navigating = True
        self.annotation_manager.moveToPreviousLabel()
        QTimer.singleShot(100, lambda: setattr(self, '_is_navigating', False))
    
    def moveToNextLabel(self): 
        self._is_navigating = True
        self.annotation_manager.moveToNextLabel()
        QTimer.singleShot(100, lambda: setattr(self, '_is_navigating', False))

    def mergeWithPrevious(self): self.annotation_manager.mergeWithPrevious()
    
    def mergeWithNext(self): self.annotation_manager.mergeWithNext()
    
    def splitCurrentLabel(self): self.annotation_manager.splitCurrentLabel()
