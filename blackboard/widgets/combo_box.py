# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets

# Local Imports
# -------------
from blackboard.utils import KeyBinder, FlatProxyModel
from blackboard.widgets import MomentumScrollTreeView, HighlightTextDelegate


# Class Definitions
# -----------------
class StaticLineEdit(QtWidgets.QLineEdit):
    """Read-only line edit that triggers the combo box popup on click.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QComboBox):
        super().__init__(
            parent,
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter,
            focusPolicy=QtCore.Qt.FocusPolicy.NoFocus,
            contextMenuPolicy=QtCore.Qt.ContextMenuPolicy.CustomContextMenu,
            readOnly=True,
        )

        # Keep a reference to the combo box
        self._combo_box = parent

    # Overridden Methods
    # ------------------
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press event to show the combo box popup.
        """
        if event.button() == QtCore.Qt.LeftButton:
            self._combo_box.showPopup()
        else:
            super().mousePressEvent(event)

class PopupComboBox(QtWidgets.QComboBox):
    """Custom combo box with a filterable popup tree view.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(
            parent, 
            contextMenuPolicy=QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._filter_text = ''

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Widgets
        # --------------
        line_edit = StaticLineEdit(self)
        self.setLineEdit(line_edit)

        # Popup widget
        self.popup_widget = QtWidgets.QWidget()
        self.popup_layout = QtWidgets.QVBoxLayout(self.popup_widget)
        self.popup_layout.setContentsMargins(0, 0, 0, 0)
        self.popup_layout.setSpacing(0)
        self.popup_widget.setWindowFlags(QtCore.Qt.WindowType.Popup)

        # Tree view to display filtered items
        self.filter_line_edit = QtWidgets.QLineEdit(self)
        self.tree_view = MomentumScrollTreeView(
            self.popup_widget, headerHidden=True, indentation=12
        )
        self.proxy_model = QtCore.QSortFilterProxyModel(
            self, filterCaseSensitivity=QtCore.Qt.CaseInsensitive,
            recursiveFilteringEnabled=True, filterKeyColumn=0
        )
        self.proxy_model.sort(0, QtCore.Qt.AscendingOrder)
        self.flat_proxy_model = FlatProxyModel(parent=self)
        self.flat_proxy_model.sort(0, QtCore.Qt.AscendingOrder)
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.expandAll()

        self.delegate = HighlightTextDelegate(self.tree_view)
        self.tree_view.setItemDelegate(self.delegate)

        # Add Widgets to Layouts
        # ----------------------
        self.popup_layout.addWidget(self.filter_line_edit)
        self.popup_layout.addWidget(self.tree_view)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.filter_line_edit.textChanged.connect(self.apply_filter)
        self.filter_line_edit.textChanged.connect(self.set_highlight_text)
        self.tree_view.clicked.connect(self.apply_selection)

        # Bind Shortcuts
        # --------------
        # Bind arrow keys for navigation
        KeyBinder.bind_key("Up", self.filter_line_edit, self.navigate_up)
        KeyBinder.bind_key("Down", self.filter_line_edit, self.navigate_down)
        # Bind Enter and Tab for selection
        KeyBinder.bind_key("Return", self.filter_line_edit, self.apply_selection)
        KeyBinder.bind_key("Enter", self.filter_line_edit, self.apply_selection)
        KeyBinder.bind_key("Tab", self.filter_line_edit, self.apply_selection)

    # Public Methods
    # --------------
    def set_highlight_text(self, text: str):
        """Update the delegate with the current filter text.
        """
        self.delegate.set_highlight_text(text)
        self.tree_view.viewport().update()

    def navigate_up(self):
        """Navigate selection up in the tree view.
        """
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return

        previous_index = self.tree_view.indexAbove(current_index)
        if not previous_index.isValid():
            return

        self.tree_view.setCurrentIndex(previous_index)

    def navigate_down(self):
        """Navigate selection down in the tree view.
        """
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return

        next_index = self.tree_view.indexBelow(current_index)
        if not next_index.isValid():
            return

        self.tree_view.setCurrentIndex(next_index)

    def apply_selection(self, index=None):
        """Set the combo box's current item based on the selection.
        """
        # Set the combo box current item and hide the popup
        index = index or self.tree_view.currentIndex()
        text = self.proxy_model.data(index)
        self.addItem(text)
        self.setCurrentText(text)
        self.hidePopup()

    def copy_current_text(self):
        """Copy the current text in the line edit to the clipboard.
        """
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.currentText())

    def find_matching_index(self, model: QtCore.QAbstractItemModel, text: str, 
                            parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """Recursively search for an item that matches the text.
        """
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            if model.data(index, QtCore.Qt.DisplayRole) == text:
                return index
            if model.hasChildren(index):
                found_index = self.find_matching_index(model, text, index)
                if found_index.isValid():
                    return found_index
        return QtCore.QModelIndex()

    def apply_filter(self, text: str):
        """Apply a filter to the list view based on the entered text.
        """
        # Update the proxy model filter
        self._filter_text = text
        self.proxy_model.setFilterWildcard(f'*{text}*')
        self.tree_view.expandAll()
        # Find the first index that matches the filter and is visible
        first_index = self._find_first_filtered_index()

        if not first_index.isValid():
            return

        self.tree_view.setCurrentIndex(first_index)
        self.tree_view.scrollTo(first_index, QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible)

    # Private Methods
    # ---------------
    def _show_context_menu(self, position: QtCore.QPoint):
        """Show the custom context menu.
        """
        context_menu = QtWidgets.QMenu(self)
        copy_action = context_menu.addAction("Copy")
        copy_action.triggered.connect(self.copy_current_text)
        context_menu.exec(self.mapToGlobal(position))

    def _find_first_filtered_index(self, parent=QtCore.QModelIndex()) -> QtCore.QModelIndex:
        """Recursively find the first visible index in the proxy model that matches the filter.
        """
        for row in range(self.proxy_model.rowCount(parent)):
            index = self.proxy_model.index(row, 0, parent)
            if not index.isValid():
                continue

            # Check if the current index's data matches the filter text
            item_text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            if item_text and self._filter_text in item_text.lower():
                return index

            # If the current index has children, search recursively
            if self.proxy_model.hasChildren(index):
                found = self._find_first_filtered_index(index)
                if found.isValid():
                    return found

        return QtCore.QModelIndex()

    # Overridden Methods
    # ------------------
    def setModel(self, model: QtCore.QAbstractItemModel):
        """Set the model for the combo box and update the proxy model.
        """
        self.proxy_model.setSourceModel(model)
        self.flat_proxy_model.setSourceModel(model)
        self.tree_view.expandAll()

        super().setModel(self.flat_proxy_model)

    def showPopup(self):
        """Display the custom popup widget and pre-select the current item in a QTreeView.
        """
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

    def hidePopup(self):
        """Hide the custom popup widget.
        """
        try:
            self.popup_widget.hide()
        except RuntimeError:
            pass


# Example Usage
# -------------
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
