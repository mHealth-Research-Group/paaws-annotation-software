import sys
import json
import csv
from collections import defaultdict

from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                           QPushButton, QWidget, QDialogButtonBox,
                           QGridLayout, QFrame, QScrollArea, QLayout, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint, QTimer, QSettings
from PyQt6.QtGui import QKeyEvent
from src.utils import resource_path
from src.custom_combo import SearchableComboBox, MultiSelectComboBox

# Constants
APP_NAME = "PAAWS-Annotation-Software"
ORGANIZATION_NAME = "PAAWS"
SETTINGS_DISABLE_ALERTS = "disableAlerts"

CAT_POSTURE = "POSTURE"
CAT_HLB = "HIGH LEVEL BEHAVIOR"
CAT_PA = "PA TYPE"
CAT_BP = "Behavioral Parameters"
CAT_ES = "Experimental situation"
CAT_NOTES = "Special Notes"

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.itemList = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(2 * margin.left() + 2 * margin.right(), 2 * margin.top() + 2 * margin.bottom())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.itemList:
            nextX = x + item.sizeHint().width() + spacing
            if nextX - spacing > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spacing
                nextX = x + item.sizeHint().width() + spacing
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

class TagWidget(QFrame):
    removed = pyqtSignal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            TagWidget { 
                background-color: #3d3d3d; 
                border-radius: 4px; 
                padding: 2px; 
                margin: 2px;
                border: 1px solid transparent;
            }
            TagWidget[invalid="true"] {
                border: 1px solid #e53935;
                background-color: #5f2a2a;
            }
            QPushButton { background-color: transparent; border: none; color: #888888; padding: 1px 6px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { color: #ffffff; }
            QLabel { color: #ffffff; margin: 0; padding: 2px 6px; font-size: 12px; background-color: transparent; border: none; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        
        self.label = QLabel(text)
        remove_btn = QPushButton("×")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.label.text()))
        
        layout.addWidget(self.label)
        layout.addWidget(remove_btn)

    def set_invalid(self, is_invalid):
        self.setProperty("invalid", is_invalid)
        self.style().polish(self)
        self.style().unpolish(self)

