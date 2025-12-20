from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                                     QListWidget, QListWidgetItem, QCheckBox, QLabel,
                                     QPushButton, QFrame, QComboBox, QCompleter, QAbstractItemView, QListView)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSortFilterProxyModel
from PyQt6.QtGui import QFontMetrics, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QComboBox, QAbstractItemView, QStyledItemDelegate
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPainter
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QRect

class SearchableComboBox(QComboBox):
    
    itemSelected = pyqtSignal(str) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        from PyQt6.QtWidgets import QAbstractItemView
        self.view().setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view().setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())
        
        self.completer = QCompleter(self.pFilterModel, self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(self.completer)
        
        self.lineEdit().textEdited.connect(self.pFilterModel.setFilterFixedString)

        self.completer.activated.connect(self.on_completer_activated)
        self.view().installEventFilter(self)
        self.view().viewport().installEventFilter(self)

        
    def on_completer_activated(self, text):
        if text:
            index = self.findText(text)
            if index >= 0:
                self.setCurrentIndex(index)
                self.itemSelected.emit(text)

    def eventFilter(self, obj, event):
        if obj == self.view().viewport():
            print("Event in viewport:", event.type())
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                index = self.view().indexAt(event.pos())
                self._on_item_selected_from_view(index.row())
                return True
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    index = self.view().currentIndex()
                    self._on_item_selected_from_view(index.row())
                    return True
        elif obj == self.view():
            print("Event in view:", event.type())
            if event.type() == QEvent.Type.MouseButtonPress:
                index = self.view().indexAt(event.pos())
                self._on_completer_popup_clicked(index)
                return True
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    index = self.view().currentIndex()
                    self._on_completer_popup_clicked(index)
                    return True
        return super().eventFilter(obj, event)
    
    def _on_completer_popup_clicked(self, index):
        """Handle clicks on the completer popup"""
        print("Completer popup clicked!", index)
        if index.isValid():
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if not text:
                try:
                    if index.model() == self.pFilterModel:
                        source_index = self.pFilterModel.mapToSource(index)
                        text = self.model().data(source_index, Qt.ItemDataRole.DisplayRole)
                except:
                    pass
            
            if text:
                print(f"Selected text: {text}")
                combo_index = self.findText(text, Qt.MatchFlag.MatchFixedString)
                if combo_index >= 0:
                    self.setCurrentIndex(combo_index)
                    self.itemSelected.emit(text)
                    self.hidePopup()

    def _on_item_selected_from_view(self, index):
        """Handle selection from dropdown view (not completer)"""
        if index >= 0:
            text = self.itemText(index)
            if text:
                self.itemSelected.emit(text)
                # set the text in line edit
                self.lineEdit().setText(text)
    
    def setModel(self, model):
        super().setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)
    
    def setModelColumn(self, column):
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super().setModelColumn(column)
    
    def set_items(self, items):
        self.clear()
        if items:
            self.addItems(items)
    
    def get_selected(self):
        return self.currentText()
    
    def set_selected(self, item):
        if isinstance(item, str):
            index = self.findText(item)
            if index >= 0:
                self.setCurrentIndex(index)
    
    def focus_search(self):
        self.setFocus()
        self.lineEdit().selectAll()
    
    def showPopup(self):
        super().showPopup()
        current_index = self.view().currentIndex()
        if current_index.isValid():
            self.view().setCurrentIndex(current_index)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clearFocus()
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if not self.view().isVisible():
                self.showPopup()
            super().keyPressEvent(event)
            return
        super().keyPressEvent(event)


class TickMarkDelegate(QStyledItemDelegate):
    
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        model = index.model()
        
        if isinstance(model, QSortFilterProxyModel):
            source_index = model.mapToSource(index)
            source_model = model.sourceModel()
            item = source_model.itemFromIndex(source_index)
        else:
            item = model.itemFromIndex(index) if hasattr(model, 'itemFromIndex') else None
        
        if item and item.data(Qt.ItemDataRole.UserRole) == "selected":
            painter.save()
            painter.setPen(Qt.GlobalColor.white)
            
            rect = option.rect
            tick_rect = QRect(rect.right() - 25, rect.top(), 20, rect.height())
            painter.drawText(tick_rect, Qt.AlignmentFlag.AlignCenter, "✓")
            
            painter.restore()


