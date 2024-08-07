# Type Checking Imports
# ---------------------
from typing import Optional

# Standard Library Imports
# ------------------------
import fnmatch

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets


# Class Definitions
# -----------------
class MatchCountButton(QtWidgets.QPushButton):
    """A custom QPushButton that changes its appearance on mouse hover and displays match counts.

    This button is designed to display the number of matches in a search operation.
    When the mouse hovers over it, the button provides a visual indication that clicking it
    will clear the search results.

    Attributes:
        _current_label (str): Stores the current label text of the button.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """Initialize the MatchCountButton with a parent widget, sets properties, and tooltip.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget of the button. Defaults to None.
        """
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._current_label = str()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Set up properties
        self.setProperty('widget-style', 'action-clear')
        self.setFixedHeight(16)
        # Setting a default tooltip
        self.setToolTip("Click to clear search")

    # Public Methods
    # --------------
    def set_match_count(self, total_matches: int):
        """Set the visibility and text of the button based on the total match count.

        Args:
            total_matches (int): The number of matches to display.
        """
        self.setVisible(bool(total_matches))
        self.setText(str(total_matches))

    # Overridden Methods
    # ------------------
    def enterEvent(self, event: QtCore.QEvent):
        """Handle mouse entry events, changing the icon and cursor.

        Args:
            event (QtCore.QEvent): The mouse enter event.
        """
        super().enterEvent(event)
        self._current_label = self.text()
        self.setIcon(TablerQIcon.x)
        self.setText('')
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

    def leaveEvent(self, event: QtCore.QEvent):
        """Handle mouse leave events, resetting the icon and cursor.

        Args:
            event (QtCore.QEvent): The mouse leave event.
        """
        super().leaveEvent(event)
        self.setIcon(QtGui.QIcon())
        self.setText(self._current_label)
        self.unsetCursor()

class SimpleSearchEdit(QtWidgets.QLineEdit):
    """A custom combo box widget tailored for simplified search functionality within a 
    groupable tree widget. It supports keyword search, highlighting matching items, 
    and displaying the total count of matches.

    Attributes:
        tree_widget (widgets.GroupableTreeWidget): The tree widget where search will be performed.
        _is_active (bool): Indicates whether the search filter is currently applied.
        _all_match_items (set): A set of items that match the current search criteria.
        skip_columns (set): A set of column indices to skip during the search.
    """

    FIXED_STRING_MATCH_FLAGS = QtCore.Qt.MatchFlag.MatchRecursive | QtCore.Qt.MatchFlag.MatchFixedString
    CONTAINS_MATCH_FLAGS = QtCore.Qt.MatchFlag.MatchRecursive | QtCore.Qt.MatchFlag.MatchContains
    WILDCARD_MATCH_FLAGS = QtCore.Qt.MatchFlag.MatchRecursive | QtCore.Qt.MatchFlag.MatchWildcard

    activated = QtCore.Signal()

    # Initialization and Setup
    # ------------------------
    def __init__(self, tree_widget: 'widgets.GroupableTreeWidget', parent: QtWidgets.QWidget = None):
        """Initialize the SimpleSearchEdit with a reference to the tree widget and sets up
        the UI components and signal connections.

        Args:
            tree_widget (widgets.GroupableTreeWidget): The tree widget to be searched.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        # Initialize the super class
        super().__init__(parent)

        # Store the arguments
        self.tree_widget = tree_widget

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        # Attributes
        # ----------
        self.tabler_icon = TablerQIcon(opacity=0.6)
        self.skip_columns = set()

        # Private Attributes
        # ------------------
        self._all_match_items = set()
        self._is_active = False
        self._is_searching = False

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setProperty('widget-style', 'round')
        self.setProperty('has-placeholder', True)
        self.setPlaceholderText('Type to Search')
        self.setFixedHeight(24)

        # Create the search action
        self.search_action = self.addAction(self.tabler_icon.search, QtWidgets.QLineEdit.ActionPosition.LeadingPosition)

        # Create the clear action
        self.__init_match_count_action()
        self.update_style()

    def __init_match_count_action(self):
        """Initialize the match count action and adds it to the line edit."""
        # Create and add the label for showing the total match count
        self.match_count_button = MatchCountButton(self)

        # Initialize a QWidgetAction to hold the match count button and set it as the default widget
        self.match_count_action = QtWidgets.QWidgetAction(self)
        self.match_count_action.setDefaultWidget(self.match_count_button)

        # Add the match count action to the line edit, positioned at the trailing end
        self.addAction(self.match_count_action, QtWidgets.QLineEdit.ActionPosition.TrailingPosition)

        # Initially hide the match count button
        self.match_count_button.setVisible(False)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.textChanged.connect(self.set_inactive)
        self.textChanged.connect(self._highlight_search)
        self.textChanged.connect(self.update_style)
        self.match_count_button.clicked.connect(self.clear)
        self.tree_widget.item_added.connect(self._filter_new_item)
        self.search_action.triggered.connect(self.set_active)

        bb.utils.KeyBinder.bind_key('Enter', self, self.set_active)
        bb.utils.KeyBinder.bind_key('Return', self, self.set_active)
        bb.utils.KeyBinder.bind_key('Escape', self, self.clear)

    # Public Methods
    # --------------
    def set_text_as_selection(self):
        """Set the text of the search edit to the selected items' text from the tree widget.
        """
        keywords = {f'"{index.data()}"' for index in self.tree_widget.selectedIndexes()}
        self.setText('|'.join(keywords))
        self.setFocus()

    def set_active(self):
        """Activate the search functionality.
        """
        self._is_searching = False
        if not self._all_match_items and not self.tree_widget.has_more_items_to_fetch:
            return

        self._set_property_active(True)
        self._apply_search()
        self.activated.emit()

        if self.tree_widget.has_more_items_to_fetch:
            self._is_searching = True
            self.tree_widget.fetch_all()

    def set_inactive(self):
        """Deactivate the search functionality.
        """
        if not self._is_active:
            return

        self._set_property_active(False)
        self._reset_search()

    def update(self):
        """Update the search and highlights matching items.
        """
        self._highlight_search()

        if self._is_active:
            self._apply_search()

    def update_style(self):
        """Update the button's style based on its state.
        """
        self.style().unpolish(self)
        self.style().polish(self)

    # Class Properties
    # ----------------
    @property
    def matched_items(self):
        return self._all_match_items

    @property
    def is_active(self):
        return self._is_active

    # Private Methods
    # ---------------
    def _filter_new_item(self, tree_item: QtWidgets.QTreeWidgetItem):
        """Filter a new item to see if it matches the search filter.

        Args:
            tree_item (QtWidgets.QTreeWidgetItem): The item that was added to the tree widget.
        """
        if not self._is_searching:
            return

        keyword = self.text().strip()
        if not keyword:
            return

        tree_item.setHidden(True)

        if self._item_matches_filter(tree_item):
            self._all_match_items.add(tree_item)
            tree_item.setHidden(False)
            self._update_total_matches()

    def _item_matches_filter(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """Check if an item matches the search filter.

        Args:
            item (QtWidgets.QTreeWidgetItem): The item to check.

        Returns:
            bool: True if the item matches the filter, False otherwise.
        """
        for column_index in range(self.tree_widget.columnCount()):
            if column_index in self.skip_columns:
                continue

            item_text = item.text(column_index)

            # Check quoted terms for exact match
            if any(item_text == term for term in self.quoted_terms):
                return True

            # Check unquoted terms with wildcard support
            if any(self._matches_unquoted_term(item_text, term) for term in self.unquoted_terms):
                return True

        return False

    def _matches_unquoted_term(self, item_text, term):
        """Helper method to check if item_text matches the unquoted term.
        """
        if bb.utils.TextExtraction.is_contains_wildcard(term):
            return fnmatch.fnmatch(item_text, term)
        else:
            return term in item_text

    def _update_total_matches(self, total_matches: Optional[int] = None):
        """Update the text of the match count label with the total number of matches.
        """
        total_matches = total_matches or len(self._all_match_items)
        self.match_count_button.set_match_count(total_matches)

    def _reset_highlight(self):
        """Reset the highlight and clears matched items.
        """
        # Reset the highlight for all items
        self.tree_widget.clear_highlight()
        # Clear any previously matched items
        self._all_match_items.clear()
        self._update_total_matches()

    def _highlight_search(self):
        """Highlight the items in the tree widget that match the search criteria.
        """
        # Reset the highlight for all items
        self._reset_highlight()

        # Get the selected column, condition, and keyword
        keyword = self.text().strip()

        # Return if the keyword is empty
        if not keyword:
            return

        # Match terms enclosed in either double or single quotes for fixed string match
        self.quoted_terms, self.unquoted_terms = bb.utils.TextExtraction.extract_terms(keyword)

        for column_index in range(self.tree_widget.columnCount()):
            if column_index in self.skip_columns:
                continue

            match_items = set()

            # Handle fixed string match terms with case-insensitive matching
            for term in self.quoted_terms:
                match_items.update(self.tree_widget.findItems(term, self.FIXED_STRING_MATCH_FLAGS, column_index))

            # Handle contains match terms
            for term in self.unquoted_terms:
                flags = self.WILDCARD_MATCH_FLAGS if bb.utils.TextExtraction.is_contains_wildcard(term) else self.CONTAINS_MATCH_FLAGS

                # Find items that contain the term, regardless of its position in the string
                match_items.update(self.tree_widget.findItems(term, flags, column_index))

            # Highlight the matched items
            self.tree_widget.highlight_items(match_items, column_index)

            # Store all matched items
            self._all_match_items.update(match_items)

        self._update_total_matches()

    def _set_property_active(self, state: bool = True):
        """Set the active state of the button.
        """
        self._is_active = state
        self.setProperty('active', self._is_active)
        self.update_style()

    def _apply_search(self):
        """Apply the filters specified by the user to the tree widget.
        """
        self.tree_widget.clear_highlight()

        # Hide all items
        bb.utils.TreeUtil.hide_all_items(self.tree_widget)
        # Show match items
        bb.utils.TreeUtil.set_items_visibility(self._all_match_items, is_visible=True)

    def _reset_search(self):
        """Reset the search and show all items.
        """
        self._is_searching = False
        # Show all items
        bb.utils.TreeUtil.show_all_items(self.tree_widget)

        self._highlight_search()


# Main Function
# -------------
def main():
    """Create the application and main window, and show the widget.
    """
    import sys
    from blackboard.examples.example_data_dict import COLUMN_NAME_LIST, ID_TO_DATA_DICT

    # Create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()

    # Set theme of QApplication to the dark theme
    bb.theme.set_theme(app, 'dark')

    # Create the tree widget with example data
    tree_widget = widgets.GroupableTreeWidget()
    tree_widget.setHeaderLabels(COLUMN_NAME_LIST)
    tree_widget.add_items(ID_TO_DATA_DICT)

    # Create an instance of the widget and set it as the central widget
    search_edit = SimpleSearchEdit(tree_widget, parent=window)

    main_widget = QtWidgets.QWidget()
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    main_layout.addWidget(search_edit)
    main_layout.addWidget(tree_widget)

    # search_edit.set_search_column('Name')
    shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+F'), main_widget)
    shortcut.activated.connect(search_edit.set_text_as_selection)

    # Create the scalable view and set the tree widget as its central widget
    scalable_view = widgets.ScalableView(widget=main_widget)

    # Add the tree widget to the layout of the widget
    window.setCentralWidget(scalable_view)

    # Show the window
    window.show()

    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
