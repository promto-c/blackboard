# Type Checking Imports
# ---------------------
from typing import Any, Dict, List, Union, Tuple, Optional, Generator, Iterable

# Standard Library Imports
# ------------------------
import time, uuid, os
from numbers import Number
from itertools import islice

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets
# NOTE: test
from blackboard.widgets.header_view import SearchableHeaderView
from blackboard.utils.thread_pool import ThreadPoolManager, GeneratorWorker
from blackboard.widgets.animate_button import DataFetchingButtons

# Class Definitions
# -----------------
class TreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """A custom `QTreeWidgetItem` that can handle different data formats and store additional data in the user role.

    Attributes:
        id (int): The ID of the item.
    """
    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: Union[QtWidgets.QTreeWidget, QtWidgets.QTreeWidgetItem], 
                 item_data: Union[Dict[str, Any], List[str]] = None, 
                 item_id: int = None):
        """Initialize the `TreeWidgetItem` with the given parent and item data.
        
        Args:
            parent (Union[QtWidgets.QTreeWidget, QtWidgets.QTreeWidgetItem]): The parent `QTreeWidget` or QtWidgets.QTreeWidgetItem.
            item_data (Union[Dict[str, Any], List[str]], optional): The data for the item. Can be a list of strings or a dictionary with keys matching the headers of the parent `QTreeWidget`. Defaults to `None`.
            item_id (int, optional): The ID of the item. Defaults to `None`.
        """
        # Set the item's ID
        self.id = item_id

        # If the data for the item is in list form
        if isinstance(item_data, list):
            item_data_list = item_data

        # If the data for the item is in dictionary form
        if isinstance(item_data, dict):

            # Get the header item from the parent tree widget
            header_item = parent.headerItem() if isinstance(parent, QtWidgets.QTreeWidget) else parent.treeWidget().headerItem()

            # Get the column names from the header item
            column_names = [header_item.text(i) for i in range(header_item.columnCount())]

            # Create a list of data for the tree item
            item_data_list = [item_id] + [item_data[column] if column in item_data.keys()
                                                                 else str() 
                                                                 for column in column_names[1:]]

        # Call the superclass's constructor to set the item's data
        super().__init__(parent, map(str, item_data_list))

        # Set the UserRole data for the item.
        self._set_user_role_data(item_data_list)

    # Private Methods
    # ---------------
    def _set_user_role_data(self, item_data_list: List[Any]):
        """Set the UserRole data for the item.

        Args:
            item_data_list (List[Any]): The list of data to set as the item's data.
        """
        # Iterate through each column in the item
        for column_index, value in enumerate(item_data_list):
            # Set the value for the column in the UserRole data
            self.set_value(column_index, value)

    # Extended Methods
    # ----------------
    def get_model_indexes(self) -> List[QtCore.QModelIndex]:
        """Get the model index for each column in the tree widget.

        Returns:
            List[QtCore.QModelIndex]: A list of model index for each column in the tree widget.
        """
        # Get a list of the shown column indices
        shown_column_indexes = bb.utils.TreeUtil.get_shown_column_indexes(self.treeWidget())

        # Create a list to store the model index
        model_indexes = list()

        # Loop through each shown column index
        for column_index in shown_column_indexes:
            # Get the model index for the current column
            model_index = self.treeWidget().indexFromItem(self, column_index)

            # Add the model index to the list
            model_indexes.append(model_index)

        # Return the list of model index properties
        return model_indexes

    def get_value(self, column: Union[int, str]) -> Any:
        """Get the value of the item's UserRole data for the given column.

        Args:
            column (Union[int, str]): The column index or name.

        Returns:
            Any: The value of the UserRole data.
        """
        # Get the column index from the column name if necessary
        column_index = self.treeWidget().get_column_index(column) if isinstance(column, str) else column

        # Get the UserRole data for the column
        value = self.data(column_index, QtCore.Qt.ItemDataRole.UserRole)
        # Fallback to the DisplayRole data if UserRole data is None
        value = self.data(column_index, QtCore.Qt.ItemDataRole.DisplayRole) if value is None else value

        return value

    def set_value(self, column: Union[int, str], value: Any):
        """Set the value of the item's UserRole data for the given column.

        Args:
            column (Union[int, str]): The column index or name.
            value (Any): The value to set.
        """
        # Get the column index from the column name if necessary
        column_index = self.treeWidget().get_column_index(column) if isinstance(column, str) else column

        # Set the value for the column in the UserRole data
        self.setData(column_index, QtCore.Qt.ItemDataRole.UserRole, value)

    # Special Methods
    # ---------------
    def __getitem__(self, key: Union[int, str]) -> Any:
        """Get the value of the item's UserRole data for the given column.

        Args:
            key (Union[int, str]): The column index or name.

        Returns:
            Any: The value of the UserRole data.
        """
        # Delegate the retrieval of the value to the `get_value` method
        return self.get_value(key)

    def __lt__(self, other_item: 'TreeWidgetItem') -> bool:
        """Sort the items in the tree widget based on their data.

        Args:
            other_item (TreeWidgetItem): The item to compare with.

        Returns:
            bool: Whether this item is less than the other item.
        """
        # Get the column that is currently being sorted
        column = self.treeWidget().sortColumn()

        # Get the UserRole data for the column for both this item and the other item
        self_data = self.get_value(column)
        other_data = other_item.get_value(column)

        # If the UserRole data is None, fallback to DisplayRole data
        if other_data is None:
            # Get the DisplayRole data for the column of the other item
            other_data = other_item.data(column, QtCore.Qt.ItemDataRole.DisplayRole)

        # If both UserRole data are None, compare their texts
        if self_data is None and other_data is None:
            return self.text(column) < other_item.text(column)

        # If this item's UserRole data is None, it is considered greater
        if self_data is None:
            return True

        # If the other item's UserRole data is None, this item is considered greater
        if other_data is None:
            return False

        try:
            # Try to compare the UserRole data directly
            return self_data < other_data
        except TypeError:
            # If the comparison fails, compare their string representations
            return str(self_data) < str(other_data)

    def __hash__(self):
        return hash(self.id)

