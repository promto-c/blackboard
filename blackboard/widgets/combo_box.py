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
    """Line edit with navigation and selection capabilities for a QTreeView."""

    def __init__(self, tree_view: QtWidgets.QTreeView, combo_box: QtWidgets.QComboBox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_view = tree_view
        self.combo_box = combo_box

        self.delegate = widgets.HighlightTextDelegate(self.tree_view)
        self.tree_view.setItemDelegate(self.delegate)

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
        self.tree_view.viewport().update()

    def navigate_up(self):
        """Navigates selection up in the tree view, taking hierarchy into account."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            previous_index = self.tree_view.indexAbove(current_index)
            if previous_index.isValid():
                self.tree_view.setCurrentIndex(previous_index)

    def navigate_down(self):
        """Navigates selection down in the tree view."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            next_index = self.tree_view.indexBelow(current_index)
            if next_index.isValid():
                self.tree_view.setCurrentIndex(next_index)

    def apply_selection(self):
        """Applies the current selection in the tree view to the combo box."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            selected_text = self.tree_view.model().data(current_index, QtCore.Qt.DisplayRole)
        else:
            selected_text = self.text()

        index = self.combo_box.findText(selected_text)
        self.combo_box.setCurrentIndex(index)
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
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy_model.sort(0, QtCore.Qt.AscendingOrder)

        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setFilterKeyColumn(0) 

        self.flat_proxy_model = bb.utils.FlatProxyModel(self.model(), self)
        self.flat_proxy_model.setSourceModel(self.model())
        self.flat_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.flat_proxy_model.sort(0, QtCore.Qt.AscendingOrder)

    def __init_ui(self):
        """Setup UI components.
        """
        line_edit = CustomLineEdit(self)
        self.setLineEdit(line_edit)
        line_edit.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        # Custom popup widget
        self.popup_widget = QtWidgets.QWidget()
        self.popup_layout = QtWidgets.QVBoxLayout(self.popup_widget)
        self.popup_layout.setContentsMargins(0, 0, 0, 0)
        self.popup_layout.setSpacing(0)
        self.popup_widget.setWindowFlags(QtCore.Qt.WindowType.Popup)
        # Tree view to display filtered items
        self.tree_view = QtWidgets.QTreeView(self.popup_widget)
        self.configure_tree_view()
        self.filter_line_edit = FilterLineEdit(self.tree_view, self, self.popup_widget)
        self.popup_layout.addWidget(self.filter_line_edit)
        self.tree_view.setModel(self.proxy_model)
        self.popup_layout.addWidget(self.tree_view)
    
    def configure_tree_view(self):
        """Configure the tree view to expand all items and hide the expand/collapse buttons."""
        self.tree_view.setHeaderHidden(True)
        self.tree_view.expandAll()
        self.tree_view.setItemsExpandable(False)
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setIndentation(12)

    def __init_signal_connections(self):
        """Connect signals and slots.
        """
        self.filter_line_edit.textChanged.connect(self.apply_filter)
        self.tree_view.clicked.connect(self.apply_selection)

    def setModel(self, model):
        """Sets the model for the combo box and updates the proxy model.
        """
        self.proxy_model.setSourceModel(model)
        self.flat_proxy_model.setSourceModel(model)
        self.tree_view.expandAll()

        super().setModel(self.flat_proxy_model)

    def showPopup(self):
        """Displays the custom popup widget and pre-selects the current item in a QTreeView."""
        self.popup_widget.show()
        self.filter_line_edit.clear()

        # Pre-select the current item in the tree view based on the current text in the combo box
        current_text = self.currentText()
        matching_index = self.find_matching_index(self.proxy_model, current_text)
        if matching_index.isValid():
            self.tree_view.setCurrentIndex(matching_index)
            self.tree_view.scrollTo(matching_index, QtWidgets.QAbstractItemView.PositionAtTop)
        else:
            self.tree_view.clearSelection()

        self.filter_line_edit.setFocus()
        popup_position = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        self.popup_widget.move(popup_position)

    def find_matching_index(self, model, text, parent=QtCore.QModelIndex()):
        """Recursively searches for an item that matches the text."""
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            if text == model.data(index, QtCore.Qt.DisplayRole):
                return index
            if model.hasChildren(index):
                found_index = self.find_matching_index(model, text, index)
                if found_index.isValid():
                    return found_index
        return QtCore.QModelIndex()

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
        self.tree_view.expandAll()
        # Find the first index that matches the filter and is visible
        first_index = self.find_first_filtered_index()

        if not first_index.isValid():
            return

        self.tree_view.setCurrentIndex(first_index)
        self.tree_view.scrollTo(first_index, QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible)

    def find_first_filtered_index(self):
        """Finds the first index in the proxy model that is visible and matches the filter."""
        for row in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(row, 0)
            if index.isValid():
                return index
        return QtCore.QModelIndex()

    def apply_selection(self, index):
        """Sets the combo box's current item based on the selection.
        """
        # Set the combo box current item and hide the popup
        text = self.proxy_model.data(index)
        index = self.findText(text)
        self.setCurrentIndex(index)
        self.hidePopup()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    combo = PopupComboBox()

    # Creating a QStandardItemModel
    model = QtGui.QStandardItemModel()

    # Defining parent nodes (fruit categories)
    citrus = QtGui.QStandardItem('Citrus Fruits')
    tropical = QtGui.QStandardItem('Tropical Fruits')
    berries = QtGui.QStandardItem('Berries')

    # Adding child nodes to citrus
    citrus.appendRow(QtGui.QStandardItem('Lemon'))
    citrus.appendRow(QtGui.QStandardItem('Orange'))
    citrus.appendRow(QtGui.QStandardItem('Lime'))
    citrus.appendRow(QtGui.QStandardItem('Tangerine'))

    # Adding child nodes to tropical
    tropical.appendRow(QtGui.QStandardItem('Mango'))
    tropical.appendRow(QtGui.QStandardItem('Papaya'))
    tropical.appendRow(QtGui.QStandardItem('Kiwi'))
    tropical.appendRow(QtGui.QStandardItem('Dragon Fruit'))

    # Adding child nodes to berries
    berries.appendRow(QtGui.QStandardItem('Strawberry'))
    berries.appendRow(QtGui.QStandardItem('Raspberry'))
    berries.appendRow(QtGui.QStandardItem('Blackberry'))

    # Adding parent nodes to the model
    model.appendRow(citrus)
    model.appendRow(tropical)
    model.appendRow(berries)

    combo.setModel(model)

    combo.show()
    app.exec_()
