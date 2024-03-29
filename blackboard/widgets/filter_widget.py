
# Type Checking Imports
# ---------------------
from typing import Any, Optional, List, Union, overload, Dict

# Standard Library Imports
# ------------------------
import re

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets


class MatchContainsCompleter(QtWidgets.QCompleter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set the completion mode to match items containing the typed text
        self.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

class FilterBarWidget(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        # Initialize setup
        self.__init_ui()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        
        UI Wireframe:

            +-------------------------+
            | [Filter 1][Filter 2][+] |
            +-------------------------+
        """
        self.tabler_icon = TablerQIcon(opacity=0.6)

        # Create Layouts
        # --------------
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.filter_area_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.filter_area_layout)

        # Create Widgets
        # --------------
        # Add filter button
        self.add_filter_button = QtWidgets.QToolButton(self)
        self.add_filter_button.setIcon(self.tabler_icon.plus)
        self.add_filter_button.setProperty('widget-style', 'round')
        self.add_filter_button.setFixedSize(24, 24)

        # Add Widgets to Layouts
        self.main_layout.addWidget(self.add_filter_button)

        self.update_style()

    def update_style(self):
        """ Update the button's style based on its state.
        """
        self.style().unpolish(self)
        self.style().polish(self)

    def add_filter_widget(self, filter_widget: 'FilterWidget'):
        self.filter_area_layout.addWidget(filter_widget.button)

class CustomMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            # Do nothing, preventing the popup from closing
            pass  
        else:
            super().keyPressEvent(event)

class FilterPopupButton(QtWidgets.QComboBox):

    MINIMUM_WIDTH, MINIMUM_HEIGHT  = 42, 24
    LEFT_PADDING = 8
    ICON_PADDING = 16

    def __init__(self, parent = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_accessibility()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        self.is_active = False
        self.icon = None

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets."""
        self.__init_popup_menu()
        self.__init_ui_properties()
        self.__init_style()

    def __init_popup_menu(self):
        """Setup the popup menu of the widget."""
        self.popup_menu = CustomMenu()

        bb.utils.KeyBinder.bind_key('Enter', self, self.showPopup)
        bb.utils.KeyBinder.bind_key('Return', self, self.showPopup)

    def __init_ui_properties(self):
        """Setup UI properties like size, cursor, etc."""
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self.setFixedHeight(self.MINIMUM_HEIGHT)
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)

    def __init_style(self):
        """Setup the style of the widget."""
        self.setProperty('widget-style', 'round')
        self.setStyleSheet(f'''
            QComboBox[widget-style="round"] {{
                padding: 0 0 0 {self.LEFT_PADDING + self.ICON_PADDING};
            }}
        ''')

    def __init_accessibility(self):
        """Setup accessibility features like keyboard navigation and screen reader support."""
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def set_active(self, state: bool = True):
        """Set the active state of the button.
        """
        self.is_active = state
        self.setProperty('active', self.is_active)
        self.update_style()

    def update_style(self):
        """ Update the button's style based on its state.
        """
        self.style().unpolish(self)
        self.style().polish(self)

    def set_icon(self, icon: QtGui.QIcon):
        """Set the icon of the button.
        """
        self.icon = icon

    # Event Handling or Override Methods
    # ----------------------------------
    def setCurrentText(self, text: str):
        """Set the current text of the button.
        """
        self.clear()
        self.addItem(text)
        super().setCurrentText(text)

    def showPopup(self):
        """Show the popup menu.
        """
        self.popup_menu.popup(self.mapToGlobal(QtCore.QPoint(0, self.height())))

    def hidePopup(self):
        """Hide the popup menu.
        """
        try:
            self.popup_menu.hide()
        except RuntimeError:
            pass

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Handles the painting of the button, including its icon and opacity."""
        super().paintEvent(event)

        if not self.icon:
            return

        with QtGui.QPainter(self) as painter:
            # Adjust opacity based on active state
            painter.setOpacity(1.0 if self.is_active else 0.6)

            # Calculate position and size for the icon
            icon_size = self.iconSize()
            rect = self.rect()
            icon_x = self.LEFT_PADDING
            icon_y = (rect.height() - icon_size.height()) // 2
            icon_rect = QtCore.QRect(icon_x, icon_y, icon_size.width() - 2, icon_size.height())

            # Paint the icon
            self.icon.paint(painter, icon_rect)

class FilterWidget(QtWidgets.QWidget):
    label_changed = QtCore.Signal(str)
    activated = QtCore.Signal(list)

    # Initialization and Setup
    # ------------------------
    def __init__(self, filter_name: str = str(), parent=None, *args, **kwargs):
        super().__init__(parent, QtCore.Qt.WindowType.Popup, *args, **kwargs)

        # Store the filter name
        self.filter_name = filter_name
        self._is_filter_applied = False

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        # Attributes
        # ------------------
        self.filtered_list = list()
        self.tabler_icon = TablerQIcon(opacity=0.6)

        # Private Attributes
        # ------------------
        self._initial_focus_widget: QtWidgets.QWidget = None
        self._saved_state = dict()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.

        UI Wireframe:

            ( FilterPopupButton ⏷)
            +---------------------------------------------+
            | Condition ⏷               [Clear] [Remove] |
            | ------------------------------------------- |
            |                                             |
            |        Widget-specific content area         |
            |                                             |
            | ------------------------------------------- |
            |                     [Cancel] [Apply Filter] |
            +---------------------------------------------+

        """
        self.setWindowTitle(self.filter_name)  # Set window title

        # Create Layouts
        # --------------
        # Main layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Title bar with remove icon
        self.title_layout = QtWidgets.QHBoxLayout()
        self.title_layout.setSpacing(3)
        self.main_layout.addLayout(self.title_layout)

        # Widget-specific content area
        self.widget_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.widget_layout)

        # 
        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.buttons_layout)

        # Create Widgets
        # --------------
        # Initialize the filter button
        self._button = FilterPopupButton(self.parent())
        # self._button.set_filter_widget(self)
        self.set_button_text()
        self.__init_button_popup_menu()

        self.condition_combo_box = QtWidgets.QComboBox()
        self.condition_combo_box.setProperty('widget-style', 'clean')
        self.condition_combo_box.addItems(['Condition1', 'Condition2'])

        self.clear_button = QtWidgets.QToolButton(self)
        self.clear_button.setIcon(self.tabler_icon.clear_all)
        self.clear_button.setToolTip("Clear all")

        self.remove_button = QtWidgets.QToolButton(self)
        self.remove_button.setProperty('color', 'red')
        self.remove_button.setIcon(self.tabler_icon.trash)
        self.remove_button.setToolTip("Remove this filter from Quick Access")

        # Add Confirm and Cancel buttons
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setProperty('widget-style', 'borderless')
        self.apply_button = QtWidgets.QPushButton("Apply Filter")
        self.apply_button.setProperty('widget-style', 'borderless')
        self.apply_button.setProperty('color', 'blue')

        # Add Widgets to Layouts
        # ----------------------
        self.title_layout.addWidget(self.condition_combo_box)
        self.title_layout.addStretch()
        self.title_layout.addWidget(self.clear_button)
        self.title_layout.addWidget(self.remove_button)

        # Add Confirm and Cancel buttons
        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.cancel_button)
        self.buttons_layout.addWidget(self.apply_button)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.apply_button.clicked.connect(self.apply_filter)

        self.cancel_button.clicked.connect(self.discard_change)
        self.cancel_button.clicked.connect(self.hide_popup)
        
        self.clear_button.clicked.connect(self.set_filter_applied)
        self.clear_button.clicked.connect(self.clear_state)
        self.clear_button.clicked.connect(self.clear_filter)
        self.clear_button.clicked.connect(self._emit_clear_signals)
        self.clear_button.clicked.connect(self.hide_popup)

        self.remove_button.clicked.connect(self.remove_filter)

        self.activated.connect(self._update_filtered_list)

        # Connect signals with the filter button
        self.label_changed.connect(self.set_button_text)
        self.activated.connect(self._update_button_active_state)

        bb.utils.KeyBinder.bind_key('Enter', self, self.apply_filter)

    def __init_button_popup_menu(self):
        # Update the popup menu with the new filter widget
        action = QtWidgets.QWidgetAction(self._button.popup_menu)
        action.setDefaultWidget(self)
        self._button.popup_menu.addAction(action)

    # Private Methods
    # ---------------
    def _update_filtered_list(self, filtered_list: List[Any]):
        self.filtered_list = filtered_list

    def _update_button_active_state(self):
        """Update the active state based on the filter widget's state.
        """
        self._button.set_active(self.is_active)

    def _format_text(self, text: str) -> str:
        """Format the text to be displayed on the button.
        """
        return f"{self.filter_name} • {text}"

    def _emit_clear_signals(self):
        # Emit the label_changed signal with an empty string to indicate that the condition is cleared
        self.label_changed.emit(str())
        # Emit the activated signal with an empty list to indicate no active date range
        self.activated.emit(list())

    # Public Methods
    # --------------
    def hide_popup(self):
        self._button.popup_menu.hide()

    def apply_filter(self):
        self.set_filter_applied()
        self.save_change()
        self.hide_popup()

    def set_button_text(self, text: str = str(), use_format: bool = True):
        """Update the button's text. Optionally format the text.
        """
        # Format the text based on the 'use_format' flag.
        text = self._format_text(text) if use_format else text
        # Update the button's text
        self._button.setCurrentText(text)

    def set_icon(self, icon: QtGui.QIcon):
        self.setWindowIcon(icon)
        self._button.set_icon(icon)

    def set_filter_applied(self):
        self._is_filter_applied = True

    def save_state(self, key, value: Any = None):
        """Saves the given state with the specified key.
        """
        self._saved_state[key] = value

    def load_state(self, key, default_value: Any = None):
        """Loads the state associated with the given key.
        """
        return self._saved_state.get(key, default_value)

    def clear_state(self):
        """Clears all saved states.
        """
        self._saved_state.clear()

    def set_initial_focus_widget(self, widget):
        self._initial_focus_widget = widget

    @property
    def button(self):
        return self._button

    @property
    def is_active(self):
        raise NotImplementedError('')

    # Slot Implementations
    # --------------------
    def discard_change(self):
        """Method to discard changes. This should be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement discard_change")

    def save_change(self):
        """Method to save changes. This should be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement save_change")

    def remove_filter(self):
        """Method to remove the filter. This should be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement remove_filter")

    def clear_filter(self):
        """Method to clear the condition. This should be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement clear_filter")

    # Event Handling or Override Methods
    # ----------------------------------
    def showEvent(self, event):
        """Override the show event to set the focus on the initial widget.
        """
        super().showEvent(event)

        if self._initial_focus_widget:
            self._initial_focus_widget.setFocus()

    def hideEvent(self, event):
        """Overrides the hide event to discard changes if not applying the filter.
        """
        if not self._is_filter_applied:
            self.discard_change()
        else:
            # Reset the flag if the widget is hidden after applying the filter
            self._is_filter_applied = False
        
        super().hideEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        # Ignore mouse release events to prevent the menu from closing
        pass