class ColumnMangementWidget(QtWidgets.QTreeWidget):

    # Initialization and Setup
    # ------------------------
    def __init__(self, tree_widget: 'GroupableTreeWidget') -> None:
        super().__init__(tree_widget)

        # Store the arguments
        self.tree_widget = tree_widget

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts."""
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setItemsExpandable(False)
        self.setRootIsDecorated(False)

        # Set the minimum width for the first column
        self.header().setMinimumSectionSize(20)
        self.setColumnWidth(0, 20)  # Adjust the size of the first column

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        self.tree_widget.header().sectionMoved.connect(self.update_columns)
        self.tree_widget.model().headerDataChanged.connect(self.update_columns)

        self.itemClicked.connect(self.toggle_check_state)
        self.itemChanged.connect(self.set_column_visibility)

    def toggle_check_state(self, tree_item, column):
        # Toggles the checkbox state when an item's text (second column) is clicked
        if column != 1:
            return

        current_state = tree_item.checkState(0)
        new_state = QtCore.Qt.Checked if current_state == QtCore.Qt.Unchecked else QtCore.Qt.Unchecked
        tree_item.setCheckState(0, new_state)  # Toggle the check state

    def sync_column_order(self):
        for i in range(self.topLevelItemCount()):
            column_name = self.topLevelItem(i).text(1)
            visual_index = self.tree_widget.get_column_visual_index(column_name)
            self.tree_widget.header().moveSection(visual_index, i)

    def set_column_visibility(self, item: QtWidgets.QTreeWidgetItem, column: int):
        column_name = item.text(1)
        is_hidden = item.checkState(0) == QtCore.Qt.Unchecked
        column_index = self.tree_widget.get_column_index(column_name)
        
        self.tree_widget.setColumnHidden(column_index, is_hidden)

    def update_columns(self):
        self.clear()

        if not self.tree_widget.column_name_list:
            return

        logical_indexes = [self.tree_widget.get_column_logical_index(i) for i in range(self.tree_widget.columnCount())]
        header_names = [self.tree_widget.column_name_list[i] for i in logical_indexes]

        self.addItems(header_names)

    def addItem(self, label: str, is_checked: bool = False):
        tree_item = QtWidgets.QTreeWidgetItem(self, ['', label])
        check_state = QtCore.Qt.CheckState.Checked if is_checked else QtCore.Qt.CheckState.Unchecked
        tree_item.setCheckState(0, check_state)

    def addItems(self, labels: Iterable[str]):
        for column_visual_index, label in enumerate(labels):
            column_logical_index = self.tree_widget.get_column_logical_index(column_visual_index)
            is_checked = not self.tree_widget.isColumnHidden(column_logical_index)
            self.addItem(label, is_checked)

    def dropEvent(self, event: QtGui.QDropEvent):
        # Attempt to find the item at the drop position.
        target_item = self.itemAt(event.pos())

        if self.dropIndicatorPosition() == QtWidgets.QAbstractItemView.DropIndicatorPosition.OnItem:

            new_row_index = self.indexFromItem(target_item).row()

            # Perform the move operation within the same level.
            for selected_item in self.selectedItems():
                # Take the item out of its current position.
                taken_item = self.takeTopLevelItem(self.indexOfTopLevelItem(selected_item))
                # Insert it at the determined position.
                self.insertTopLevelItem(new_row_index, taken_item)
            
            event.ignore()
        else:
            # If not reparenting, use the default behavior which is already correct for same-level moves.
            super().dropEvent(event)

        self.sync_column_order()

class TreeUtilityToolBar(QtWidgets.QToolBar):
    def __init__(self, tree_widget: 'GroupableTreeWidget'):
        # Initialize the super class
        super().__init__(parent=tree_widget)

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
        self.tabler_icon = TablerQIcon()

        # Private Attributes
        # ------------------
        ...

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        """
        self.setFixedHeight(24)
        # Create Layouts
        # --------------
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        # Add a stretchable spacer to the toolbar to align items to the left
        spacer = QtWidgets.QWidget(self)
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        # Create Widgets
        # --------------
        self.fit_in_view_button = QtWidgets.QToolButton(self)
        self.fit_in_view_button.setIcon(self.tabler_icon.arrow_autofit_content)
        self.fit_in_view_button.setFixedSize(22, 22)
        self.fit_in_view_button.setToolTip("Fit columns in view")  # Tooltip added

        self.word_wrap_button = QtWidgets.QToolButton(self)
        self.word_wrap_button.setCheckable(True)
        self.word_wrap_button.setIcon(self.tabler_icon.text_wrap)
        self.word_wrap_button.setFixedSize(22, 22)
        self.word_wrap_button.setToolTip("Toggle word wrap")  # Tooltip added

        self.set_uniform_row_height_button = QtWidgets.QToolButton(self)
        self.set_uniform_row_height_button.setCheckable(True)
        self.set_uniform_row_height_button.setIcon(self.tabler_icon.arrow_autofit_height)
        self.set_uniform_row_height_button.setFixedSize(22, 22)
        self.set_uniform_row_height_button.setToolTip("Toggle uniform row height")  # Tooltip added

        self.uniform_row_height_spin_box = QtWidgets.QSpinBox(self)
        self.uniform_row_height_spin_box.setRange(16, 200)
        self.uniform_row_height_spin_box.setFixedHeight(20)
        self.uniform_row_height_spin_box.setSingleStep(4)
        self.uniform_row_height_spin_box.setValue(24)
        self.uniform_row_height_spin_box.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.uniform_row_height_spin_box.setToolTip("Set uniform row height")  # Tooltip added

        self.refresh_button = QtWidgets.QToolButton(self)
        self.refresh_button.setIcon(self.tabler_icon.refresh)
        self.refresh_button.setFixedSize(22, 22)
        self.refresh_button.setToolTip("Refresh tree")

        # Add Widgets to Layouts
        # ----------------------
        self.addWidget(self.fit_in_view_button)
        self.addWidget(self.word_wrap_button)
        self.addWidget(self.set_uniform_row_height_button)
        self.addWidget(self.uniform_row_height_spin_box)
        self.addWidget(self.refresh_button)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.fit_in_view_button.clicked.connect(self.tree_widget.fit_column_in_view)
        self.word_wrap_button.toggled.connect(self.tree_widget.setWordWrap)
        self.set_uniform_row_height_button.toggled.connect(self.toggle_uniform_row_height)
        self.uniform_row_height_spin_box.valueChanged.connect(self.tree_widget.set_row_height)
        # self.refresh_button.clicked.connect(self.tree_widget.refresh)

    def toggle_uniform_row_height(self, state: bool):
        height = self.uniform_row_height_spin_box.value() if state else -1
        self.tree_widget.set_row_height(height)

