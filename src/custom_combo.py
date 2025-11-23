from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                                     QListWidget, QListWidgetItem, QCheckBox, QLabel,
                                     QPushButton, QFrame, QComboBox, QCompleter)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSortFilterProxyModel
from PyQt6.QtGui import QFontMetrics, QStandardItemModel, QStandardItem


class SearchableComboBox(QComboBox):
    """Searchable combo box with QCompleter for single selection"""
    
    itemSelected = pyqtSignal(str) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure combo box
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        # Create filter model
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())
        
        # Create completer
        self.completer = QCompleter(self.pFilterModel, self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(self.completer)
        
        # Connect signals
        self.lineEdit().textEdited.connect(self.pFilterModel.setFilterFixedString)
        self.completer.activated.connect(self.on_completer_activated)
        
    def on_completer_activated(self, text):
        """Handle completer activation"""
        if text:
            index = self.findText(text)
            if index >= 0:
                self.setCurrentIndex(index)
                self.itemSelected.emit(text)
    
    def setModel(self, model):
        """Override setModel to update filter model"""
        super().setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)
    
    def setModelColumn(self, column):
        """Override setModelColumn"""
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super().setModelColumn(column)
    
    def set_items(self, items):
        """Set items in the combo box"""
        self.clear()
        if items:
            self.addItems(items)
    
    def get_selected(self):
        """Get currently selected item"""
        return self.currentText()
    
    def set_selected(self, item):
        """Set selected item"""
        if isinstance(item, str):
            index = self.findText(item)
            if index >= 0:
                self.setCurrentIndex(index)
    
    def focus_search(self):
        """Focus and select all text in line edit"""
        self.setFocus()
        self.lineEdit().selectAll()