class DateRangeFilterWidget(FilterWidget):
    RELATIVE_DATES = ["Selected Date Range", "Today", "Yesterday", "Last 7 Days", "Last 15 Days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        # Attributes
        # ----------
        today = QtCore.QDate.currentDate()
        # Mapping of indices to their corresponding date range logic
        self.date_ranges = {
            1: (today, today),                           # "Today"
            2: (today.addDays(-1), today.addDays(-1)),   # "Yesterday"
            3: (today.addDays(-7), today),               # "Last 7 Days"
            4: (today.addDays(-15), today),              # "Last 15 Days"
            # Add more date ranges here if needed
        }

        self.start_date, self.end_date = None, None

        # Private Attributes
        # ------------------
        ...

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.
        """
        self.set_icon(TablerQIcon.calendar)

        # Create widgets and layouts here
        self.calendar = widgets.RangeCalendarWidget(self)
        self.relative_date_combo_box = QtWidgets.QComboBox(self)
        self.relative_date_combo_box.addItems(self.RELATIVE_DATES)

        # Set the layout for the widget
        self.widget_layout.addWidget(self.relative_date_combo_box)
        self.widget_layout.addWidget(self.calendar)

        self.set_initial_focus_widget(self.relative_date_combo_box)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.relative_date_combo_box.currentIndexChanged.connect(self.select_relative_date_range)
        self.calendar.range_selected.connect(self.select_absolute_date_range)

    @property
    def is_active(self):
        return self.relative_date_combo_box.currentIndex() != 0 or \
            self.relative_date_combo_box.itemText(0) != self.RELATIVE_DATES[0]

    # Slot Implementations
    # --------------------
    def discard_change(self):
        current_index = self.load_state('current_index', 0)
        self.start_date, self.end_date = self.load_state('date_range', (None, None))
        filter_label = self.load_state('filter_label', str())

        self.relative_date_combo_box.setCurrentIndex(current_index)

        if current_index == 0:
            self.relative_date_combo_box.setItemText(0, filter_label)
        self.calendar.select_date_range(self.start_date, self.end_date)

    def save_change(self):
        
        current_index = self.relative_date_combo_box.currentIndex()
        filter_label = self.relative_date_combo_box.currentText()
        
        date_range = self.calendar.get_date_range()
        self.start_date, self.end_date = date_range

        self.save_state('current_index', current_index)
        self.save_state('date_range', date_range)
        self.save_state('filter_label', filter_label)

        start_date_str = self.start_date.toString(QtCore.Qt.DateFormat.ISODate) if self.start_date else str()
        end_date_str = self.end_date.toString(QtCore.Qt.DateFormat.ISODate) if self.end_date else str()

        if start_date_str or end_date_str:
            date_list = bb.utils.DateUtil.get_date_list(start_date_str, end_date_str)
        else:
            date_list = list()
            filter_label = str()

        self.label_changed.emit(filter_label)
        self.activated.emit(date_list)

    def clear_filter(self):
        """Clears the selected date range and resets the relative date selector.
        """
        # Reset the relative date selector to its initial state
        self.relative_date_combo_box.setCurrentIndex(0)
        self.relative_date_combo_box.setItemText(0, self.RELATIVE_DATES[0])

        # Clear any selections made in the calendar
        self.start_date, self.end_date = None, None
        self.calendar.clear()

    def select_relative_date_range(self, index):
        # Reset the first item text if a predefined relative date is selected
        if index > 0:
            self.relative_date_combo_box.setItemText(0, "Selected Date Range")

        start_date, end_date = self.date_ranges.get(index, (None, None))
        self.calendar.select_date_range(start_date, end_date)

    def select_absolute_date_range(self, start_date, end_date):
        # Check if end_date is None (single date selection)
        if end_date is None or start_date == end_date:
            formatted_range = start_date.toString(QtCore.Qt.DateFormat.ISODate)
        else:
            formatted_range = f"{start_date.toString(QtCore.Qt.DateFormat.ISODate)} to {end_date.toString(QtCore.Qt.DateFormat.ISODate)}"

        # Update the first item in the relative date selector
        self.relative_date_combo_box.setItemText(0, formatted_range)

        # Set the first item as the current item
        self.relative_date_combo_box.setCurrentIndex(0)

class MultiSelectFilterWidget(FilterWidget):
    """A widget representing a filter with a checkable tree.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        # Attributes
        # ----------
        ...

        # Private Attributes
        # ------------------
        ...

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        """
        # Setup Widgets 
        # -------------
        # Create widgets and layouts
        self.set_icon(TablerQIcon.list_check)

        self.tag_widget = widgets.TagWidget(self)

        #
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setProperty('has-placeholder', True)
        self.line_edit.addAction(self.tabler_icon.layout_grid_add, QtWidgets.QLineEdit.ActionPosition.LeadingPosition)

        # Set placeholder text and tooltip for line edit
        self.line_edit.setPlaceholderText("Press 'Enter' to add filters (separate with a comma, line break, or '|')")
        self.line_edit.setToolTip('Enter filter items, separated by a comma, newline, or pipe. Press Enter to apply.')

        self.set_initial_focus_widget(self.line_edit)

        # Completer setup
        self.completer = MatchContainsCompleter(self)
        self.line_edit.setCompleter(self.completer)

        # Tree widget
        self.tree_widget = QtWidgets.QTreeWidget(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setRootIsDecorated(False)

        # Setup Layouts
        # -------------
        # Set the layout for the widget
        self.widget_layout.addWidget(self.tag_widget)
        self.widget_layout.addWidget(self.line_edit)
        self.widget_layout.addWidget(self.tree_widget)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.tag_widget.tag_removed.connect(self.uncheck_item)
        # Input text field
        self.line_edit.editingFinished.connect(self.update_checked_state)
        self.line_edit.textChanged.connect(self.update_style)
        # Connect completer's activated signal to add tags
        self.completer.activated.connect(self.update_checked_state)
        # Tree widget
        self.tree_widget.itemChanged.connect(self.update_tag_as_checked)
        self.tree_widget.model().rowsInserted.connect(self.update_completer)
        self.tree_widget.model().rowsRemoved.connect(self.update_completer)

    def uncheck_item(self, tag_name):
        self.set_check_items([tag_name], False)

    def update_style(self):
        self.line_edit.style().unpolish(self.line_edit)
        self.line_edit.style().polish(self.line_edit)

    def update_completer(self):
        item_names = [item.text(0) for item in bb.utils.TreeUtil.get_child_items(self.tree_widget)]
        model = QtCore.QStringListModel(item_names)
        self.completer.setModel(model)

    def update_checked_state(self):
        text = self.line_edit.text()
        tag_names = [t.strip() for t in self.split_keyswords(text) if t.strip()]
        
        self.set_check_items(tag_names)

        self.line_edit.clear()

    def add_new_tag_to_tree(self, tag_name: str):
        """Add a new tag to the tree, potentially in a new group."""
        # Check if a 'Custom Tags' group exists, if not, create it
        matched_custom_tags_items = self.find_tree_items('Custom Tags')

        if not matched_custom_tags_items:
            custom_tags_item = self.add_item('Custom Tags')
        else:
            custom_tags_item = matched_custom_tags_items[0]

        # Add the new tag as a child of the 'Custom Tags' group
        new_tag_item = self.add_item(tag_name, custom_tags_item)

        self.tree_widget.expandAll()
        return new_tag_item

    def find_tree_items(self, item_name: str):
        flags = QtCore.Qt.MatchFlag.MatchExactly | QtCore.Qt.MatchFlag.MatchRecursive
        return self.tree_widget.findItems(item_name, flags)

    @staticmethod
    def split_keyswords(text, splitter: str = '\t\n,|'):
        return re.split(f'[{splitter}]+', text)

    def set_check_items(self, tag_names: List[str], check_state: bool = True):
        flags = QtCore.Qt.MatchFlag.MatchWildcard | QtCore.Qt.MatchFlag.MatchRecursive
        check_state = QtCore.Qt.CheckState.Checked if check_state else QtCore.Qt.CheckState.Unchecked

        for tag in tag_names:
            # Check if the tag is a wildcard
            is_wildcard = '*' in tag

            # Find items that match the text in the specified column (0 in this case)
            matching_items = self.tree_widget.findItems(tag, flags, 0)
            
            if not matching_items and not is_wildcard:
                # If no matching items and tag is not a wildcard, add as a new tag
                new_tag_item = self.add_new_tag_to_tree(tag)
                matching_items.append(new_tag_item)

            for item in matching_items:
                item.setCheckState(0, check_state)

        self.line_edit.clear()

    def update_line_edit_as_checked(self):
        self.line_edit.setText(', '.join(self.get_checked_item_texts()))

    def update_tag_as_checked(self):
        current_tag_name_set = self.tag_widget.tags

        tag_names = set(self.get_checked_item_texts())

        # Tags to be added are those in tag_names but not in current_tag_name_set
        tags_to_add = tag_names - current_tag_name_set

        # Tags to be tag_removed are those in current_tag_name_set but not in tag_names
        tags_to_remove = current_tag_name_set - tag_names

        # Add new tags
        for tag in tags_to_add:
            self.tag_widget.add_tag(tag)

        # Remove old tags
        for tag in tags_to_remove:
            self.tag_widget.remove_tag(tag)

    @property
    def is_active(self):
        return bool(self.tag_widget.tags)

    def restore_checked_state(self, checked_state_dict: dict, parent_item: QtWidgets.QTreeWidgetItem = None):
        parent_item = parent_item or self.tree_widget.invisibleRootItem()

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            key = child.text(0)
            checked_state = checked_state_dict.get(key, False)
            child.setCheckState(0, checked_state)

            self.restore_checked_state(checked_state_dict, child)

    def get_checked_state_dict(self, checked_state_dict: dict = dict(), parent_item: QtWidgets.QTreeWidgetItem = None):
        parent_item = parent_item or self.tree_widget.invisibleRootItem()

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            # Assuming the first column is used for unique identification
            key = child.text(0)
            checked_state_dict[key] = child.checkState(0)
            checked_state_dict = self.get_checked_state_dict(checked_state_dict, child)

        return checked_state_dict

    def clear_filter(self):
        """Clears all selections in the tree widget.
        """
        # Uncheck all items in the tree widget
        self.uncheck_all()

        # Clear the line edit
        self.line_edit.clear()

    def uncheck_all(self, parent_item: QtWidgets.QTreeWidgetItem = None):
        """Recursively unchecks all child items.
        """
        parent_item = parent_item or self.tree_widget.invisibleRootItem()

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
            self.uncheck_all(child)

    def add_items(self, item_names: Union[Dict[str, List[str]], List[str]]):
        """Adds items to the tree widget.

        Args:
            item_names (Union[Dict[str, List[str]], List[str]]): If a dictionary is provided, it represents parent-child relationships where keys are parent item names and values are lists of child item names. If a list is provided, it contains item names to be added at the root level.
        """
        if isinstance(item_names, dict):
            self._add_items_from_dict(item_names)
        elif isinstance(item_names, list):
            self._add_items_from_list(item_names)
        else:
            raise ValueError("Invalid type for item_names. Expected a list or a dictionary.")

        self.tree_widget.expandAll()

    def add_item(self, item_label: str, parent: Optional[QtWidgets.QTreeWidgetItem] = None):
        """Adds a single item to the tree widget.

        Args:
            item_label (str): The label for the tree item.
            parent (QtWidgets.QTreeWidgetItem, optional): The parent item for this item. Defaults to None, in which case the item is added at the root level.

        Returns:
            QtWidgets.QTreeWidgetItem: The created tree item.
        """
        parent = parent or self.tree_widget.invisibleRootItem()
        tree_item = QtWidgets.QTreeWidgetItem(parent, [item_label])
        tree_item.setFlags(tree_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsAutoTristate)
        tree_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

        return tree_item

    def _add_items_from_dict(self, item_dict: Dict[str, List[str]]):
        """Adds items to the tree widget based on a dictionary of parent-child relationships.

        Args:
            item_dict (Dict[str, List[str]]): A dictionary where keys are parent item names and values are lists of child item names.
        """
        for parent_name, child_names in item_dict.items():
            parent_item = self.add_item(parent_name)
            self._add_items_from_list(child_names, parent_item)

    def _add_items_from_list(self, item_list: List[str], parent: Optional[QtWidgets.QTreeWidgetItem] = None):
        """Adds items to the tree widget at the root level from a list of item names.

        Args:
            item_list (List[str]): A list of item names to be added at the root level.
        """
        for item_name in item_list:
            self.add_item(item_name, parent)

    def get_checked_item_texts(self) -> List[str]:
        """Returns the checked items in the tree.
        """
        all_items = bb.utils.TreeUtil.get_child_items(self.tree_widget)
        checked_items = []
        for tree_item in all_items:
            if tree_item.childCount() or tree_item.checkState(0) == QtCore.Qt.CheckState.Unchecked:
                continue
            checked_items.append(tree_item.text(0))

        return checked_items

    # Slot Implementations
    # --------------------
    def discard_change(self):
        checked_state_dict = self.load_state('checked_state', dict())
        self.restore_checked_state(checked_state_dict)

    def save_change(self):
        checked_state_dict = self.get_checked_state_dict()
        self.save_state('checked_state', checked_state_dict)

        checked_item_texts = self.get_checked_item_texts()

        self.label_changed.emit(', '.join(checked_item_texts))
        self.activated.emit(checked_item_texts)

class FileTypeFilterWidget(FilterWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.
        """
        self.set_icon(TablerQIcon.file)

        # Custom file type input
        self.custom_input = QtWidgets.QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom file types (e.g., txt)")
        self.custom_input.setProperty('has-placeholder', True)
        self.custom_input.addAction(self.tabler_icon.file_plus, QtWidgets.QLineEdit.ActionPosition.LeadingPosition)
        self.custom_input.textChanged.connect(self.update_style)
        self.widget_layout.addWidget(self.custom_input)

        self.set_initial_focus_widget(self.custom_input)

        # Preset file type groups with tooltips and extensions
        self.file_type_groups = {
            "Image Sequences": (["exr", "dpx", "jpg", "jpeg"], "Image sequence formats like EXR, DPX"),
            "Video Files": (["mp4", "avi", "mkv", 'mov'], "Video formats like MP4, AVI, MKV"),
            "Audio Files": (["mp3", "wav", "aac"], "Audio formats like MP3, WAV, AAC"),
            "Image Files": (["jpg", "png", "gif"], "Image formats like JPG, PNG, GIF"),
            "Document Files": (["pdf", "docx", "txt"], "Document formats like PDF, DOCX, TXT"),
        }

        self.checkboxes = {}
        for group, (extensions, tooltip) in self.file_type_groups.items():
            checkbox = QtWidgets.QCheckBox(group)
            checkbox.setToolTip(tooltip)
            checkbox.extensions = extensions  # Store the extensions with the checkbox
            self.widget_layout.addWidget(checkbox)
            self.checkboxes[group] = checkbox

    def update_style(self):
        self.custom_input.style().unpolish(self.custom_input)
        self.custom_input.style().polish(self.custom_input)

    def __init_signal_connections(self):
        """Set up signal connections.
        """
        ...

    @property
    def is_active(self):
        """Checks if the filter is active (any file type is selected or custom types are specified).
        """
        # Check if any checkbox is checked
        if any(checkbox.isChecked() for checkbox in self.checkboxes.values()):
            return True

        # Check if there is any text in the custom input
        if self.custom_input.text().strip():
            return True

        # If none of the above conditions are met, return False
        return False

    def get_selected_extensions(self):
        selected_extensions = list()
        
        for checkbox in self.checkboxes.values():
            if not checkbox.isChecked():
                continue

            selected_extensions.extend(checkbox.extensions)

        custom_types = self.get_custom_types()
        selected_extensions.extend(custom_types)

        return list(set(selected_extensions))

    def get_custom_types(self):
        custom_types = self.custom_input.text().strip().split(',')
        custom_types = [ext.strip() for ext in custom_types if ext.strip()]
        return custom_types

    def get_checked_state_dict(self):
        """Returns a dictionary of the checked state for each checkbox.
        """
        return {checkbox.text(): checkbox.isChecked() for checkbox in self.checkboxes.values()}

    def uncheck_all(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def clear_filter(self):
        """Clears all selections and resets the filter to its initial state.
        """
        # Uncheck all checkboxes
        self.uncheck_all()
        # Clear the custom input field
        self.custom_input.clear()

    # Slot Implementations
    # --------------------
    def save_change(self):
        """Save the changes and emit the filter data.
        """
        custom_types = self.get_custom_types()
        checked_state_dict = self.get_checked_state_dict()
        
        # Save and add custom extensions
        self.save_state('custom_input', custom_types)
        self.save_state('checked_state', checked_state_dict)

        # 
        selected_extensions = self.get_selected_extensions()

        # Emit the signal with the selected file extensions
        self.label_changed.emit(", ".join(selected_extensions))
        self.activated.emit(selected_extensions)

    def discard_change(self):
        """Revert any changes made.
        """
        custom_input = self.load_state('custom_input', list())
        checked_state_dict = self.load_state('checked_state', dict())

        if not checked_state_dict:
            self.uncheck_all()

        # Restore the state of checkboxes from the saved state
        for checkbox_text, checked in checked_state_dict.items():
            self.checkboxes[checkbox_text].setChecked(checked)

        # Restore the text of the custom input from the saved state
        custom_input_text = ', '.join(custom_input)
        self.custom_input.setText(custom_input_text)

class BooleanFilterWidget(FilterWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._is_active = False

        self.__init_ui()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.
        """
        self.set_icon(TablerQIcon.checkbox)
        self.button.showPopup = self.toggle_active

    def toggle_active(self):
        self.set_active(not self._is_active)

    def set_active(self, state: bool = True):
        self._is_active = state
        self.activated.emit([self._is_active])

    @property
    def is_active(self):
        """
        """
        return self._is_active

if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    bb.theme.set_theme(app, 'dark')

    main_window = QtWidgets.QMainWindow()
    main_layout = QtWidgets.QHBoxLayout()

    # Date Filter Setup
    date_filter_widget = DateRangeFilterWidget(filter_name="Date")
    date_filter_widget.activated.connect(print)
    # Shot Filter Setup
    shot_filter_widget = MultiSelectFilterWidget(filter_name="Shot")
    sequence_to_shot = {
        "100": [
            "100_010_001", "100_020_050"
        ],
        "101": [
            "101_022_232", "101_023_200"
        ],
    }
    shot_filter_widget.add_items(sequence_to_shot)
    shots = ['102_212_010', '103_202_110']
    shot_filter_widget.add_items(shots)
    shot_filter_widget.activated.connect(print)

    # File Type Filter Setup
    file_type_filter_widget = FileTypeFilterWidget(filter_name="File Type")
    file_type_filter_widget.activated.connect(print)

    show_hidden_filter_widget = BooleanFilterWidget(filter_name='Show Hidden')
    show_hidden_filter_widget.activated.connect(print)

    # Filter bar
    filter_bar_widget = FilterBarWidget()
    filter_bar_widget.add_filter_widget(date_filter_widget)
    filter_bar_widget.add_filter_widget(shot_filter_widget)
    filter_bar_widget.add_filter_widget(file_type_filter_widget)
    filter_bar_widget.add_filter_widget(show_hidden_filter_widget)

    # Adding widgets to the layout
    main_layout.addWidget(filter_bar_widget)
    
    main_widget = QtWidgets.QWidget()
    main_widget.setLayout(main_layout)
    main_window.setCentralWidget(main_widget)

    main_window.show()
    app.exec_()

