
# Type Checking Imports
# ---------------------
from typing import Any, Optional, List, Union, Dict

# Standard Library Imports
# ------------------------
import re
import fnmatch
from functools import partial

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets


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

class MoreOptionsButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setIcon(TablerQIcon(opacity=0.6).dots_vertical)

        # Create the menu
        self.popup_menu = QtWidgets.QMenu()

        self.clicked.connect(self.show_menu)

    def addAction(self, text: str, icon: QtGui.QIcon = None):
        """Add an action to the menu."""
        action = self.popup_menu.addAction(text)
        if icon is not None:
            action.setIcon(icon)

        return action

    def show_menu(self):
        """Display the menu at the button's position."""
        self.popup_menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

class CustomMenu(QtWidgets.QMenu):

    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, button: Optional[QtWidgets.QPushButton] = None):
        super().__init__()
        self.button = button

        self.init_drag()

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            # Do nothing, preventing the popup from closing
            pass  
        else:
            super().keyPressEvent(event)

    def showEvent(self, event: QtGui.QShowEvent):
        """ Override exec_ to modify the position of the menu popup """
        if self.button:
            # Adjust the position
            pos = self.button.mapToGlobal(QtCore.QPoint(0, self.button.height()))
            self.move(pos)
        super().showEvent(event)

    def init_drag(self):
        self.dragging = False
        self.drag_start_point = QtCore.QPoint()
        self.initial_size = self.size()

    def resizeEvent(self, event):
        # Update the layout of the widget container on resize
        self.resized.emit(self.size())
        # self.widget_container.setMinimumSize(self.size())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.pos().x() >= (self.width() - 20) and event.pos().y() >= (self.height() - 20):
            self.dragging = True
            self.drag_start_point = event.pos()
            self.initial_size = self.size()
            self.setCursor(QtGui.QCursor(QtCore.Qt.SizeFDiagCursor))
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_width = max(self.initial_size.width() + (event.pos().x() - self.drag_start_point.x()), self.minimumWidth())
            new_height = max(self.initial_size.height() + (event.pos().y() - self.drag_start_point.y()), self.minimumHeight())
            self.resize(new_width, new_height)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.unsetCursor()
        super().mouseReleaseEvent(event)

class FilterPopupButton(QtWidgets.QPushButton):

    MINIMUM_WIDTH, MINIMUM_HEIGHT  = 42, 24

    def __init__(self, parent = None):
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_accessibility()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        self.is_active = False

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets."""
        self.__init_popup_menu()
        self.__init_ui_properties()

    def __init_popup_menu(self):
        """Setup the popup menu of the widget."""
        self.popup_menu = CustomMenu(button=self)
        self.setMenu(self.popup_menu)

    def __init_ui_properties(self):
        """Setup UI properties like size, cursor, etc."""
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self.setFixedHeight(self.MINIMUM_HEIGHT)
        self.setProperty('widget-style', 'round')

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

        # Vertical ellipsis button with menu
        self.more_options_button = MoreOptionsButton(self)

        # Add "Remove Filter" action
        self.remove_action = self.more_options_button.addAction("Remove Filter", self.tabler_icon.trash)
        
        self.remove_action.setProperty('color', 'red')
        self.remove_action.setToolTip("Remove this filter from Quick Access")

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
        self.title_layout.addWidget(self.more_options_button)

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

        self.remove_action.triggered.connect(self.remove_filter)

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
        self._button.popup_menu.resized.connect(self.setMinimumSize)

        # Calculate the appropriate minimum size based on content
        # self._button.popup_menu.setMinimumSize(self.minimumSizeHint())

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
    def update_style(self, widget: Optional[QtWidgets.QWidget] = None):
        if not isinstance(widget, QtWidgets.QWidget):
            widget = None
        widget = widget or self.sender() or self

        self.style().unpolish(widget)
        self.style().polish(widget)

    def unset_popup(self):
        self._button.setMenu(None)

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
        self._button.setText(text)

    def setIcon(self, icon: QtGui.QIcon):
        self.setWindowIcon(icon)
        self._button.setIcon(icon)

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
    
    def set_filter(self):
        """Method to set the filter. This should be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement set_filter")

    # Override Methods
    # ----------------
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
        self.setIcon(TablerQIcon.calendar)

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

class FilterEntryEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):

        self.tabler_icon = TablerQIcon(opacity=0.6)

        self.setProperty('has-placeholder', True)
        self.addAction(self.tabler_icon.layout_grid_add, QtWidgets.QLineEdit.ActionPosition.LeadingPosition)

        # Set placeholder text and tooltip for the line edit
        self.setPlaceholderText("Press 'Enter' to add filters (separate with a comma, line break, or '|')")
        self.setToolTip('Enter filter items, separated by a comma, newline, or pipe. Press Enter to apply.')

        # Setup the completer (assuming a completer class is defined)
        completer = bb.utils.MatchContainsCompleter(self)
        self.setCompleter(completer)

    def __init_signal_connections(self):
        self.textChanged.connect(self.update_style)

    @staticmethod
    def split_keywords(input_string):
        # Regular expression that splits on | or , or spaces not within quotes
        # It captures quoted strings or sequences of characters outside quotes not including delimiters
        pattern = re.compile(r'''
            (?:             # Start of non-capturing group for the entire pattern
                [ ]*        # Match any leading spaces (ignored in results)
                "([^"]*)"   # Capture anything within double quotes
                [ ]*        # Match any trailing spaces (ignored in results)
            |               # OR
                '([^']*)'   # Capture anything within single quotes
                [ ]*        # Match any trailing spaces (ignored in results)
            |               # OR
                ([^,|"'\s]+) # Capture any sequence of characters that aren't delimiters or quotes
            )               # End of non-capturing group
            ''', re.VERBOSE)
        
        # Find all matches based on the pattern, this ignores empty matches by the nature of the regex
        matches = pattern.findall(input_string)
        
        # Flatten the list of tuples returned by findall, and filter out any empty strings
        result = [non_empty for tup in matches for non_empty in tup if non_empty]
        
        return result

    def texts(self) -> List[str]:
        # Get text from QLineEdit, split into keywords, remove any surrounding whitespace or quotes
        return self.split_keywords(self.text())

    def update_style(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def setModel(self, model):
        self.model = model
        self.proxy_model = bb.utils.FlatProxyModel(self.model)
        # Set the model for the completer
        self.completer().setModel(self.proxy_model)

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
        self._custom_tags_item = None

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        """
        # Create Layouts
        # --------------
        # Set the layout for the widget
        self.tag_layout = QtWidgets.QHBoxLayout()
        self.widget_layout.addLayout(self.tag_layout)

        # Create Widgets
        # --------------
        # Create widgets and layouts
        self.setIcon(TablerQIcon.list_check)

        # Tree view
        self.tree_view = QtWidgets.QTreeView(self)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setRootIsDecorated(False)
        self.proxy_model = bb.utils.CheckableProxyModel()
        self.tree_view.setModel(self.proxy_model)

        self.filter_entry_edit = FilterEntryEdit(self)
        self.set_initial_focus_widget(self.filter_entry_edit)
        self.filter_entry_edit.setModel(self.tree_view.model())

        self.tag_list_view = widgets.TagListView(self)
        self.tag_list_view.setModel(self.tree_view.model())

        # Copy button
        # TODO: Implement copy_button as reusable class
        self.copy_button = QtWidgets.QPushButton(self.tabler_icon.copy, '', self)

        # Add Widgets to Layouts
        # ----------------------
        self.tag_layout.addWidget(self.tag_list_view)
        self.tag_layout.addWidget(self.copy_button)
        self.widget_layout.addWidget(self.filter_entry_edit)
        self.widget_layout.addWidget(self.tree_view)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        # Input text field
        self.filter_entry_edit.editingFinished.connect(self.update_checked_state)
        # Connect completer's activated signal to add tags
        self.filter_entry_edit.completer().activated.connect(self.update_checked_state)

        self.copy_button.clicked.connect(self.copy_data_to_clipboard)
        self.tag_list_view.tag_changed.connect(self.update_copy_button_state)

    def update_copy_button_state(self):
        """Update the state of the copy button based on the number of tags in the tag widget.
        """
        tag_count = self.tag_list_view.get_tags_count()
        self.copy_button.setEnabled(bool(tag_count))

        num_item_str = str(tag_count) if tag_count else str()
        self.copy_button.setText(num_item_str)

    def copy_data_to_clipboard(self):
        full_text = ', '.join(self.tag_list_view.get_tags())

        clipboard = QtWidgets.qApp.clipboard()
        clipboard.setText(full_text)

        # Show tooltip message
        self.show_tool_tip(f'Copied:\n{full_text}', 5000)

    def show_tool_tip(self, text: str, msc_show_time: int = 1000):
        """Show a tooltip message for the given text.
        """
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text, self, QtCore.QRect(), msc_show_time)

    def update_checked_state(self):
        self.set_check_items(self.filter_entry_edit.texts())
        self.filter_entry_edit.clear()

    def add_new_tag_to_tree(self, tag_name: str):
        """Add a new tag to the tree, potentially in a new group."""
        # Check if the 'Custom Tags' group exists
        if not self._custom_tags_item:
            self._custom_tags_item = self.add_item('Custom Tags')

        # Add the new tag as a child of the 'Custom Tags' group
        new_tag_item = self.add_item(tag_name, self._custom_tags_item)

        self.tree_view.expandAll()
        return new_tag_item

    def setModel(self, model: QtCore.QAbstractItemModel):
        """Set the model for the widget.

        Args:
            model (QtCore.QAbstractItemModel): The model to set.
        """
        self.proxy_model.setSourceModel(model)
        self.filter_entry_edit.setModel(self.proxy_model)

        self.tag_list_view.setModel(self.proxy_model)
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.expandAll()

    def set_check_items(self, keywords: List[str], checked_state: QtCore.Qt.CheckState = QtCore.Qt.CheckState.Checked):
        filter_func = partial(self.filter_keywords, keywords)
        model_indexes = bb.utils.TreeUtil.get_model_indexes(self.tree_view.model(), filter_func=filter_func)

        for model_index in model_indexes:
            self.tree_view.model().setData(model_index, checked_state, QtCore.Qt.CheckStateRole)

        # TODO: Handle to add new inputs
        # # Check if the tag is a wildcard
        # is_wildcard = '*' in keyword

        # if not matching_items and not is_wildcard:
        #     # If no matching items and tag is not a wildcard, add as a new tag
        #     new_tag_item = self.add_new_tag_to_tree(keyword)
        #     matching_items.append(new_tag_item)

    # TODO: Add support when when add parent, children should be filtered
    @staticmethod
    def filter_keywords(keywords: List[str], index: QtCore.QModelIndex):
        if not index.isValid():
            return False

        text = index.data()
        # Check each keyword against the text using fnmatch which supports wildcards like *
        return any(fnmatch.fnmatch(text, pattern) for pattern in keywords)

    @property
    def is_active(self):
        return bool(self.tag_list_view.get_tags())

    def restore_checked_state(self, checked_state_dict: dict, parent_index: QtCore.QModelIndex = QtCore.QModelIndex()):

        model_indexes = bb.utils.TreeUtil.get_model_indexes(self.tree_view.model(), parent_index)
        model_index_to_check_state = dict()

        is_proxy_model = isinstance(self.tree_view.model(), bb.utils.CheckableProxyModel)

        for model_index in model_indexes:
            text = model_index.data()
            checked_state = checked_state_dict.get(text, QtCore.Qt.CheckState.Unchecked)
            if is_proxy_model:
                model_index_to_check_state[model_index] = checked_state
            else:
                self.tree_view.model().setData(model_index, checked_state, QtCore.Qt.CheckStateRole)

        if is_proxy_model:
            self.tree_view.model().set_check_states(model_index_to_check_state)

    def get_checked_state_dict(self, checked_state_dict: Dict[str, QtCore.Qt.CheckState] = dict(), parent_index: QtCore.QModelIndex = QtCore.QModelIndex()):
        model_indexes = bb.utils.TreeUtil.get_model_indexes(self.tree_view.model(), parent_index)
        for model_index in model_indexes:
            text = model_index.data()
            checked_state = model_index.data(QtCore.Qt.CheckStateRole)
            checked_state_dict[text] = checked_state

        return checked_state_dict

    def clear_filter(self):
        """Clears all selections in the tree widget.
        """
        # Uncheck all items in the tree widget
        self.uncheck_all()

        # Clear the line edit
        self.filter_entry_edit.clear()

    def uncheck_all(self, parent_index: QtCore.QModelIndex = QtCore.QModelIndex()):
        """Recursively unchecks all child indexes.
        """
        model_indexes = bb.utils.TreeUtil.get_model_indexes(self.tree_view.model(), parent_index)

        for model_index in model_indexes:
            self.tree_view.model().setData(model_index, QtCore.Qt.CheckState.Unchecked, QtCore.Qt.CheckStateRole)

    def add_items(self, item_names: Union[Dict[str, List[str]], List[str]]):
        """Adds items to the tree widget.

        Args:
            item_names (Union[Dict[str, List[str]], List[str]]): If a dictionary is provided, it represents parent-child relationships where keys are parent item names and values are lists of child item names. If a list is provided, it contains item names to be added at the root level.
        """

        if isinstance(self.tree_view.model(), bb.utils.CheckableProxyModel):
            self.tree_view_model = QtGui.QStandardItemModel()
            self.tree_view.setModel(self.tree_view_model)

            self.filter_entry_edit.setModel(self.tree_view_model)
            self.tag_list_view.setModel(self.tree_view_model)

        if isinstance(item_names, dict):
            self._add_items_from_dict(item_names)
        elif isinstance(item_names, list):
            self._add_items_from_list(item_names)
        else:
            raise ValueError("Invalid type for item_names. Expected a list or a dictionary.")

        self.tree_view.expandAll()

    # def add_item(self, item_label: str, parent: Optional[QtWidgets.QTreeWidgetItem] = None):
    #     """Adds a single item to the tree widget.

    #     Args:
    #         item_label (str): The label for the tree item.
    #         parent (QtWidgets.QTreeWidgetItem, optional): The parent item for this item. Defaults to None, in which case the item is added at the root level.

    #     Returns:
    #         QtWidgets.QTreeWidgetItem: The created tree item.
    #     """
    #     parent = parent or self.tree_view.invisibleRootItem()
    #     tree_item = QtWidgets.QTreeWidgetItem(parent, [item_label])
    #     tree_item.setFlags(tree_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsAutoTristate)
    #     tree_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

    #     return tree_item
    
    # Implement add_item for self.tree_view
    # TODO: Implement appendRow for CheckableProxyModel
    def add_item(self, item_label: str, parent_item: QtGui.QStandardItem = None):
        """Adds a single item to the tree widget.
        """ 
        # Add items to the model
        parent_item = parent_item or self.tree_view_model
        item = QtGui.QStandardItem(item_label)
        item.setCheckable(True)
        item.setEditable(False)
        parent_item.appendRow(item)
        return item

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

    # Slot Implementations
    # --------------------
    def set_filter(self, filters: List[str]):
        self.clear_filter()
        self.set_check_items(filters)
        self.apply_filter()

    def discard_change(self):
        checked_state_dict = self.load_state('checked_state', dict())
        self.restore_checked_state(checked_state_dict)

    def save_change(self):
        checked_state_dict = self.get_checked_state_dict()
        self.save_state('checked_state', checked_state_dict)

        tags = self.tag_list_view.get_tags()

        self.label_changed.emit(', '.join(tags))
        self.activated.emit(tags)

class FileTypeFilterWidget(FilterWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.
        """
        self.setIcon(TablerQIcon.file)

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
        self.setIcon(TablerQIcon.checkbox)
        self.unset_popup()
        self.button.clicked.connect(self.toggle_active)

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
    # sequence_to_shot = {
    #     "100": [
    #         "100_010_001", "100_020_050"
    #     ],
    #     "101": [
    #         "101_022_232", "101_023_200"
    #     ],
    # }
    # shot_filter_widget.add_items(sequence_to_shot)
    # shots = ['102_212_010', '103_202_110']
    # shot_filter_widget.add_items(shots)


    # NOTE: Test set model
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

    # Setting the model for the tree view
    shot_filter_widget.setModel(model)

    shots = ['102_212_010', '103_202_110']
    # shot_filter_widget.add_items(shots)

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