class SelectionWidget(QWidget):
    selectionChanged = pyqtSignal()
    userMadeSelection = pyqtSignal()

    def __init__(self, combo, active_label, multi_select=False, parent=None):
        super().__init__(parent)
        self.combo = combo
        self.active_label = active_label
        self.selected_values = []
        self.multi_select = multi_select
        self.unlabeled_text = ""
        self._is_typing = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        if multi_select:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
            scroll.setMinimumHeight(80)
            scroll.setMaximumHeight(120)
            self.tag_container = QWidget()
            self.tag_layout = FlowLayout(self.tag_container, margin=4, spacing=6)
            self.tag_container.setLayout(self.tag_layout)
            scroll.setWidget(self.tag_container)
            layout.addWidget(scroll)
        
        layout.addWidget(combo)

    def set_unlabeled_text(self, text):
        self.unlabeled_text = text
        self.set_values([text])

    def set_values(self, values):
        self.selected_values.clear()
        if self.multi_select:
            while self.tag_layout.count() > 0:
                item = self.tag_layout.takeAt(0)
                if item and item.widget(): item.widget().deleteLater()
        
        values_to_set = values if (values and values[0] is not None) else [self.unlabeled_text]
        # Ensure unlabeled text is removed if other values are present
        if len(values_to_set) > 1 and self.unlabeled_text in values_to_set:
            values_to_set.remove(self.unlabeled_text)

        for value in values_to_set: self._add_value(value)

        if not self.selected_values:
            self._add_value(self.unlabeled_text)
 
        if hasattr(self.combo, 'set_selected'):
            if self.multi_select:
                self.combo.set_selected(self.selected_values)
            else:
                self.combo.set_selected(self.selected_values[0] if self.selected_values else self.unlabeled_text)
        
        self._update_ui()
        self.selectionChanged.emit()

    def _handle_combo_activated(self, index):
        text = self.combo.itemText(index)
        if not text:
            return

        changed = False
        if not self.multi_select:
            if not self.selected_values or text != self.selected_values[0]:
                self.selected_values = [text]
                changed = True
        else:
            if text != self.unlabeled_text and text not in self.selected_values:
                if self.unlabeled_text in self.selected_values:
                    self._remove_value(self.unlabeled_text)
                self._add_value(text)
                changed = True
        
        if changed:
            self._update_ui()
            self.selectionChanged.emit()
            self.userMadeSelection.emit()

    def remove_tag(self, text):
        """Remove a tag and update selection"""
        self._remove_value(text)
        
        # If nothing left, add unlabeled
        if not self.selected_values:
            self._add_value(self.unlabeled_text)
        
        # Update the combo box to reflect changes
        if hasattr(self.combo, 'set_selected'):
            self.combo.set_selected(self.selected_values)
        
        self._update_ui()
        self.selectionChanged.emit()

    def _add_value(self, text):
        if text and text not in self.selected_values:
            self.selected_values.append(text)
            if self.multi_select:
                tag = TagWidget(text)
                tag.removed.connect(self.remove_tag)
                self.tag_layout.addWidget(tag)

    def _remove_value(self, text):
        if text in self.selected_values:
            self.selected_values.remove(text)
        if self.multi_select:
            for i in range(self.tag_layout.count()):
                item = self.tag_layout.itemAt(i)
                widget = item.widget() if item else None
                if isinstance(widget, TagWidget) and widget.label.text() == text:
                    self.tag_layout.takeAt(i); widget.deleteLater()
                    break

    def _update_ui(self):
        self.update_active_label()

    def update_active_label(self):
        if not self.selected_values:
            self.active_label.setText(self.unlabeled_text)
            return

        chunks, current_chunk = [], []
        valid_selections = [v for v in self.selected_values if v != self.unlabeled_text]
        if not valid_selections:
            self.active_label.setText(self.unlabeled_text)
            return

        for i, value in enumerate(valid_selections):
            current_chunk.append(value)
            if len(current_chunk) >= 2 or i == len(valid_selections) - 1:
                chunks.append(", ".join(current_chunk))
                current_chunk = []
        self.active_label.setText("\n".join(chunks))

    def set_invalid_style(self, is_invalid):
        self.setProperty("invalid", is_invalid)
        for widget in [self, self.combo, self.active_label]:
            widget.style().polish(widget); widget.style().unpolish(widget)

