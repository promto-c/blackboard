from PyQt5 import QtCore, QtGui, QtWidgets

from blackboard.utils.key_binder import KeyBinder

class HighlightDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that highlights text matches within items."""
    
    def __init__(self, parent=None, highlight_text: str = ''):
        """Initializes the HighlightDelegate with optional highlighting text.
        
        Args:
            parent: The parent widget.
            highlight_text: The text to highlight within the delegate's items.
        """
        super().__init__(parent)
        self.highlight_text = highlight_text

        app = QtWidgets.QApplication.instance()
        self.spacing = app.style().pixelMetric(QtWidgets.QStyle.PixelMetric.PM_FocusFrameHMargin)

    def paint(self, painter, option, index):
        """Paints the delegate's items, highlighting matches of the highlight text.
        
        Args:
            painter: The QPainter instance used for painting the item.
            option: The style options for the item.
            index: The index of the item in the model.
        """
        if self.highlight_text:
            # Custom painting code here
            text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            painter.save()

            # Highlight color
            painter.setBrush(QtGui.QColor(QtCore.Qt.GlobalColor.yellow).lighter(160))
            painter.setPen(QtCore.Qt.PenStyle.DashLine)

            # Find all occurrences of the highlight text
            start_pos = 0
            while True:
                start_pos = text.lower().find(self.highlight_text.lower(), start_pos)
                if start_pos == -1:
                    break
                end_pos = start_pos + len(self.highlight_text)

                # Calculate the bounding rect for the highlight text
                font_metrics = painter.fontMetrics()
                before_text_width = font_metrics.width(text[:start_pos])
                highlight_text_width = font_metrics.width(text[start_pos:end_pos])

                # Adjust highlight_rect to include padding
                highlight_rect = QtCore.QRect(option.rect.left() + before_text_width + self.spacing, option.rect.top(),
                                            highlight_text_width + self.spacing, option.rect.height())
        
                # Fill the background of the highlight text
                painter.drawRect(highlight_rect)
                start_pos += len(self.highlight_text)

            painter.restore()

        # Call the base class to do the default painting
        super().paint(painter, option, index)

class FilterLineEdit(QtWidgets.QLineEdit):
    """Line edit with navigation and selection capabilities for a QListView."""

    def __init__(self, list_view: QtWidgets.QListView, combo_box: QtWidgets.QComboBox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_view = list_view
        self.combo_box = combo_box

        self.delegate = HighlightDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)

        # self.__init_attributes()
        self.__init_signal_connections()

    def __init_signal_connections(self):
        """Initializes signal connections and key binding shortcuts.
        """
        # Signal connections
        self.textChanged.connect(self.updateHighlight)

        # Bind Shortcuts
        # --------------
        # Bind arrow keys for navigation
        KeyBinder.bind_key(self, QtGui.QKeySequence(QtCore.Qt.Key.Key_Up), self.navigate_up)
        KeyBinder.bind_key(self, QtGui.QKeySequence(QtCore.Qt.Key.Key_Down), self.navigate_down)
        # Bind Enter and Tab for selection
        KeyBinder.bind_key(self, QtGui.QKeySequence(QtCore.Qt.Key.Key_Return), self.apply_selection)
        KeyBinder.bind_key(self, QtGui.QKeySequence(QtCore.Qt.Key.Key_Enter), self.apply_selection)
        KeyBinder.bind_key(self, QtGui.QKeySequence(QtCore.Qt.Key.Key_Tab), self.apply_selection)

    def updateHighlight(self, text):
        """Updates the delegate with the current filter text.
        """
        self.delegate.highlight_text = text
        self.list_view.viewport().update()  # Refresh the view

    def navigate_up(self):
        """Navigates selection up in the list view.
        """
        currentIndex = self.list_view.currentIndex()
        rowCount = self.list_view.model().rowCount()
        if not currentIndex.isValid():
            # If no current selection, select the last item
            newIndex = self.list_view.model().index(rowCount - 1, 0)
        else:
            # Move selection up, wrap around if necessary
            newIndex = self.list_view.model().index(max(currentIndex.row() - 1, 0), 0)
        self.list_view.setCurrentIndex(newIndex)

    def navigate_down(self):
        """Navigates selection down in the list view.
        """
        currentIndex = self.list_view.currentIndex()
        rowCount = self.list_view.model().rowCount()
        if not currentIndex.isValid():
            # If no current selection, select the first item
            newIndex = self.list_view.model().index(0, 0)
        else:
            # Move selection down, wrap around if necessary
            newIndex = self.list_view.model().index((currentIndex.row() + 1) % rowCount, 0)
        self.list_view.setCurrentIndex(newIndex)

    def apply_selection(self):
        """Applies the current selection in the list view to the combo box.
        """
        text = self.text()
        model = self.list_view.model()

        # First, check if the current index is valid and apply that selection.
        current_index = self.list_view.currentIndex()
        if current_index.isValid():
            selected_text = model.data(current_index, QtCore.Qt.DisplayRole)
            idx = self.combo_box.findText(selected_text)
            self.combo_box.setCurrentIndex(idx)
        else:
            self.combo_box.setCurrentText(text)

        self.combo_box.hidePopup()

class CustomPopupComboBox(QtWidgets.QComboBox):
    """Custom combo box with a filterable popup list view.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize models and proxy models.
        """
        # Model to hold the original items
        self.source_model = QtCore.QStringListModel(["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"])
        # Proxy model for filtering
        self.proxy_model = QtCore.QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    def __init_ui(self):
        """Setup UI components.
        """
        self.setModel(self.source_model)
        # Custom popup widget
        self.popup_widget = QtWidgets.QWidget()
        self.popup_layout = QtWidgets.QVBoxLayout(self.popup_widget)
        self.popup_widget.setWindowFlags(QtCore.Qt.WindowType.Popup)
        # Line edit for filtering with list_view linked
        self.list_view = QtWidgets.QListView(self.popup_widget)
        self.filter_line_edit = FilterLineEdit(self.list_view, self, self.popup_widget)
        self.popup_layout.addWidget(self.filter_line_edit)
        self.popup_layout.setContentsMargins(0, 0, 0, 0)
        # List view to display filtered items
        self.list_view.setModel(self.proxy_model)
        self.popup_layout.addWidget(self.list_view)

    def __init_signal_connections(self):
        """Connect signals and slots.
        """
        self.filter_line_edit.textChanged.connect(self.apply_filter)
        self.list_view.clicked.connect(self.apply_selection)

    def showPopup(self):
        """Displays the custom popup widget.
        """
        # Show the custom popup widget
        popup_position = self.mapToGlobal(self.rect().topLeft())  # Corrected to use topLeft() of the rect
        self.popup_widget.setGeometry(popup_position.x(), 
                                    popup_position.y() + self.height(), 
                                    self.width(), 200)  # Adjust size as needed
        self.popup_widget.show()
        self.filter_line_edit.setFocus()  # Focus on the line edit when popup is shown

    def hidePopup(self):
        """Hides the custom popup widget.
        """
        self.popup_widget.hide()

    def apply_filter(self, text):
        """Applies a filter to the list view based on the entered text.
        """
        # Update the proxy model filter
        self.proxy_model.setFilterWildcard(f'*{text}*')

    def apply_selection(self, index):
        """Sets the combo box's current item based on the selection.
        """
        # Set the combo box current item and hide the popup
        text = self.proxy_model.data(index)
        idx = self.findText(text)
        self.setCurrentIndex(idx)
        self.hidePopup()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    combo = CustomPopupComboBox()
    combo.show()
    app.exec_()