class MultiSelectComboBox(QWidget):
    """Multi-select combo box with checkboxes"""
    
    selectionChanged = pyqtSignal(list)  # Emitted when selection changes
    
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.all_items = items or []
        self.selected_items = []
        self.dropdown_visible = False
        self.unlabeled_text = ""
        self._programmatic_close = False
        
        self.setStyleSheet(self._get_stylesheet())
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to search...")
        self.search_box.textChanged.connect(self._filter_items)
        self.search_box.installEventFilter(self)
        layout.addWidget(self.search_box)
        
        # Dropdown container
        self.dropdown = QFrame()
        self.dropdown.setFrameShape(QFrame.Shape.StyledPanel)
        self.dropdown.setObjectName("dropdown")
        self.dropdown.hide()
        self.dropdown.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dropdown.installEventFilter(self)
        
        dropdown_layout = QVBoxLayout(self.dropdown)
        dropdown_layout.setContentsMargins(0, 0, 0, 0)
        dropdown_layout.setSpacing(0)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("listWidget")
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.installEventFilter(self)
        dropdown_layout.addWidget(self.list_widget)
        
        layout.addWidget(self.dropdown)
        
        self._populate_list()
        
        self.installEventFilter(self)
        
    def _populate_list(self, filter_text=""):
        """Populate list with items, optionally filtered"""
        self.list_widget.clear()
        
        for item_text in self.all_items:
            if filter_text and filter_text.lower() not in item_text.lower():
                continue
                
            item = QListWidgetItem()
            self.list_widget.addItem(item)
            
            # Multi-select: use checkbox
            checkbox = QCheckBox(item_text)
            checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            checkbox.setChecked(item_text in self.selected_items)
            from functools import partial
            checkbox.stateChanged.connect(partial(self._on_checkbox_changed, item_text))
            self.list_widget.setItemWidget(item, checkbox)
            item.setSizeHint(checkbox.sizeHint())
        
        if self.dropdown_visible:
            self._update_dropdown_size()
    
    def _filter_items(self, text):
        """Filter items based on search text"""
        self._populate_list(text)
        if not self.dropdown_visible:
            self.show_dropdown()
    
    def _on_checkbox_changed(self, text, state):
        """Handle checkbox state change"""
        is_checked = (state == Qt.CheckState.Checked.value)
        
        if is_checked:
            if text not in self.selected_items:
                self.selected_items.append(text)
                
                if self.unlabeled_text and text != self.unlabeled_text:
                    if self.unlabeled_text in self.selected_items:
                        self.selected_items.remove(self.unlabeled_text)
                        self._update_checkbox_states()
        else:
            if text in self.selected_items:
                self.selected_items.remove(text)

        # self._update_search_box_display()
        
        self.selectionChanged.emit(self.selected_items.copy())
    
    def _update_dropdown_size(self):
        """Update dropdown size based on current item count"""
        item_count = min(self.list_widget.count(), 10)
        if item_count > 0:
            item_height = 35
            self.list_widget.setMinimumHeight(item_height * item_count)
            self.list_widget.setMaximumHeight(item_height * 10)
        else:
            self.list_widget.setMinimumHeight(30)
            self.list_widget.setMaximumHeight(300)
    
    def show_dropdown(self):
        """Show the dropdown list"""
        self.dropdown.show()
        self.dropdown_visible = True
        self._update_dropdown_size()
    
    def hide_dropdown(self):
        """Hide the dropdown list"""
        if not self.dropdown_visible:
            return
        self._programmatic_close = True
        self.dropdown.hide()
        self.dropdown_visible = False
        self._update_search_box_display()
        self._programmatic_close = False
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if self.dropdown_visible:
            if self.dropdown.geometry().contains(event.pos()):
                event.accept()
                return
        super().mousePressEvent(event)
    
    def set_items(self, items):
        """Set the list of items"""
        self.all_items = items
        if items and not self.unlabeled_text:
            self.unlabeled_text = items[0]
        self._populate_list()
    
    def set_unlabeled_text(self, text):
        self.unlabeled_text = text
    
    def get_selected(self):
        """Get currently selected items"""
        return self.selected_items.copy()
    
    def set_selected(self, items):
        """Set selected items"""
        if isinstance(items, str):
            items = [items]
        
        self.selected_items = items.copy() if items else []
        if self.unlabeled_text and len(self.selected_items) > 1:
            if self.unlabeled_text in self.selected_items:
                self.selected_items.remove(self.unlabeled_text)
        
        self._populate_list(self.search_box.text())
        self._update_search_box_display()
    
    def _update_checkbox_states(self):
        """Update checkbox states without triggering signals"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if isinstance(checkbox, QCheckBox):
                checkbox.blockSignals(True)
                checkbox.setChecked(checkbox.text() in self.selected_items)
                checkbox.blockSignals(False)
    
    def _update_search_box_display(self):
        """Update search box to show selected items summary"""
        if not self.selected_items or (len(self.selected_items) == 1 and self.selected_items[0] == self.unlabeled_text):
            self.search_box.setPlaceholderText("Type to search...")
            if not self.search_box.hasFocus():
                self.search_box.clear()
        else:
            # Show count of selected items
            valid_items = [item for item in self.selected_items if item != self.unlabeled_text]
            if valid_items:
                if len(valid_items) == 1:
                    display_text = valid_items[0]
                else:
                    display_text = f"{len(valid_items)} items selected"
                
                if not self.search_box.hasFocus():
                    self.search_box.setText(display_text)
                    self.search_box.setPlaceholderText(display_text)
    
    def clear_selection(self):
        """Clear all selections"""
        self.selected_items = []
        self.search_box.clear()
        self._populate_list()
    
    def focus_search(self):
        """Focus and select all text in search box"""
        self.search_box.setFocus()
        self.search_box.selectAll()
    
    def eventFilter(self, obj, event):
        """Handle events for the widget"""
        if not hasattr(self, 'search_box') or not hasattr(self, 'dropdown') or not hasattr(self, 'list_widget'):
            return super().eventFilter(obj, event)

        if obj == self.search_box:
            if event.type() == QEvent.Type.FocusIn:
                self.search_box.clear()
                if not self.dropdown_visible:
                    self.show_dropdown()
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self.hide_dropdown()
                    return True
                elif event.key() == Qt.Key.Key_Down:
                    if self.list_widget.count() > 0:
                        self.list_widget.setCurrentRow(0)
                    return True
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.hide_dropdown()
                    return True
        
        return super().eventFilter(obj, event)
    
    def _get_stylesheet(self):
        return """
            QLineEdit {
                padding: 10px 14px;
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                font-size: 13px;
                color: #ffffff;
            }
            QLineEdit:hover {
                border-color: #4a4a4a;
                background-color: #2a2a2a;
            }
            QLineEdit:focus {
                border-color: #2b79ff;
                background-color: #2a2a2a;
            }
            
            QFrame#dropdown {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 4px;
            }
            
            QListWidget#listWidget {
                background-color: #252525;
                border: none;
                outline: none;
                color: #ffffff;
            }
            QListWidget#listWidget::item {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QListWidget#listWidget::item:hover {
                background-color: #3d3d3d;
            }
            QListWidget#listWidget::item:selected {
                background-color: #2b79ff;
            }
            
            QCheckBox {
                spacing: 8px;
                color: #ffffff;
                font-size: 13px;
                padding: 8px 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
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
            }
        """