class MultiSelectComboBox(SearchableComboBox):
    
    selectionChanged = pyqtSignal(list)
    
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        
        self.unlabeled_text = ""
        self._selected_items = set()
        self._is_popup_open = False
        
        self.view().setItemDelegate(TickMarkDelegate(self))
        
        self.completer.activated.disconnect(self.on_completer_activated)
        self.completer.activated.connect(self._on_item_activated)
        
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.view().installEventFilter(self)
        
        self.view().viewport().installEventFilter(self)
        
        self.lineEdit().setPlaceholderText("Type to search or click to select...")
        
        if items:
            self.set_items(items)
        
        self.view().setStyleSheet("""
            QListView {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                selection-background-color: #2b79ff;
                color: #ffffff;
                padding: 4px;
                outline: none;
            }
            QListView::item {
                padding: 6px;
                padding-right: 30px;
                border: none;
            }
            QListView::item:hover {
                background-color: #3d3d3d;
            }
            QListView::item:selected {
                background-color: #2b79ff;
                color: #ffffff;
            }
        """)
    
    def eventFilter(self, obj, event):
        if obj == self.view().viewport():
            if event.type() == QEvent.Type.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                if index.isValid():
                    self._toggle_item_at_index(index)
                    return True
        elif obj == self.view():
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    index = self.view().currentIndex()
                    if index.isValid():
                        self._toggle_item_at_index(index)
                        return True
        return super().eventFilter(obj, event)
    
    def _on_item_activated(self, text):
        if text:
            search_text = self.lineEdit().text()
            
            for i in range(self.model().rowCount()):
                item = self.model().item(i)
                if item and item.text() == text:
                    index = self.model().index(i, 0)
                    self._toggle_item_at_index(index)
                    break
            
            self.lineEdit().blockSignals(True)
            self.lineEdit().setText(search_text)
            self.lineEdit().blockSignals(False)
            if not self.view().isVisible():
                self.showPopup()
            self.lineEdit().setFocus()
    
    def _toggle_item_at_index(self, index):
        if not index.isValid():
            return
        
        item = self.model().itemFromIndex(index)
        if not item:
            return
        
        item_text = item.text()
        
        if item_text in self._selected_items:
            self._selected_items.discard(item_text)
            item.setData(None, Qt.ItemDataRole.UserRole)
        else:
            if item_text != self.unlabeled_text:
                self._selected_items.discard(self.unlabeled_text)
                for i in range(self.model().rowCount()):
                    unlabeled_item = self.model().item(i)
                    if unlabeled_item and unlabeled_item.text() == self.unlabeled_text:
                        unlabeled_item.setData(None, Qt.ItemDataRole.UserRole)
                        break
            
            self._selected_items.add(item_text)
            item.setData("selected", Qt.ItemDataRole.UserRole)
        
        if not self._selected_items:
            self._selected_items.add(self.unlabeled_text)
            for i in range(self.model().rowCount()):
                unlabeled_item = self.model().item(i)
                if unlabeled_item and unlabeled_item.text() == self.unlabeled_text:
                    unlabeled_item.setData("selected", Qt.ItemDataRole.UserRole)
                    break
        
        self.view().viewport().update()
        
        self.selectionChanged.emit(list(self._selected_items))
    
    def _update_display_text(self):
        pass
    
    def _get_display_text(self):
        return ""
    
    def showPopup(self):
        self._is_popup_open = True
        
        current_text = self.lineEdit().text()
        if not current_text.strip():
            self.lineEdit().blockSignals(True)
            self.lineEdit().clear()
            self.lineEdit().blockSignals(False)
            
            self.pFilterModel.setFilterFixedString("")
        
        super().showPopup()
        
        self.lineEdit().setFocus()
    
    def hidePopup(self):
        self._is_popup_open = False
        super().hidePopup()
        self._update_display_text()
    
    def keyPressEvent(self, event):
        print("Key Pressed in MultiSelectComboBox:", event.key(), "Popup Open:", self._is_popup_open)
        if event.key() == Qt.Key.Key_Escape:
            self.hidePopup()
            self.clearFocus()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Down:
            if not self.view().isVisible():
                self.showPopup()
                event.accept()
                return
        elif event.key() == Qt.Key.Key_Up:
            if not self.view().isVisible():
                self.showPopup()
                event.accept()
                return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            print("Enter key pressed in MultiSelectComboBox")
            if self._is_popup_open:
                print("Popup is open, toggling item")
            elif self.view().isVisible():
                search_text = self.lineEdit().text()
                
                current_index = self.view().currentIndex()
                if current_index.isValid():
                    source_index = self.pFilterModel.mapToSource(current_index)
                    self._toggle_item_at_index(source_index)
                    
                    self.lineEdit().blockSignals(True)
                    self.lineEdit().setText(search_text)
                    self.lineEdit().blockSignals(False)
                    
                    self.lineEdit().setFocus()
                    
                    event.accept()
                    return
        
        super().keyPressEvent(event)
    
    def set_items(self, items):
        self._all_items = items
        
        self.clear()
        model = QStandardItemModel()
        
        for item_text in items:
            item = QStandardItem()
            item.setText(item_text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            if item_text in self._selected_items:
                item.setData("selected", Qt.ItemDataRole.UserRole)
            
            model.appendRow(item)
        
        self.setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)
        
        if items and not self.unlabeled_text:
            self.unlabeled_text = items[0]
        
        self._update_display_text()
    
    def set_unlabeled_text(self, text):
        self.unlabeled_text = text
    
    def get_selected(self):
        return list(self._selected_items)
    
    def set_selected(self, items):
        if isinstance(items, str):
            items = [items]
        
        if not items:
            items = []
        
        items_list = list(items)
        if len(items_list) > 1 and self.unlabeled_text in items_list:
            items_list.remove(self.unlabeled_text)
        
        if not items_list:
            items_list = [self.unlabeled_text]
        
        self._selected_items = set(items_list)
        
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item:
                if item.text() in self._selected_items:
                    item.setData("selected", Qt.ItemDataRole.UserRole)
                else:
                    item.setData(None, Qt.ItemDataRole.UserRole)
        
        if self.view().isVisible():
            self.view().viewport().update()
        
        self._update_display_text()
        
        self.selectionChanged.emit(list(self._selected_items))
    
    def focus_search(self):
        self.setFocus()
        self.lineEdit().clear()
        self.lineEdit().setFocus()