class GroupableTreeWidget(QtWidgets.QTreeWidget):
    """A QTreeWidget subclass that displays data in a tree structure with the ability to group data by a specific column.

    Attributes:
        column_name_list (List[str]): The list of column names to be displayed in the tree widget.
        groups (Dict[str, TreeWidgetItem]): A dictionary mapping group names to their tree widget items.
        _is_middle_button_pressed (bool): Indicates if the middle mouse button is pressed.
            It's used for scrolling functionality when the middle button is pressed and the mouse is moved.
        _middle_button_prev_pos (QtCore.QPoint): The previous position of the mouse when the middle button was pressed.
        _middle_button_start_pos (QtCore.QPoint): The initial position of the mouse when the middle button was pressed.
        _mouse_move_timestamp (float): The timestamp of the last mouse movement.
    """
    # Set default to index 1, cause of first column willl be "id"
    DEFAULT_DRAG_DATA_COLUMN = 1

    # Signals emitted by the GroupableTreeWidget
    ungrouped_all = QtCore.Signal()
    grouped_by_column = QtCore.Signal(str)

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None):
        # Call the parent class constructor
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        # Attributes
        # ----------
        # Store the current grouped column name
        self.grouped_column_name = str()

        self.column_name_list = list()

        self._drag_data_column = self.DEFAULT_DRAG_DATA_COLUMN

        #
        self.id_to_tree_item = dict()
        self.color_adaptive_columns = list()

        # Initialize the HighlightItemDelegate object to highlight items in the tree widget.
        self.highlight_item_delegate = widgets.HighlightItemDelegate()
        self.thumbnail_delegate = widgets.ThumbnailDelegate(self)

        # Private Attributes
        # ------------------
        # Initialize middle button pressed flag
        self._is_middle_button_pressed = False

        # Previous position of the middle mouse button
        self._middle_button_prev_pos = QtCore.QPoint()
        # Initial position of the middle mouse button
        self._middle_button_start_pos = QtCore.QPoint()

        # Timestamp of the last mouse move event
        self._mouse_move_timestamp = float()

        self._row_height = 24

        self._current_column_index = 0

        self.generator = None
        self._current_task = None

        self.batch_size = 50
        self.threshold_to_fetch_more = 50

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.
        """
        self.setColumnWidth(0, 10)
        self.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)

        # Initializes scroll modes for the widget.
        self.setVerticalScrollMode(QtWidgets.QTreeWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QTreeWidget.ScrollMode.ScrollPerPixel)

        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)

        # Set up the context menu for the header
        self.header().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        # Enable sorting in the tree widget
        self.setSortingEnabled(True)

        self.setWordWrap(True)

        # Enable ExtendedSelection mode for multi-select and set the selection behavior to SelectItems
        self.setSelectionMode(QtWidgets.QTreeWidget.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QTreeWidget.SelectionBehavior.SelectItems)

        # Set the item delegate for highlight search item
        self.setItemDelegate(self.highlight_item_delegate)

        # NOTE: Test
        # self.searchable_header = SearchableHeaderView(self)

        self.set_row_height(self._row_height)
        self._create_header_menu()

        self.data_fetching_buttons = DataFetchingButtons(self)
        self.data_fetching_buttons.hide()
        self.fetch_more_button = self.data_fetching_buttons.fetch_more_button
        self.fetch_all_button = self.data_fetching_buttons.fetch_all_button
        self.stop_fetch_button = self.data_fetching_buttons.stop_fetch_button

        # Position the button and make it hidden by default
        self.position_fetch_more_button()

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signal of header
        self.header().customContextMenuRequested.connect(self._on_header_context_menu)
        
        self.itemExpanded.connect(self.toggle_expansion_for_selected)
        self.itemCollapsed.connect(self.toggle_expansion_for_selected)

        self.header().sortIndicatorChanged.connect(lambda _: self.set_row_height())

        self.itemSelectionChanged.connect(self._highlight_selected_items)

        # NOTE: Fetch more data
        self.fetch_more_button.clicked.connect(self.fetch_more)
        self.fetch_all_button.clicked.connect(self.fetch_all)
        self.stop_fetch_button.clicked.connect(self.stop_fetch)

        # Key Binds
        # ---------
        # Create a shortcut for the copy action and connect its activated signal
        bb.utils.KeyBinder.bind_key(QtGui.QKeySequence.StandardKey.Copy, self, self.copy_selected_cells)

    # Private Methods
    # ---------------
    def _create_header_menu(self):
        """Create a context menu for the header of the tree widget.

        Context Menu:
            +-------------------------------+
            | Grouping                      |
            | - Group by this column        |
            | - Ungroup all                 |
            | ----------------------------- |
            | Visualization                 |
            | - Set Color Adaptive          |
            | - Reset All Color Adaptive    |
            | ----------------------------- |
            | - Fit in View                 |
            | ----------------------------- |
            | Manage Columns                |
            | - Show/Hide Columns >         |
            | - Hide This Column            |
            +-------------------------------+
        """
        # Create the context menu
        self.menu = QtWidgets.QMenu()

        self.add_label_action(self.menu, 'Grouping')

        # Create the 'Group by this column' action and connect it to the 'group_by_column' method. Pass in the selected column as an argument.
        self.group_by_action = self.menu.addAction('Group by this column')
        self.group_by_action.triggered.connect(lambda: self.group_by_column(self._current_column_index))

        # Create the 'Ungroup all' action and connect it to the 'ungroup_all' method
        ungroup_all_action = self.menu.addAction('Ungroup all')
        ungroup_all_action.triggered.connect(self.ungroup_all)

        # Add a separator
        self.menu.addSeparator()

        self.add_label_action(self.menu, 'Visualization')

        # Create the 'Set Color Adaptive' action and connect it to the 'apply_column_color_adaptive' method
        apply_color_adaptive_action = self.menu.addAction('Set Color Adaptive')
        apply_color_adaptive_action.triggered.connect(lambda: self.apply_column_color_adaptive(self._current_column_index))

        # Create the 'Reset All Color Adaptive' action and connect it to the 'reset_all_color_adaptive_column' method
        reset_all_color_adaptive_action = self.menu.addAction('Reset All Color Adaptive')
        reset_all_color_adaptive_action.triggered.connect(self.reset_all_color_adaptive_column)

        # Add a separator
        self.menu.addSeparator()

        # Add the 'Fit in View' action and connect it to the 'fit_column_in_view' method
        fit_column_in_view_action = self.menu.addAction('Fit in View')
        fit_column_in_view_action.triggered.connect(self.fit_column_in_view)

        # Add a separator
        self.menu.addSeparator()

        self.add_label_action(self.menu, 'Manage Columns')
        show_hide_column = self.menu.addMenu('Show/Hide Columns')
        self.menu.addMenu(show_hide_column)

        self.column_list_widget = ColumnMangementWidget(self)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(self.column_list_widget)
        show_hide_column.addAction(action)

        hide_this_column = self.menu.addAction('Hide This Column')
        hide_this_column.triggered.connect(lambda: self.hideColumn(self._current_column_index))

    def _on_header_context_menu(self, pos: QtCore.QPoint) -> None:
        """Show a context menu for the header of the tree widget.

        Args:
            pos (QtCore.QPoint): The position where the right click occurred.
        """
        # Get the index of the column where the right click occurred
        self._current_column_index = self.header().logicalIndexAt(pos)

        # Disable 'Group by this column' on the first column
        if not self._current_column_index:
            self.group_by_action.setDisabled(True)
        else:
            self.group_by_action.setDisabled(False)

        # Show the context menu
        self.menu.popup(QtGui.QCursor.pos())

    def _create_item_groups(self, data: List[str]) -> Dict[str, List[TreeWidgetItem]]:
        """Group the data into a dictionary mapping group names to lists of tree items.

        Args:
            data (List[str]): The data to be grouped.

        Returns:
            Dict[str, List[TreeWidgetItem]]: A dictionary mapping group names to lists of tree items.
        """
        # Create a dictionary to store the groups
        groups = {}

        # Group the data
        for i, item_data in enumerate(data):
            # If the data is empty, add it to the '_others' group
            if not item_data:
                item_data = '_others'

            # Add the tree item to the appropriate group
            item = self.topLevelItem(i)
            if item_data in groups:
                groups[item_data].append(item)
            else:
                groups[item_data] = [item]

        return groups

    def _apply_scroll_momentum(self, velocity: QtCore.QPointF, momentum_factor: float = 0.5) -> None:
        """Applies momentum to the scroll bars based on the given velocity.

        Args:
            velocity (QtCore.QPointF): The velocity of the mouse movement.
            momentum_factor (float, optional): The factor to control the momentum strength. Defaults to 0.5.
        """
        # Calculate horizontal and vertical momentum based on velocity and momentum factor
        horizontal_momentum = int(velocity.x() * momentum_factor)
        vertical_momentum = int(velocity.y() * momentum_factor)

        # Scroll horizontally and vertically with animation using the calculated momenta
        self._animate_scroll(self.horizontalScrollBar(), horizontal_momentum)
        self._animate_scroll(self.verticalScrollBar(), vertical_momentum)

    def _animate_scroll(self, scroll_bar: QtWidgets.QScrollBar, momentum: int) -> None:
        """Animates the scrolling of the given scroll bar to the target value over the specified duration.

        Args:
            scroll_bar (QtWidgets.QScrollBar): The scroll bar to animate.
            momentum (int): The momentum value to scroll.
        """
        # Get the current value of the scroll bar
        current_value = scroll_bar.value()
        # Calculate the target value by subtracting the momentum from the current value
        target_value = current_value - momentum

        # Calculate the duration of the animation based on the absolute value of the momentum
        duration = min(abs(momentum) * 20, 500)

        # Get the start time of the animation
        start_time = time.time()

        def _perform_scroll_animation():
            """Animates the scrolling of the given scroll bar to the target value over the specified duration.

            The animation interpolates the scroll bar value from the current value to the target value based on the elapsed time.
            """
            # Access the current_value variable from the enclosing scope
            nonlocal current_value

            # Stop the animation if the middle mouse button is pressed
            if self._is_middle_button_pressed:
                return

            # Calculate the elapsed time since the start of the animation
            elapsed_time = int((time.time() - start_time) * 1000)

            # Check if the elapsed time has reached the duration
            if elapsed_time >= duration:
                # Animation complete
                scroll_bar.setValue(target_value)
                return

            # Calculate the interpolated value based on elapsed time and duration
            progress = elapsed_time / duration
            interpolated_value = int(current_value + (target_value - current_value) * progress)

            # Update the scroll bar value and schedule the next animation frame
            scroll_bar.setValue(interpolated_value)
            QtCore.QTimer.singleShot(10, _perform_scroll_animation)

        # Start the animation
        _perform_scroll_animation()

    def _highlight_selected_items(self):
        """Highlight the specified `tree_items` in the tree widget.
        """
        self.highlight_item_delegate.target_selected_model_indexes.clear()
        tree_items = self.selectedItems()
        # Loop through the specified tree items
        for tree_item in tree_items:

            # Add the model indexes of the current tree item to the target properties
            self.highlight_item_delegate.target_selected_model_indexes.extend(tree_item.get_model_indexes())

        self.update()

    # Extended Methods
    # ----------------
    def create_thumbnail_column(self, column_name: str):

        self.column_name_list.append('thumbnail')
        self.setHeaderLabels(self.column_name_list)

        source_column = self.column_name_list.index(column_name)
        thumbnail_column = self.column_name_list.index('thumbnail')

        self.thumbnail_delegate.set_thumbnail_column(thumbnail_column)
        self.thumbnail_delegate.set_source_column(source_column)

        self.setItemDelegateForColumn(thumbnail_column, self.thumbnail_delegate)

    def add_label_action(self, parent_menu: QtWidgets.QMenu, text: str):
        label = QtWidgets.QLabel(text, parent_menu)
        label.setDisabled(True)
        label.setStyleSheet(
            'color: rgb(144, 144, 144); padding: 6px;'
        )

        action = QtWidgets.QWidgetAction(parent_menu)
        action.setDefaultWidget(label)

        parent_menu.addAction(action)

    def show_items(self, items: List[QtWidgets.QTreeWidgetItem]):
        """Show the items and their parent and children.
        """
        # Show the items that match all filter criteria
        for item in items:
            item.setHidden(False)

            # Show the parent of the item if it exists
            if item.parent():
                item.parent().setHidden(False)

            # Show all children of the item
            for index in range(item.childCount()):
                item.child(index).setHidden(False)

    def show_all_items(self):
        # Get a list of all items in the tree widget
        all_items = self.get_all_items()

        # Show all items
        for item in all_items:
            item.setHidden(False)

    def hide_all_items(self):
        # Get a list of all items in the tree widget
        all_items = self.get_all_items()

        # Hide all items
        for item in all_items:
            item.setHidden(True)

    def highlight_items(self, tree_items: List['TreeWidgetItem'], focused_column_index = None):
        """Highlight the specified `tree_items` in the tree widget.
        """
        # Loop through the specified tree items
        for tree_item in tree_items:
            # Add the model indexes of the current tree item to the target properties
            self.highlight_item_delegate.target_model_indexes.extend(tree_item.get_model_indexes())

            if focused_column_index is None:
                continue

            focused_model_index = self.indexFromItem(tree_item, focused_column_index)
            self.highlight_item_delegate.target_focused_model_indexes.append(focused_model_index)

        self.update()

    def clear_highlight(self):
        # Reset the highlight for all items
        self.highlight_item_delegate.clear()
        self.update()

    # NOTE: for refactoring
    def set_row_height(self, height: Optional[int] = None):
        self._row_height = height or self._row_height

        if self._row_height == -1:
            self.reset_row_height()
            return

        if not self.topLevelItem(0):
            return

        self.setUniformRowHeights(True)

        for column_index in range(self.columnCount()):
            size_hint = self.sizeHintForColumn(column_index)
            self.topLevelItem(0).setSizeHint(column_index, QtCore.QSize(size_hint, self._row_height))

    def reset_row_height(self):

        if not self.topLevelItem(0):
            return

        self.setUniformRowHeights(False)

        for column_index in range(self.columnCount()):
            size_hint = self.sizeHintForColumn(column_index)
            self.topLevelItem(0).setSizeHint(column_index, QtCore.QSize(size_hint, -1))

    def toggle_expansion_for_selected(self, item):
        """Toggles the expansion state of selected items.

        Args:
            item: The clicked item whose expansion state will be used as a reference.

        Returns:
            None.
        """
        # Get the currently selected items
        selected_items = self.selectedItems()

        # If no items are selected, return early
        if not selected_items:
            return

        # Set the expanded state of all selected items to match the expanded state of the clicked item
        for i in selected_items:
            i.setExpanded(item.isExpanded())

    def get_column_value_range(self, column: int, child_level: int = 0) -> Tuple[Optional[Number], Optional[Number]]:
        """Get the value range of a specific column at a given child level.

        Args:
            column (int): The index of the column.
            child_level (int): The child level to calculate the range for. Defaults to 0 (top-level items).

        Returns:
            Tuple[Optional[Number], Optional[Number]]: A tuple containing the minimum and maximum values,
            or (None, None) if no valid values are found.
        """
        # Get the items at the specified child level
        items = bb.utils.TreeUtil.get_items_at_child_level(self, child_level)

        # Collect the values from the specified column in the items
        values = [
            item.get_value(column)
            for item in items
            if isinstance(item.get_value(column), Number)
        ]

        # If there are no valid values, return None
        if not values:
            return None, None

        # Calculate the minimum and maximum values
        min_value = min(*values)
        max_value = max(*values)

        # Return the value range
        return min_value, max_value

    def apply_column_color_adaptive(self, column: int):
        """Apply adaptive color mapping to a specific column at the appropriate child level determined by the group column.

        This method calculates the minimum and maximum values of the column at the appropriate child level determined by the group column
        and applies an adaptive color mapping based on the data distribution within the column.
        The color mapping dynamically adjusts to the range of values.

        Args:
            column (int): The index of the column to apply the adaptive color mapping.
        """
        self.color_adaptive_columns.append(column)

        # Determine the child level based on the presence of a grouped column
        child_level = 1 if self.grouped_column_name else 0

        # Calculate the minimum and maximum values of the column at the determined child level
        min_value, max_value = self.get_column_value_range(column, child_level)

        # Create and set the adaptive color mapping delegate for the column
        delegate = widgets.AdaptiveColorMappingDelegate(self, min_value, max_value)
        self.setItemDelegateForColumn(column, delegate)

    def reset_all_color_adaptive_column(self):
        """Reset the color adaptive for all columns in the tree widget.
        """
        for column in self.color_adaptive_columns:
            self.setItemDelegateForColumn(column, None)

        self.color_adaptive_columns.clear()

    def get_column_index(self, column_name: str) -> int:
        """Retrieves the index of the specified column name.

        Args:
            column_name: The name of the column.

        Returns:
            int: The index of the column if found.

        Raises:
            ValueError: If the column name is not found.
        """
        # Check if the column name is not in the column_name_list
        if column_name not in self.column_name_list:
            # Raise an exception with a descriptive error message
            raise ValueError(f"Invalid column name: {column_name}")

        # Return the index of the column if found
        return self.column_name_list.index(column_name)

    def get_column_visual_index(self, column: Union[str, int]) -> int:
        """
        """
        if isinstance(column, str):
            column = self.get_column_index(column)

        #
        return self.header().visualIndex(column)

    def get_column_logical_index(self, visual_index: int) -> int:
        return self.header().logicalIndex(visual_index)

    def add_items(self, item_names: Union[Dict[str, List[str]], List[str]], parent: Optional[QtWidgets.QTreeWidgetItem] = None):
        """Adds items to the tree widget.

        Args:
            item_names (Union[Dict[str, List[str]], List[str]]): If a dictionary is provided, it represents parent-child relationships where keys are parent item names and values are lists of child item names. If a list is provided, it contains item names to be added at the root level.
        """
        if isinstance(item_names, dict):
            self._add_items_from_id_to_data_dict(item_names, parent)
        elif isinstance(item_names, list):
            self._add_items_from_data_dicts(item_names, parent)
        else:
            raise ValueError("Invalid type for item_names. Expected a list or a dictionary.")

    def add_item(self, data_dict, item_id=None, parent=None):
        # Capture the current first top-level item, if any
        previous_first_item = self.topLevelItem(0) if self.topLevelItemCount() > 0 else None
        
        parent = parent or self.invisibleRootItem()
        item_id = item_id or uuid.uuid1()
        
        # Create a new TreeWidgetItem and add to the tree widget
        tree_item = TreeWidgetItem(parent, item_data=data_dict, item_id=item_id)
        self.id_to_tree_item[item_id] = tree_item

        # Check the current first top-level item after the potential sort
        current_first_item = self.topLevelItem(0)

        # If the first item has changed (by comparing object references), emit the signal
        if current_first_item != previous_first_item:
            self.set_row_height()

        return tree_item

    def _add_items_from_id_to_data_dict(self, id_to_data_dict: Dict[str, Dict[str, Any]],  parent: Optional[QtWidgets.QTreeWidgetItem]):
        """Add items to the tree widget.

        Args:
            id_to_data_dict (Dict[int, Dict[str, str]]): A dictionary mapping item IDs to their data as a dictionary.
        """
        # Iterate through the dictionary of items
        for item_id, data_dict in id_to_data_dict.items():
            # Create a new custom QTreeWidgetItem for sorting by type of the item data, and add to the self tree widget
            self.add_item(data_dict, item_id, parent)

    # TODO: Handle id or primary key
    def _add_items_from_data_dicts(self, data_dicts: List[str], parent: Optional[QtWidgets.QTreeWidgetItem] = None):
        """Adds items to the tree widget at the root level from a list of item names.

        Args:
            item_list (List[str]): A list of item names to be added at the root level.
        """
        ...
        for data_dict in data_dicts:
            self.add_item(data_dict)

    def group_by_column(self, column: Union[int, str]) -> None:
        """Group the items in the tree widget by the values in the specified column.

        Args:
            column (int): The index of the column to group by.
        """
        if not isinstance(column, int):
            column = self.get_column_index(column)

        # Ungroup all items in the tree widget
        self.ungroup_all()

        # Hide the grouped column
        self.setColumnHidden(column, True)

        # Get the label for the column that we want to group by and the label for the first column 
        self.grouped_column_name = self.headerItem().text(column)
        first_column_label = self.headerItem().text(0)
        
        # Rename the first column
        self.setHeaderLabel(f'{self.grouped_column_name} / {first_column_label}')
        
        # Get the data for each tree item in the column
        data = [self.topLevelItem(row).data(column, QtCore.Qt.ItemDataRole.UserRole) for row in range(self.topLevelItemCount())]
        
        # Group the data and add the tree items to the appropriate group
        groups = self._create_item_groups(data)

        # Iterate through each group and its items
        for group_name, items in groups.items():
            # Create a new QTreeWidgetItem for the group
            group_item = TreeWidgetItem(self, [group_name])
            
            # Add the items to the group item as children
            for item in items:
                # Save the original parent and position of the tree item
                original_parent = item.parent()
                original_row = original_parent.indexOfChild(item) if original_parent else self.indexOfTopLevelItem(item)

                # Remove the tree item from its original parent
                if original_parent:
                    original_parent.takeChild(original_row)
                else:
                    self.takeTopLevelItem(original_row)

                # Add the tree item to the group item as a child and restore its original position
                group_item.addChild(item)
            
        # Expand all items
        self.expandAll()

        # Resize first columns to fit their contents
        self.resizeColumnToContents(0)

        # Emit signal for grouped by column with column name
        self.grouped_by_column.emit(self.grouped_column_name)
        
    def fit_column_in_view(self) -> None:
        """Adjust the width of all columns to fit the entire view.
    
            This method resizes columns so that their sum is equal to the width of the view minus the width of the vertical scroll bar. 
            It starts by reducing the width of the column with the largest width by 10% until all columns fit within the expected width.
        """
        # Resize all columns to fit their contents
        self.resize_to_contents()
        
        # Get the expected width of the columns (the width of the view minus the width of the scroll bar)
        expect_column_width = self.size().width() - self.verticalScrollBar().width()
        # Calculate the sum of the current column widths
        column_width_sum = sum(self.columnWidth(column) for column in range(self.columnCount()))
        
        # Loop until all columns fit within the expected width
        while column_width_sum > expect_column_width:
            # Find the column with the largest width
            largest_column = max(range(self.columnCount()), key=lambda x: self.columnWidth(x))
            # Reduce the width of the largest column by 10%
            new_width = max(self.columnWidth(largest_column) - expect_column_width // 10, 0)
            self.setColumnWidth(largest_column, new_width)
            # Update the sum of the column widths
            column_width_sum -= self.columnWidth(largest_column) - new_width

    def resize_to_contents(self) -> None:
        """Resize all columns in the object to fit their contents.
        """
        # Iterate through all columns
        for column_index in range(self.columnCount()):  
            # Resize the column to fit its contents
            self.resizeColumnToContents(column_index) 

    def ungroup_all(self) -> None:
        """Ungroup all the items in the tree widget.
        """
        # Return if there are no groups to ungroup
        if not self.grouped_column_name:
            return

        # Reset the header label
        self.setHeaderLabel(self.column_name_list[0])
        
        # Show hidden column
        column_index = self.get_column_index(self.grouped_column_name)
        self.setColumnHidden(column_index, False)

        # Get a list of all the top-level items in the tree widget
        group_item_list = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]

        # Iterate through all the top-level items in the tree widget
        for group_item in group_item_list:

            # Remove all of its children and add them as top-level items
            child_items = group_item.takeChildren()
            self.addTopLevelItems(child_items)

            # Remove the group item from the top-level items
            self.takeTopLevelItem(self.indexOfTopLevelItem(group_item))

        # Clear the grouped column label
        self.grouped_column_name = str()

        # Resize first columns to fit their contents
        self.resizeColumnToContents(0)

        # Emit signal for ungrouped all
        self.ungrouped_all.emit()

    def get_all_items(self) -> List[TreeWidgetItem]:
        """This function returns all the items in the tree widget as a list.

        The items are sorted based on their order in the tree structure, 
        with children appearing after their parent items for each grouping.

        Returns:
            List[TreeWidgetItem]: A list containing all the items in the tree widget.
        """
        return bb.utils.TreeUtil.get_child_items(self)

    def copy_selected_cells(self):
        # NOTE: For refactoring
        #
        #
        model = self.selectionModel()
        model_indexes = model.selectedIndexes()

        all_items = self.get_all_items()
        # Sort the cells based on their global row and column
        sorted_indexes = sorted(
            model_indexes, 
            key=lambda model_index: (
                all_items.index(self.itemFromIndex(model_index)),
                model_index.column()
                )
            )

        cell_dict = dict()
        column_set = set()

        for model_index in sorted_indexes:
            tree_item = self.itemFromIndex(model_index)

            global_row = all_items.index(tree_item)
            column = model_index.column()

            cell_value = tree_item.get_value(column)
            cell_text = str() if cell_value is None else str(cell_value)
            cell_text = f'"{cell_text}"' if '\t' in cell_text or '\n' in cell_text else cell_text

            cell_dict.setdefault(global_row, dict())
            cell_dict[global_row][column] = cell_text
            column_set.add(column)

        for row_dict in cell_dict.values():
            for column in column_set:
                row_dict.setdefault(column, str())

        row_texts = list()
        for row_dict in cell_dict.values():
            row_text = '\t'.join(row_dict[column] for column in sorted(column_set))
            row_texts.append(row_text)

        full_text = '\n'.join(row_texts)

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(full_text)

        # Show tooltip message
        self.show_tool_tip(f'Copied:\n{full_text}', 5000)

    def show_tool_tip(self, text: str, msc_show_time: Number = 1000):
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text, self, QtCore.QRect(), msc_show_time)

    def paste_cells_from_clipboard(self):
        # NOTE: Further Implementation Required
        # TODO: Implement popup window to be confirm paste data on each columns.
        #
        model = self.selectionModel()
        model_indexes = model.selectedIndexes()

        # Get the text from the clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()
        
        # Split the text into rows and columns
        rows = text.split('\n')
        rows = [row.split('\t') for row in rows]

        # Get the current selected item

        # Get the current row and column

        # Paste the values into the tree widget

        print('Not implement')

    def set_drag_data_column(self, column: Union[int, str]):
        # Get the column index from the column name if necessary
        column_index = self.get_column_index(column) if isinstance(column, str) else column
        self._drag_data_column = column_index

    def create_drag_pixmap(self, items_count, opacity: float = 0.8, badge_radius: int = 10, badge_margin: int = 0):
        # Get the application icon and create a pixmap from it
        icon = QtWidgets.QApplication.instance().windowIcon()
        if icon.isNull():
            icon_pixmap = QtGui.QPixmap(24, 16)
            icon_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        else:
            icon_pixmap = icon.pixmap(64, 64)

        # Create a transparent pixmap
        pixmap = QtGui.QPixmap(icon_pixmap.width() + badge_margin, icon_pixmap.height() + badge_margin)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setOpacity(opacity)
        painter.drawPixmap(QtCore.QPoint(0, badge_margin), icon_pixmap)

        # Draw badge logic
        items_count_text = "99+" if items_count > 99 else str(items_count)

        # Calculate the optimal badge radius and diameter
        metrics = QtGui.QFontMetrics(painter.font())
        text_width = metrics.width(items_count_text)
        badge_radius = max(badge_radius, int(text_width / 2))
        badge_diameter = badge_radius * 2

        painter.setBrush(QtGui.QColor('red'))
        painter.setPen(QtGui.QColor('white'))
        painter.drawEllipse(pixmap.width() - badge_diameter - 2, 0, badge_diameter, badge_diameter)
        painter.drawText(pixmap.width() - badge_diameter - 2, 0, badge_diameter, badge_diameter, 
                         QtCore.Qt.AlignmentFlag.AlignCenter, items_count_text)

        painter.end()

        return pixmap

    # Event Handling or Override Methods
    # ----------------------------------
    def setHeaderLabels(self, labels: Iterable[str]):
        """Set the names of the columns in the tree widget.

        Args:
            labels (Iterable[str]): The iterable of column names to be set.
        """
        # Store the column names for later use
        self.column_name_list = labels

        # Set the number of columns and the column labels
        self.setColumnCount(len(self.column_name_list))
        super().setHeaderLabels(self.column_name_list)

    def hideColumn(self, column: Union[int, str]):
        column_index = self.get_column_index(column) if isinstance(column, str) else column
        super().hideColumn(column_index)

    def startDrag(self, supported_actions: QtCore.Qt.DropActions):
        """Handles drag event of tree widget
        """
        items = self.selectedItems()

        if not items:
            return
        
        mime_data = QtCore.QMimeData()

        # Set mime data in format 'text/plain'
        texts = [item.text(self._drag_data_column) for item in items]
        text = '\n'.join(texts)
        mime_data.setText(text)

        # Set mime data in format 'text/uri-list'
        urls = [QtCore.QUrl.fromLocalFile(text) for text in texts]
        mime_data.setUrls(urls)

        # Create drag icon pixmap with badge
        drag_pixmap = self.create_drag_pixmap(len(items))

        # Set up the drag operation with the semi-transparent pixmap
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(drag_pixmap)
        drag.exec_(supported_actions)

    def clear(self):
        self.id_to_tree_item.clear()
        super().clear()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse press event.
        
        Overrides the parent class method to handle the event where the middle mouse button is pressed.
        If the middle button is pressed, sets the cursor to SizeAllCursor.
        
        Args:
            event: The mouse event.
        """
        # Check if middle mouse button is pressed
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            # Set middle button press flag to True
            self._is_middle_button_pressed = True
            # Record the initial position where mouse button is pressed
            self._middle_button_start_pos = event.pos()
            # Change the cursor to SizeAllCursor
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        else:
            # If not middle button, call the parent class method to handle the event
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse release event.
        
        Overrides the parent class method to handle the event where the middle mouse button is released.
        If the middle button is released, restores the cursor to the default.
        
        Args:
            event: The mouse event.
        """
        # Check if middle mouse button is released
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            # Set middle button press flag to False
            self._is_middle_button_pressed = False
            # Calculate the velocity based on the change in mouse position and the elapsed time
            # NOTE: The + 0.01 is added to avoid division by zero
            velocity = (event.pos() - self._middle_button_prev_pos) / ((time.time() - self._mouse_move_timestamp + 0.01))
            # Apply momentum based on velocity
            self._apply_scroll_momentum(velocity)
            # Restore the cursor to default
            QtWidgets.QApplication.restoreOverrideCursor()
        else:
            # If not middle button, call the parent class method to handle the event
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse move event.
        
        Overrides the parent class method to handle the event where the mouse is moved.
        If the middle button is pressed, adjusts the scroll bar values according to the mouse movement.
        
        Args:
            event: The mouse event.
        """
        # Check if middle mouse button is pressed
        if self._is_middle_button_pressed:
            # Calculate the change in mouse position
            delta = event.pos() - self._middle_button_start_pos

            # Get the scroll bars
            horizontal_scroll_bar = self.horizontalScrollBar()
            vertical_scroll_bar = self.verticalScrollBar()

            # Adjust the scroll bar values according to mouse movement
            horizontal_scroll_bar.setValue(horizontal_scroll_bar.value() - int(delta.x()))
            vertical_scroll_bar.setValue(vertical_scroll_bar.value() - int(delta.y()))

            # Update the previous and start positions of the middle mouse button
            self._middle_button_prev_pos = self._middle_button_start_pos
            self._middle_button_start_pos = event.pos()

            # Set the timestamp of the last mouse move event
            self._mouse_move_timestamp = time.time()
        else:
            # If middle button is not pressed, call the parent class method to handle the event
            super().mouseMoveEvent(event)

    def save_state(self, settings: QtCore.QSettings, group_name='tree_widget'):
        settings.beginGroup(group_name)
        settings.setValue('header_state', self.header().saveState())
        # TODO: Store self.color_adaptive_columns when apply color adaptive
        settings.setValue('color_adaptive_columns', self.color_adaptive_columns)
        settings.setValue('group_column_name', self.grouped_column_name)
        settings.setValue('uniform_row_height', self._row_height)
        settings.endGroup()

    def load_state(self, settings: QtCore.QSettings, group_name='tree_widget'):
        settings.beginGroup(group_name)
        header_state = settings.value('header_state', QtCore.QByteArray)
        color_adaptive_columns = settings.value('color_adaptive_columns', list())
        grouped_column_name = settings.value('grouped_column_name', str())
        uniform_row_height = int(settings.value('uniform_row_height', -1))
        settings.endGroup()

        if not header_state:
            return

        self.header().restoreState(header_state)
        self._restore_color_adaptive_column(color_adaptive_columns)
        self.group_by_column(grouped_column_name)
        self.set_row_height(uniform_row_height)

    def set_generator(self, generator: Generator):
        self.clear()

        # Clear old task
        if self._current_task is not None:
            self._current_task.stop()
            self._current_task = None

        self.generator = generator

        if not self.generator:
            return

        self.verticalScrollBar().valueChanged.connect(self._check_scroll_position)

        first_batch_size = self.calculate_dynamic_batch_size()

        # NOTE: Fetch more data
        self.data_fetching_buttons.show()
        self._fetch_more_data(first_batch_size)

    def _restore_color_adaptive_column(self, columns):
        self.reset_all_color_adaptive_column()

        for column in columns:
            self.apply_column_color_adaptive(column)

    def _fetch_more_data(self, batch_size: int = None):
        if self._current_task is not None:
            return

        if batch_size:
            items_to_fetch = islice(self.generator, batch_size)
        else:
            items_to_fetch = self.generator

        # Create the self._current_task
        self._current_task = GeneratorWorker(items_to_fetch)
        # Connect signals to slots for handling placeholders and real data
        self._current_task.result.connect(self.add_item)
        # NOTE: Fetch more data button
        self._current_task.started.connect(self.show_fetching_indicator)  # Optional: Show a fetching indicator
        self._current_task.finished.connect(self.show_fetch_buttons)

        self._current_task.loaded_all.connect(self._disconnect_check_scroll_possition)
        self._current_task.loaded_all.connect(self.data_fetching_buttons.hide)
        # Start the self._current_task using ThreadPoolManager
        ThreadPoolManager.thread_pool().start(self._current_task.run)

    def _disconnect_check_scroll_possition(self):
        try:
            self.verticalScrollBar().valueChanged.disconnect(self._check_scroll_position)
        except TypeError:
            pass

    def _check_scroll_position(self, value):
        """Checks the scroll position and fetchs more data if the threshold is reached."""
        scroll_bar = self.verticalScrollBar()
        if value >= scroll_bar.maximum() - self.threshold_to_fetch_more:
            self._fetch_more_data(self.batch_size)

    def calculate_dynamic_batch_size(self):
        """Estimates the number of items that can fit in the current view.

        Returns:
            int: Estimated number of items that can fit in the view.
        """
        # Add a temporary item to calculate its size
        temp_item = QtWidgets.QTreeWidgetItem(["Temporary Item"])
        self.addTopLevelItem(temp_item)
        item_height = self.visualItemRect(temp_item).height()
        # Remove the temporary item
        self.takeTopLevelItem(0)

        # Calculate the visible area height
        visible_height = self.viewport().height()

        # Calculate and return the number of items that can fit in the view
        estimated_items = (visible_height // item_height) + 1 if item_height > 0 else self.batch_size
        
        # Adjust the batch size based on the estimate
        # You may want to add some buffer (e.g., 10% more items) to ensure the view is fully populated
        return max(estimated_items, self.batch_size)

    def stop_fetch(self):
        # Assuming `current_task` is your currently running FetchDataTask instance
        if self._current_task:
            self._current_task.stop()

    # NOTE: Fetch more data button
    def fetch_more(self):
        # Fetch more data
        self._fetch_more_data(self.batch_size)

    def fetch_all(self):
        # Fetch more data
        self._fetch_more_data()

    def show_fetching_indicator(self):
        # Position and show the fetching indicator
        self.fetch_more_button.hide()
        self.fetch_all_button.hide()
        self.stop_fetch_button.show()

    def show_fetch_buttons(self):
        # Once fetching is finished, change the button text back to "Fetch More" and enable it
        self.fetch_more_button.show()
        self.fetch_all_button.show()
        self.stop_fetch_button.hide()
        self._current_task = None

    def position_fetch_more_button(self):
        if self.data_fetching_buttons.isHidden():
            return

        # Position the Fetch More button at the center bottom of the tree widget
        x = (self.width() - self.data_fetching_buttons.width()) / 2
        y = self.height() - self.data_fetching_buttons.height() - 30  # 10 pixels from the bottom

        self.data_fetching_buttons.move(int(x), int(y))

    def resizeEvent(self, event):
        # Override resize event to reposition the Fetch More button when the widget is resized
        self.position_fetch_more_button()
        super().resizeEvent(event)


# Main Function
# -------------
def main():
    """Create the application and main window, and show the widget.
    """
    import sys
    from blackboard.examples.example_data_dict import COLUMN_NAME_LIST, ID_TO_DATA_DICT
    from blackboard.examples.example_generator import generate_file_paths

    # Create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    # NOTE: Test window icon
    app.setWindowIcon(QtGui.QIcon('image_not_available_placeholder.png'))

    # Set theme of QApplication to the dark theme
    bb.theme.set_theme(app, 'dark')

    # Create an instance of the widget
    generator = generate_file_paths('blackboard', delay_duration_sec=0.05)
    tree_widget = GroupableTreeWidget()
    tree_widget.setHeaderLabels(['id', 'file_path'])
    tree_widget.create_thumbnail_column('file_path')
    tree_widget.set_generator(generator)

    # tree_widget = GroupableTreeWidget(column_name_list=COLUMN_NAME_LIST)
    # tree_widget.add_items(ID_TO_DATA_DICT)

    # Show the window and run the application
    tree_widget.show()

    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
