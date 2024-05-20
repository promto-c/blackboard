# Type Checking Imports
# ---------------------
from typing import Optional

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
    It changes its appearance when the mouse hovers over it, providing a visual cue
    for user interaction.

    Attributes:
        _current_label (str): Stores the current label text of the button.
    """
    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None):
        """Initializes the MatchCountButton with a parent widget, sets properties, and tooltip.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget of the button. Defaults to None.
        """
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        self._current_label = str()

    def __init_ui(self):
        """Sets up the initial properties of the button."""
        self.setProperty('widget-style', 'action-clear')
        self.setFixedHeight(16)
        # Setting a default tooltip
        self.setToolTip("Click to clear search")

    # Public Methods
    # --------------
    def set_match_count(self, total_matches: int):
        """Sets the visibility and text of the button based on the total match count.

        Args:
            total_matches (int): The number of matches to display.
        """
        self.setVisible(bool(total_matches))
        self.setText(str(total_matches))

    # Overridden Methods
    # ------------------
    def enterEvent(self, event: QtCore.QEvent):
        """Handles mouse entry events on the button, changing the icon and cursor.

        Args:
            event (QtCore.QEvent): The mouse enter event.
        """
        super().enterEvent(event)
        self._current_label = self.text()
        self.setIcon(TablerQIcon.x)
        self.setText('')
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

    def leaveEvent(self, event: QtCore.QEvent):
        """Handles mouse leave events on the button, resetting the icon and cursor.

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
        is_active (bool): Indicates whether the search filter is currently applied.
        _all_match_items (set): A set of items that match the current search criteria.
    """
    activated = QtCore.Signal()

    # Initialization and Setup
    # ------------------------
    def __init__(self, tree_widget: 'widgets.GroupableTreeWidget', parent: QtWidgets.QWidget = None):
        """Initializes the SimpleSearchEdit with a reference to the tree widget and sets up
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
        """Set up the initial values for the widget.
        """
        # Attributes
        # ----------
        self.tabler_icon = TablerQIcon(opacity=0.6)
        self.is_active = False
        self.is_searching = False

        # Private Attributes
        # ------------------
        self._all_match_items = set()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        """
        self.setProperty('widget-style', 'round')
        self.setProperty('has-placeholder', True)
        self.setPlaceholderText('Type to Search')
        self.setFixedHeight(24)

        # Add search icon
        self.addAction(self.tabler_icon.search, QtWidgets.QLineEdit.ActionPosition.LeadingPosition)

        self.__init_match_count_action()
        self.update_style()

    def __init_match_count_action(self):
        """Initializes the match count action and adds it to the line edit."""
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
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.textChanged.connect(self.set_inactive)
        self.textChanged.connect(self._highlight_search)
        self.textChanged.connect(self.update_style)
        self.match_count_button.clicked.connect(self.clear)
        self.tree_widget.item_added.connect(self._handle_item_added)

        bb.utils.KeyBinder.bind_key('Enter', self, self.set_active)
        bb.utils.KeyBinder.bind_key('Return', self, self.set_active)
        bb.utils.KeyBinder.bind_key('Escape', self, self.clear)

    # Public Methods
    # --------------
    def set_text_as_selection(self):
        keywords = {f'"{index.data()}"' for index in self.tree_widget.selectedIndexes()}

        self.setText('|'.join(keywords))
        self.setFocus()

    def set_active(self):
        self.is_searching = False
        if not self._all_match_items and not self.tree_widget.has_more_items_to_fetch:
            return

        self._set_property_active(True)
        self._apply_search()
        self.activated.emit()

        if self.tree_widget.has_more_items_to_fetch:
            self.is_searching = True
            self.tree_widget.fetch_all()

    def set_inactive(self):
        if not self.is_active:
            return

        self._set_property_active(False)
        self._reset_search()

    def update(self):
        self._highlight_search()

        if self.is_active:
            self._apply_search()

    def update_style(self):
        """ Update the button's style based on its state.
        """
        self.style().unpolish(self)
        self.style().polish(self)

    # Class Properties
    # ----------------
    @property
    def matched_items(self):
        return self._all_match_items

    # Private Methods
    # ---------------
    def _handle_item_added(self, tree_item):
        if not self.is_searching:
            return

        keyword = self.text().strip()
        if not keyword:
            return

        tree_item.setHidden(True)
        quoted_terms = bb.utils.TextExtraction.extract_quoted_terms(keyword)
        unquoted_terms = bb.utils.TextExtraction.extract_unquoted_terms(keyword)
        if self._item_matches_filter(tree_item, quoted_terms, unquoted_terms):
            self._all_match_items.add(tree_item)
            tree_item.setHidden(False)
            self._update_total_matches()

    def _item_matches_filter(self, item, quoted_terms, unquoted_terms):
        for column_index in range(self.tree_widget.columnCount()):
            item_text = item.text(column_index)
            for term in quoted_terms:
                if item_text == term:
                    return True
            for term in unquoted_terms:
                if bb.utils.TextExtraction.is_contains_wildcard(term):
                    if fnmatch.fnmatch(item_text, term):
                        return True
                else:
                    if term in item_text:
                        return True

        return False

    def _update_total_matches(self, total_matches: Optional[int] = None):
        """Update the text of the match count label with the total number of matches."""
        total_matches = total_matches or len(self._all_match_items)
        self.match_count_button.set_match_count(total_matches)

    def _highlight_search(self):
        """Highlight the items in the tree widget that match the search criteria.
        """
        # Reset the highlight for all items
        self.tree_widget.clear_highlight()

        # Clear any previously matched items
        self._all_match_items.clear()
        self._update_total_matches()

        # Get the selected column, condition, and keyword
        keyword = self.text().strip()

        # Return if the keyword is empty
        if not keyword:
            return

        # Match terms enclosed in either double or single quotes for fixed string match
        quoted_terms = bb.utils.TextExtraction.extract_quoted_terms(keyword)

        # Split the string at parts enclosed in either double or single quotes for contains match
        unquoted_terms = bb.utils.TextExtraction.extract_unquoted_terms(keyword)

        fixed_string_match_flags = QtCore.Qt.MatchFlag.MatchRecursive | QtCore.Qt.MatchFlag.MatchFixedString
        contains_match_flags = QtCore.Qt.MatchFlag.MatchRecursive | QtCore.Qt.MatchFlag.MatchContains
        wildcard_match_flags = QtCore.Qt.MatchFlag.MatchRecursive | QtCore.Qt.MatchFlag.MatchWildcard

        for column_index in range(self.tree_widget.columnCount()):
            match_items = list()

            # Handle fixed string match terms with case-insensitive matching
            for term in quoted_terms:
                match_items.extend(self.tree_widget.findItems(term, fixed_string_match_flags, column_index))

            # Handle contains match terms
            for term in unquoted_terms:
                flags = wildcard_match_flags if bb.utils.TextExtraction.is_contains_wildcard(term) else contains_match_flags

                # Find items that contain the term, regardless of its position in the string
                match_items.extend(self.tree_widget.findItems(term, flags, column_index))

            # Highlight the matched items
            self.tree_widget.highlight_items(match_items, column_index)

            # Store all matched items
            self._all_match_items.update(match_items)

        self._update_total_matches()

    def _set_property_active(self, state: bool = True):
        """Set the active state of the button.
        """
        self.is_active = state
        self.setProperty('active', self.is_active)
        self.update_style()

    def _apply_search(self):
        """Apply the filters specified by the user to the tree widget.
        """
        self.tree_widget.clear_highlight()

        # Hide all items
        self.tree_widget.hide_all_items()
        # Show match items
        self.tree_widget.show_items(self._all_match_items)

    def _reset_search(self):
        # Show all items
        self.tree_widget.show_all_items()

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
