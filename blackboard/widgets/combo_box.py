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
    """Line edit with navigation and selection capabilities for a QTreeView.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, tree_view: QtWidgets.QTreeView, combo_box: QtWidgets.QComboBox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_view = tree_view
        self.combo_box = combo_box

        self.delegate = widgets.HighlightTextDelegate(self.tree_view)
        self.tree_view.setItemDelegate(self.delegate)

        self.__init_signal_connections()

    def __init_signal_connections(self):
        """Initialize signal connections and key binding shortcuts.
        """
        # Signal connections
        self.textChanged.connect(self.set_highlight_text)

        # Bind Shortcuts
        # --------------
        # Bind arrow keys for navigation
        bb.utils.KeyBinder.bind_key("Up", self, self.navigate_up)
        bb.utils.KeyBinder.bind_key("Down", self, self.navigate_down)
        # Bind Enter and Tab for selection
        bb.utils.KeyBinder.bind_key("Return", self, self.apply_selection)
        bb.utils.KeyBinder.bind_key("Enter", self, self.apply_selection)
        bb.utils.KeyBinder.bind_key("Tab", self, self.apply_selection)

    # Public Methods
    # --------------
    def set_highlight_text(self, text: str):
        """Update the delegate with the current filter text.
        """
        self.delegate.set_highlight_text(text)
        self.tree_view.viewport().update()

    def navigate_up(self):
        """Navigate selection up in the tree view, taking hierarchy into account.
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

    def apply_selection(self):
        """Apply the current selection in the tree view to the combo box.
        """
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            selected_text = self.tree_view.model().data(current_index, QtCore.Qt.DisplayRole)
        else:
            selected_text = self.text()

        index = self.combo_box.findText(selected_text)
        self.combo_box.setCurrentIndex(index)
        self.combo_box.hidePopup()

class StaticLineEdit(QtWidgets.QLineEdit):

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
        self.tree_view = widgets.MomentumScrollTreeView(self.popup_widget)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.expandAll()
        self.tree_view.setIndentation(12)
        self.tree_view.setModel(self.proxy_model)

        self.filter_line_edit = FilterLineEdit(self.tree_view, self, self.popup_widget)

        # Add Widgets to Layouts
        # ----------------------
        self.popup_layout.addWidget(self.filter_line_edit)
        self.popup_layout.addWidget(self.tree_view)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.filter_line_edit.textChanged.connect(self.apply_filter)
        self.tree_view.clicked.connect(self.apply_selection)

        self.customContextMenuRequested.connect(self._show_context_menu)
        self.lineEdit().customContextMenuRequested.connect(self._show_context_menu)

    # Public Methods
    # --------------
    def apply_selection(self, index):
        """Set the combo box's current item based on the selection.
        """
        # Set the combo box current item and hide the popup
        text = self.proxy_model.data(index)
        self.setCurrentText(text)
        self.hidePopup()

    def copy_current_text(self):
        """Copy the current text in the line edit to the clipboard.
        """
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.currentText())

    def find_matching_index(self, model, text, parent=QtCore.QModelIndex()):
        """Recursively search for an item that matches the text.
        """
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            if text == model.data(index, QtCore.Qt.DisplayRole):
                return index
            if model.hasChildren(index):
                found_index = self.find_matching_index(model, text, index)
                if found_index.isValid():
                    return found_index
        return QtCore.QModelIndex()

    def apply_filter(self, text):
        """Apply a filter to the list view based on the entered text.
        """
        # Update the proxy model filter
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
    def _show_context_menu(self, position):
        """Show the custom context menu.
        """
        context_menu = QtWidgets.QMenu(self)
        copy_action = context_menu.addAction("Copy")
        copy_action.triggered.connect(self.copy_current_text)
        context_menu.exec(self.mapToGlobal(position))

    def _find_first_filtered_index(self):
        """Find the first index in the proxy model that is visible and matches the filter.
        """
        for row in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(row, 0)
            if index.isValid():
                return index
        return QtCore.QModelIndex()

    # Overridden Methods
    # ------------------
    def setModel(self, model):
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