class AnnotationDialog(QDialog):
    def __init__(self, annotation=None, parent=None, is_editing=True):
        super().__init__(parent)
        self.setWindowTitle("Category Choices")
        self.setModal(True)
        self.setMinimumWidth(1200); self.setMinimumHeight(800)
        
        self.is_editing = is_editing
        self.settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        self.mappings = {}; self.full_categories = {}

        if not self.load_mappings() or not self.load_categories():
            QTimer.singleShot(0, self.reject); return

        self._init_ui()
        initial_data = self._get_initial_data(annotation)
        if initial_data:
            self._set_values_from_data(initial_data)

        self.disable_alerts_checkbox.stateChanged.connect(self._on_settings_change)

        self.pa_selection.selectionChanged.connect(self._update_filters)
        self.hlb_selection.selectionChanged.connect(self._update_filters)
        self.posture_selection.selectionChanged.connect(self._update_filters)
        
        self.pa_selection.userMadeSelection.connect(self._handle_user_validation)
        self.hlb_selection.userMadeSelection.connect(self._handle_user_validation)
        self.posture_selection.userMadeSelection.connect(self._handle_user_validation)

        self._run_validation_check(is_initial_load=True)

    def _init_ui(self):
        main_scroll = QScrollArea(); main_scroll.setWidgetResizable(True)
        main_widget = QWidget(); main_widget.setStyleSheet(self._get_stylesheet())
        main_layout = QVBoxLayout(main_widget); main_layout.setSpacing(24); main_layout.setContentsMargins(24, 24, 24, 24)
        
        options_layout = QHBoxLayout()
        self.disable_alerts_checkbox = QCheckBox("Disable all pop-up warnings")
        self.disable_alerts_checkbox.setChecked(self.settings.value(SETTINGS_DISABLE_ALERTS, False, type=bool))
        options_layout.addStretch(); options_layout.addWidget(self.disable_alerts_checkbox)
        main_layout.addLayout(options_layout)
        
        grid = QGridLayout()
        grid.setSpacing(16)
        # Fixed column widths to prevent resizing
        grid.setColumnMinimumWidth(0, 220)  # Category column
        grid.setColumnMinimumWidth(1, 350)  # Choices column
        grid.setColumnMinimumWidth(2, 300)  # Active labels column
        # Set stretch factors - only category column should not stretch
        grid.setColumnStretch(0, 0)  # Category - fixed width
        grid.setColumnStretch(1, 2)  # Choices - can stretch
        grid.setColumnStretch(2, 1)  # Active labels - can stretch less
        
        headers = ["Category", "Choice(s)", "Active labels"]
        for i, header in enumerate(headers):
            label = QLabel(header)
            label.setObjectName("headerLabel")
            grid.addWidget(label, 0, i)
        
        # Create custom combo boxes
        self.posture_combo = SearchableComboBox()
        self.hlb_combo = MultiSelectComboBox()
        self.pa_combo = SearchableComboBox()
        self.bp_combo = MultiSelectComboBox()
        self.es_combo = SearchableComboBox()
        
        self.posture_active, self.hlb_active, self.pa_active, self.bp_active, self.es_active = (QLabel() for _ in range(5))
        
        # Set size policies for active labels to prevent excessive expansion
        for label in [self.posture_active, self.hlb_active, self.pa_active, self.bp_active, self.es_active]:
            label.setWordWrap(True)
            label.setMinimumWidth(250)
        
        self.posture_selection = SelectionWidget(self.posture_combo, self.posture_active, multi_select=False)
        self.hlb_selection = SelectionWidget(self.hlb_combo, self.hlb_active, multi_select=True)
        self.pa_selection = SelectionWidget(self.pa_combo, self.pa_active, multi_select=False)
        self.bp_selection = SelectionWidget(self.bp_combo, self.bp_active, multi_select=True)
        self.es_selection = SelectionWidget(self.es_combo, self.es_active, multi_select=False)
        self.all_selections = { CAT_POSTURE: self.posture_selection, CAT_HLB: self.hlb_selection, CAT_PA: self.pa_selection }

        self._populate_combos()

        categories_setup = [
            (f"{CAT_POSTURE} (Key 1)", self.posture_selection, self.posture_active),
            (f"{CAT_HLB} (Key 2)", self.hlb_selection, self.hlb_active),
            (f"{CAT_PA} (Key 3)", self.pa_selection, self.pa_active),
            (f"{CAT_BP} (Key 4)", self.bp_selection, self.bp_active),
            (f"{CAT_ES} (Key 5)", self.es_selection, self.es_active)
        ]
        for row, (title, sel, active) in enumerate(categories_setup, 1):
            label = QLabel(title); label.setProperty("category", "true")
            grid.addWidget(label, row, 0); grid.addWidget(sel, row, 1); grid.addWidget(active, row, 2)
        main_layout.addLayout(grid)
        
        notes_container = QWidget(); notes_container.setObjectName("notesContainer")
        notes_layout = QVBoxLayout(notes_container); notes_layout.setSpacing(12)
        notes_label = QLabel(f"{CAT_NOTES} (Key 6)"); notes_label.setProperty("category", "true")
        notes_layout.addWidget(notes_label)
        notes_sublabel = QLabel("Maximum 255 characters"); notes_sublabel.setObjectName("notesSublabel")
        notes_layout.addWidget(notes_sublabel)
        self.notes_edit = QLineEdit(); self.notes_edit.setMaxLength(255); self.notes_edit.setPlaceholderText("Enter any special notes here...")
        notes_layout.addWidget(self.notes_edit)
        main_layout.addWidget(notes_container)

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container); button_layout.setSpacing(10)
        self.button_box = QDialogButtonBox()
        self.ok_button = QPushButton("SAVE CHANGES" if self.is_editing else "Save")
        self.cancel_button = QPushButton("Cancel")
        self.button_box.addButton(self.ok_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        button_layout.addStretch(); button_layout.addWidget(self.button_box)
        main_layout.addWidget(button_container)
        
        if not self.is_editing:
            button_container.hide()
        
        main_scroll.setWidget(main_widget)
        dialog_layout = QVBoxLayout(self); dialog_layout.setContentsMargins(0, 0, 0, 0); dialog_layout.addWidget(main_scroll)
    
    def _get_initial_data(self, annotation):
        if annotation and hasattr(annotation, 'comments') and annotation.comments:
            try:
                return json.loads(annotation.comments[0]["body"])
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to parse annotation: {e}")
                return None
        elif hasattr(self.parent(), "annotation_manager") and hasattr(self.parent().annotation_manager, "last_used_labels"):
            d = self.parent().annotation_manager.last_used_labels
            if any(v for k, v in d.items() if k != "special_notes" or v):
                return [
                    {"category": CAT_POSTURE, "selectedValue": d["posture"]},
                    {"category": CAT_HLB, "selectedValue": d["hlb"]},
                    {"category": CAT_PA, "selectedValue": d["pa_type"]},
                    {"category": CAT_BP, "selectedValue": d["behavioral_params"]},
                    {"category": CAT_ES, "selectedValue": d["exp_situation"]},
                    {"category": CAT_NOTES, "selectedValue": d.get("special_notes", "")}
                ]
        return None

    def _set_values_from_data(self, data):
        for w in self.all_selections.values(): w.blockSignals(True)
        data_map = {item["category"]: item["selectedValue"] for item in data}
        self.posture_selection.set_values([data_map.get(CAT_POSTURE)])
        self.hlb_selection.set_values(data_map.get(CAT_HLB))
        self.pa_selection.set_values([data_map.get(CAT_PA)])
        self.bp_selection.set_values(data_map.get(CAT_BP))
        self.es_selection.set_values([data_map.get(CAT_ES)])
        self.notes_edit.setText(data_map.get(CAT_NOTES, ""))
        for w in self.all_selections.values(): w.blockSignals(False)

    def accept(self):
        errors = self._get_validation_errors()
        if not errors:
            super().accept()
            return
        
        if self.disable_alerts_checkbox.isChecked():
            super().accept()
            return
        
        error_messages = []
        if CAT_POSTURE in errors:
            error_messages.append(f"Posture '{errors[CAT_POSTURE][0]}' is incompatible.")
        if CAT_HLB in errors:
            error_messages.append(f"HLB(s) {', '.join(errors[CAT_HLB])} are incompatible.")
        
        msg = f"There are incompatible selections for PA Type '{self.pa_selection.selected_values[0]}':\n\n" + "\n".join(f"- {e}" for e in error_messages) + "\n\nDo you want to save anyway?"
        
        reply = QMessageBox.question(self, "Confirm Save", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            super().accept()

    def get_all_selections(self):
        return { CAT_POSTURE: self.posture_selection.selected_values[0], CAT_HLB: self.hlb_selection.selected_values, CAT_PA: self.pa_selection.selected_values[0], CAT_BP: self.bp_selection.selected_values, CAT_ES: self.es_selection.selected_values[0], CAT_NOTES: self.notes_edit.text() }

    def _on_settings_change(self):
        self.settings.setValue(SETTINGS_DISABLE_ALERTS, self.disable_alerts_checkbox.isChecked())
        self._run_validation_check()

    def _handle_user_validation(self):
        if not self.disable_alerts_checkbox.isChecked():
            errors = self._get_validation_errors()
            if errors:
                error_messages = []
                if CAT_POSTURE in errors: error_messages.append(f"Posture '{errors[CAT_POSTURE][0]}' is incompatible with the selected PA Type.")
                if CAT_HLB in errors: error_messages.append(f"HLB(s) {', '.join(errors[CAT_HLB])} are incompatible with the selected PA Type.")
                msg = "⚠️ Incompatible selection detected:\n\n" + "\n".join(f"• {e}" for e in error_messages) + "\n\nYou can still save this annotation, but please verify the selection is correct."
                QMessageBox.warning(self, "Incompatible Selection", msg)
    
    def _update_filters(self):
        # Always show all options - no filtering
        self._run_validation_check()

    def _run_validation_check(self, is_initial_load=False):
        self._clear_all_invalid_styles()
        errors = self._get_validation_errors()
        if not errors: return
        
        self._apply_invalid_styles(errors)
        
        if is_initial_load and not self.disable_alerts_checkbox.isChecked():
            error_messages = []
            if CAT_POSTURE in errors: error_messages.append(f"Posture '{errors[CAT_POSTURE][0]}' is incompatible with the selected PA Type.")
            if CAT_HLB in errors: error_messages.append(f"HLB(s) {', '.join(errors[CAT_HLB])} are incompatible with the selected PA Type.")
            msg = "⚠️ The loaded annotation has incompatible values:\n\n" + "\n".join(f"• {e}" for e in error_messages) + "\n\nYou can still save this annotation, but please verify the selection is correct."
            QMessageBox.warning(self, "Incompatible Annotation", msg)
            
    def _get_validation_errors(self):
        errors = defaultdict(list)
        selected_pa = self.pa_selection.selected_values[0]
        selected_posture = self.posture_selection.selected_values[0]
        
        if selected_pa == self.pa_selection.unlabeled_text: return {}

        allowed_postures = self.mappings.get('PA_to_POS', {}).get(selected_pa)
        if (allowed_postures is not None and selected_posture not in allowed_postures and 
            selected_posture != self.posture_selection.unlabeled_text):
            errors[CAT_POSTURE].append(selected_posture)

        allowed_hlb = self.mappings.get('PA_to_HLB', {}).get(selected_pa)
        if allowed_hlb is not None:
            for hlb in self.hlb_selection.selected_values:
                if hlb != allowed_hlb and hlb != self.hlb_selection.unlabeled_text:
                    errors[CAT_HLB].append(hlb)
            
        return dict(errors)

    def _apply_invalid_styles(self, errors):
        if errors:
            self.pa_selection.set_invalid_style(True)
        if CAT_POSTURE in errors:
            self.posture_selection.set_invalid_style(True)
        if CAT_HLB in errors:
            invalid_hlbs = set(errors[CAT_HLB])
            for i in range(self.hlb_selection.tag_layout.count()):
                item = self.hlb_selection.tag_layout.itemAt(i)
                widget = item.widget() if item else None
                if isinstance(widget, TagWidget) and widget.label.text() in invalid_hlbs:
                    widget.set_invalid(True)

    def _clear_all_invalid_styles(self):
        for sel in self.all_selections.values():
            sel.set_invalid_style(False)
        if self.hlb_selection.tag_layout:
            for i in range(self.hlb_selection.tag_layout.count()):
                item = self.hlb_selection.tag_layout.itemAt(i)
                widget = item.widget() if item else None
                if isinstance(widget, TagWidget):
                    widget.set_invalid(False)

    def closeEvent(self, event):
        if not self.is_editing:
            self.accept()
        super().closeEvent(event)
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() >= Qt.Key.Key_1 and event.key() <= Qt.Key.Key_5: 
            self.selectCategoryByIndex(event.key() - Qt.Key.Key_1)
        super().keyPressEvent(event)
    
    def selectCategoryByIndex(self, index):
        category_combos = [self.posture_combo, self.hlb_combo, self.pa_combo, self.bp_combo, self.es_combo]
        if 0 <= index < len(category_combos):
            combo = category_combos[index]
            combo.focus_search()
    
    def load_mappings(self):
        try:
            path = resource_path('data/mapping/mapping.json')
            with open(path, 'r') as f: self.mappings = json.load(f)
            self.mappings['HLB_to_PA'] = defaultdict(list); [self.mappings['HLB_to_PA'][hlb].append(pa) for pa, hlb in self.mappings.get('PA_to_HLB', {}).items()]
            self.mappings['POS_to_PA'] = defaultdict(list); [[self.mappings['POS_to_PA'][pos].append(pa) for pos in postures] for pa, postures in self.mappings.get('PA_to_POS', {}).items()]
            return True
        except Exception as e: QMessageBox.critical(self, "Config Error", f"Could not load mapping.json:\n{e}"); return False
    
    def load_categories(self):
        try:
            path = resource_path('data/categories/categories.csv')
            with open(path, 'r') as f:
                categories = defaultdict(list); [categories[cat].append(val) for row in csv.DictReader(f) for cat, val in row.items() if val]
                self.full_categories = { CAT_POSTURE: ["Posture_Unlabeled"] + categories[CAT_POSTURE], CAT_HLB: ["HLB_Unlabeled"] + categories[CAT_HLB], CAT_PA: ["PA_Type_Unlabeled"] + categories[CAT_PA], CAT_BP: ["CP_Unlabeled"] + categories[CAT_BP], CAT_ES: ["ES_Unlabeled"] + categories[CAT_ES] }
            return True
        except Exception as e: QMessageBox.critical(self, "Config Error", f"Could not load categories.csv:\n{e}"); return False
    
    def _populate_combos(self):
        # Set items for all combos
        self.posture_combo.set_items(self.full_categories[CAT_POSTURE])
        self.hlb_combo.set_items(self.full_categories[CAT_HLB])
        self.pa_combo.set_items(self.full_categories[CAT_PA])
        self.bp_combo.set_items(self.full_categories[CAT_BP])
        self.es_combo.set_items(self.full_categories[CAT_ES])
        
        # Set unlabeled text on SelectionWidget instances
        self.posture_selection.set_unlabeled_text(self.full_categories[CAT_POSTURE][0])
        self.hlb_selection.set_unlabeled_text(self.full_categories[CAT_HLB][0])
        self.pa_selection.set_unlabeled_text(self.full_categories[CAT_PA][0])
        self.bp_selection.set_unlabeled_text(self.full_categories[CAT_BP][0])
        self.es_selection.set_unlabeled_text(self.full_categories[CAT_ES][0])
        
        # Also set unlabeled text on the MultiSelectComboBox instances
        self.hlb_combo.set_unlabeled_text(self.full_categories[CAT_HLB][0])
        self.bp_combo.set_unlabeled_text(self.full_categories[CAT_BP][0])
        
        # Connect signals for single-select combos
        self.posture_combo.itemSelected.connect(lambda text: self._on_combo_selection(self.posture_selection, text))
        self.pa_combo.itemSelected.connect(lambda text: self._on_combo_selection(self.pa_selection, text))
        self.es_combo.itemSelected.connect(lambda text: self._on_combo_selection(self.es_selection, text))
        
        # Connect signals for multi-select combos
        self.hlb_combo.selectionChanged.connect(lambda items: self._on_multi_selection(self.hlb_selection, items))
        self.bp_combo.selectionChanged.connect(lambda items: self._on_multi_selection(self.bp_selection, items))
    
    def _on_combo_selection(self, selection_widget, text):
        """Handle single selection from custom combo"""
        if text and text != selection_widget.unlabeled_text:
            selection_widget.selected_values = [text]
            selection_widget._update_ui()
            selection_widget.selectionChanged.emit()
            selection_widget.userMadeSelection.emit()
    
    def _on_multi_selection(self, selection_widget, items):
        if items and len(items) > 1 and selection_widget.unlabeled_text in items:
            items = [i for i in items if i != selection_widget.unlabeled_text]
        
        # If nothing selected, use unlabeled
        if not items:
            items = [selection_widget.unlabeled_text]
        
        # Update the selection widget's selected values
        selection_widget.selected_values = items
        
        # Rebuild tags
        if selection_widget.multi_select:
            # Clear existing tags
            while selection_widget.tag_layout.count() > 0:
                item = selection_widget.tag_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            
            # Add tags for non-unlabeled items
            for value in items:
                if value != selection_widget.unlabeled_text:
                    tag = TagWidget(value)
                    tag.removed.connect(lambda text, sw=selection_widget: self._on_tag_removed(sw, text))
                    selection_widget.tag_layout.addWidget(tag)
        
        # Update the active label
        selection_widget.update_active_label()
        
        # Emit signals
        selection_widget.selectionChanged.emit()
        selection_widget.userMadeSelection.emit()

    def _on_tag_removed(self, selection_widget, text):
        selection_widget.remove_tag(text)
        
        # Update the combo box to reflect the removal
        if hasattr(selection_widget.combo, 'set_selected'):
            remaining = [v for v in selection_widget.selected_values if v != text]
            if not remaining:
                remaining = [selection_widget.unlabeled_text]
            selection_widget.combo.set_selected(remaining)
    
    def _get_stylesheet(self):
        return """
            QWidget { 
                background-color: #1e1e1e; 
                color: #ffffff; 
                font-size: 13px; 
            }
            
            QLabel#headerLabel { 
                font-weight: bold; 
                color: #ffffff; 
                font-size: 14px; 
                padding: 8px 12px; 
                background-color: #2a2a2a;
                border-radius: 4px;
            }
            
            QLabel[category="true"] { 
                padding: 10px 14px; 
                background-color: #2a2a2a; 
                border-radius: 6px; 
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #3d3d3d;
            }
            
            QWidget#notesContainer { 
                background-color: #252525; 
                border-radius: 6px; 
                padding: 16px; 
                border: 1px solid #3d3d3d;
            }
            
            QLabel#notesSublabel { 
                color: #999999; 
                font-size: 11px; 
                padding: 2px 0; 
            }
            
            QCheckBox { 
                spacing: 8px; 
                color: #ffffff;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #3d3d3d;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border-color: #2b79ff;
                background-color: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background-color: #2b79ff;
                border-color: #2b79ff;
                image: url(none);
            }
            QCheckBox::indicator:checked:hover {
                background-color: #3d8aff;
                border-color: #3d8aff;
            }
            
            QComboBox { 
                background-color: #252525; 
                border: 2px solid #3d3d3d; 
                border-radius: 6px; 
                padding: 10px 14px;
                min-height: 20px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #4a4a4a;
                background-color: #2a2a2a;
            }
            QComboBox:focus {
                border-color: #2b79ff;
                background-color: #2a2a2a;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #3d3d3d;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #888888;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                selection-background-color: #2b79ff;
                color: #ffffff;
                padding: 4px;
            }
            
            QWidget[invalid="true"] > QComboBox { 
                border: 2px solid #e53935; 
            }
            
            QLineEdit { 
                padding: 10px 14px; 
                background-color: #252525; 
                border: 2px solid #3d3d3d; 
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:hover {
                border-color: #4a4a4a;
                background-color: #2a2a2a;
            }
            QLineEdit:focus {
                border-color: #2b79ff;
                background-color: #2a2a2a;
            }
            
            QPushButton { 
                padding: 12px 28px; 
                border-radius: 6px; 
                font-weight: bold; 
                border: none;
                font-size: 13px;
            }
            QPushButton[text="Save"], QPushButton[text="SAVE CHANGES"] { 
                background-color: #2b79ff; 
                color: white; 
            }
            QPushButton[text="Save"]:hover, QPushButton[text="SAVE CHANGES"]:hover { 
                background-color: #3d8aff; 
            }
            QPushButton[text="Save"]:pressed, QPushButton[text="SAVE CHANGES"]:pressed { 
                background-color: #1a5cbd; 
            }
            QPushButton[text="Cancel"] { 
                background-color: #3d3d3d; 
                color: white; 
            }
            QPushButton[text="Cancel"]:hover { 
                background-color: #4a4a4a; 
            }
            QPushButton[text="Cancel"]:pressed { 
                background-color: #2d2d2d; 
            }
            
            QLabel { 
                padding: 8px 12px;
                background-color: #252525;
                border-radius: 6px;
                border: 1px solid #3d3d3d;
            }
            
            QScrollArea {
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                background-color: #252525;
                padding: 4px;
            }
        """