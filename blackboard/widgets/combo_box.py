# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets


# Class Definitions
# -----------------
class FilterLineEdit(QtWidgets.QLineEdit):
    """Line edit with navigation and selection capabilities for a QListView."""

    def __init__(self, list_view: QtWidgets.QListView, combo_box: QtWidgets.QComboBox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_view = list_view
        self.combo_box = combo_box

        self.delegate = widgets.HighlightTextDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)

        self.__init_signal_connections()

    def __init_signal_connections(self):
        """Initializes signal connections and key binding shortcuts.
        """
        # Signal connections
        self.textChanged.connect(self.set_highlight_text)

        # Bind Shortcuts
        # --------------
        # Bind arrow keys for navigation using string representations
        bb.utils.KeyBinder.bind_key("Up", self, self.navigate_up)
        bb.utils.KeyBinder.bind_key("Down", self, self.navigate_down)
        # Bind Enter and Tab for selection using string representations
        bb.utils.KeyBinder.bind_key("Return", self, self.apply_selection)
        bb.utils.KeyBinder.bind_key("Enter", self, self.apply_selection)
        bb.utils.KeyBinder.bind_key("Tab", self, self.apply_selection)

    def set_highlight_text(self, text: str):
        """Updates the delegate with the current filter text.
        """
        self.delegate.set_highlight_text(text)
        self.list_view.viewport().update()  # Refresh the view

    def navigate_up(self):
        """Navigates selection up in the list view, looping to the last item if the current item is the first.
        """
        current_index = self.list_view.currentIndex()
        row_count = self.list_view.model().rowCount()
        
        if not current_index.isValid() or current_index.row() == 0:
            # If no current selection or the first item is selected,
            # select the last item to loop back
            new_index = self.list_view.model().index(row_count - 1, 0)
        else:
            # Otherwise, move selection up
            new_index = self.list_view.model().index(current_index.row() - 1, 0)
        
        self.list_view.setCurrentIndex(new_index)

    def navigate_down(self):
        """Navigates selection down in the list view.
        """
        current_index = self.list_view.currentIndex()
        row_count = self.list_view.model().rowCount()

        if not current_index.isValid():
            # If no current selection, select the first item
            new_index = self.list_view.model().index(0, 0)
        else:
            # Move selection down, wrap around if necessary
            new_index = self.list_view.model().index((current_index.row() + 1) % row_count, 0)

        self.list_view.setCurrentIndex(new_index)

    def apply_selection(self):
        """Applies the current selection in the list view to the combo box.
        """
        # First, check if the current index is valid and apply that selection.
        current_index = self.list_view.currentIndex()
        if current_index.isValid():
            selected_text = self.list_view.model().data(current_index, QtCore.Qt.DisplayRole)
        else:
            selected_text = self.text()

        self.combo_box.setCurrentText(selected_text)
        self.combo_box.hidePopup()

class CustomLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_box = parent  # Keep a reference to the combo box
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if self.combo_box is not None:
            self.combo_box.showPopup()
        super().mousePressEvent(event)

class PopupComboBox(QtWidgets.QComboBox):
    """Custom combo box with a filterable popup list view.
    """
    POPUP_HEIGHT = 200

    def __init__(self, parent=None):
        super().__init__(parent)

        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize models and proxy models.
        """
        # Proxy model for filtering
        self.proxy_model = QtCore.QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model())
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    def __init_ui(self):
        """Setup UI components.
        """
        line_edit = CustomLineEdit(self)
        self.setLineEdit(line_edit)
        # Custom popup widget
        self.popup_widget = QtWidgets.QWidget()
        self.popup_layout = QtWidgets.QVBoxLayout(self.popup_widget)
        self.popup_layout.setContentsMargins(0, 0, 0, 0)
        self.popup_layout.setSpacing(0)
        self.popup_widget.setWindowFlags(QtCore.Qt.WindowType.Popup)
        # Line edit for filtering with list_view linked
        self.list_view = QtWidgets.QListView(self.popup_widget)
        self.filter_line_edit = FilterLineEdit(self.list_view, self, self.popup_widget)
        self.popup_layout.addWidget(self.filter_line_edit)
        # List view to display filtered items
        self.list_view.setModel(self.proxy_model)
        self.popup_layout.addWidget(self.list_view)

    def __init_signal_connections(self):
        """Connect signals and slots.
        """
        self.filter_line_edit.textChanged.connect(self.apply_filter)
        self.list_view.clicked.connect(self.apply_selection)

    def showPopup(self):
        """Displays the custom popup widget and clears the filter line edit.
        """
        self.popup_widget.show()
        self.filter_line_edit.clear()  # Clear the text to be ready for new input
        self.list_view.selectionModel().clearSelection()
        self.filter_line_edit.setFocus()  # Focus on the line edit when popup is shown
        popup_position = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        self.popup_widget.move(popup_position)
        
    def hidePopup(self):
        """Hides the custom popup widget.
        """
        try:
            self.popup_widget.hide()
        except RuntimeError:
            pass

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
        self.setCurrentText(text)
        self.hidePopup()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    combo = PopupComboBox()

    items = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
    combo.addItems(items)

    combo.show()
    app.exec_()
