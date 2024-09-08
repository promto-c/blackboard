# Type Checking Imports
# ---------------------
from typing import Any, Dict, List, Union, Tuple, Optional, Generator, Iterable

# Standard Library Imports
# ------------------------
import uuid
from numbers import Number
from itertools import islice
from collections import defaultdict
from functools import partial

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
from blackboard.utils.tree_utils import TreeUtil, TreeItemUtil
from blackboard.widgets.button import DataFetchingButtons
from blackboard.widgets.menu import ContextMenu
from blackboard.widgets.momentum_scroll_widget import MomentumScrollTreeWidget


# Class Definitions
# -----------------
class TreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """Extend QTreeWidgetItem to handle various data formats and store additional data in the user role.

    Attributes:
        id (Any): The ID of the item.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: Union[QtWidgets.QTreeWidget, QtWidgets.QTreeWidgetItem], 
                 item_data: Union[Dict[str, Any], List[Any]] = None, item_id: Any = None):
        """Initialize with the given parent and item data.

        Args:
            parent (Union[QtWidgets.QTreeWidget, QtWidgets.QTreeWidgetItem]): Parent widget or item.
            item_data (Union[Dict[str, Any], List[str]], optional): Data for the item, as a list of values or a dictionary with keys matching the headers of the parent widget. Defaults to `None`.
            item_id (Any, optional): The ID of the item. Defaults to `None`.
        """
        # Store the item's ID
        self.id = item_id

        # Determine the format of the data (list or dict) and prepare it for the item
        if isinstance(item_data, list):
            item_values = item_data
        elif isinstance(item_data, dict):
            # Retrieve column names from the parent widget
            column_names = TreeUtil.get_column_names(parent)
            # Match data to columns
            item_values = [item_data.get(column, '') for column in column_names]

        # Call superclass constructor to initialize the item with formatted data
        super().__init__(parent, map(self._convert_to_str, item_values))

        # Set the UserRole data for the item.
        self._set_user_role_data(item_values)

    def _convert_to_str(self, value: Any) -> str:
        """Convert a given value to a string, decoding bytes if necessary.

        Args:
            value (Any): The value to convert to a string.

        Returns:
            str: The string representation of the value.
        """
        if isinstance(value, bytes):
            return value.hex()

        return str(value)

    # Public Methods
    # --------------
    def get_value(self, column: Union[int, str], data_role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.UserRole) -> Any:
        """Retrieves the value for the specified column and role.

        Args:
            column (Union[int, str]): Column index or name.
            data_role (QtCore.Qt.ItemDataRole, optional): Data role to retrieve. Defaults to UserRole.

        Returns:
            Any: The value associated with the column and role.
        """
        # Get the column index from the column name if necessary
        column_index = self.treeWidget().get_column_index(column) if isinstance(column, str) else column

        # Get the data for the specified role and column
        value = self.data(column_index, data_role) or self.data(column_index, QtCore.Qt.ItemDataRole.DisplayRole)

        return value

    def set_value(self, column: Union[int, str], value: Any, data_role: Optional[QtCore.Qt.ItemDataRole] = None):
        """Set the value for the specified column and role.

        Args:
            column (Union[int, str]): Column index or name.
            value (Any): Value to set.
            data_role (QtCore.Qt.ItemDataRole, optional): Role under which to set the value. Defaults to UserRole.
        """
        # Get the column index from the column name if necessary
        column_index = self.treeWidget().get_column_index(column) if isinstance(column, str) else column

        # Set the value for the specified role and column
        if data_role is None:
            # Set both UserRole and DisplayRole data
            self.setData(column_index, QtCore.Qt.ItemDataRole.UserRole, value)
            self.setData(column_index, QtCore.Qt.ItemDataRole.DisplayRole, self._convert_to_str(value))

            # Special handling for lists and booleans
            if isinstance(value, list):
                self._set_tag_list_view(column_index, value)
            elif isinstance(value, bool):
                check_state = QtCore.Qt.CheckState.Checked if value else QtCore.Qt.CheckState.Unchecked
                self.setData(column_index, QtCore.Qt.ItemDataRole.CheckStateRole, check_state)
        else:
            # Set data for the specified role
            self.setData(column_index, data_role, value)

    # Private Methods
    # ---------------
    def _set_user_role_data(self, item_values: List[Any]):
        """Set the UserRole data for the item.

        Args:
            item_values (List[Any]): The list of values to set as the item's data.
        """
        # Iterate through each column and set its value in the UserRole data
        for column_index, value in enumerate(item_values):
            self.set_value(column_index, value, QtCore.Qt.ItemDataRole.UserRole)

    def _set_tag_list_view(self, column_index: int, values: List[str]):
        """Set up a TagListView with the given list of tags and assign it to the specified column.

        Args:
            column_index (int): The column index where the TagListView will be set.
            values (List[str]): The list of tags to populate the TagListView.
        """
        # Create the TagListView widget
        tag_list_view = widgets.TagListView(self.treeWidget(), read_only=True)
        tag_list_view.add_items(values)

        # NOTE: Workaround
        tag_list_view.sizeHint = partial(self.sizeHint, column_index)
        # Set the TagListView as the widget for the specified item and column
        self.treeWidget().setItemWidget(self, column_index, tag_list_view)

    def __getitem__(self, key: Union[int, str]) -> Any:
        """Retrieve the value of the UserRole data for the given column.

        Args:
            key (Union[int, str]): Column index or name.

        Returns:
            Any: The value stored under UserRole.
        """
        return self.get_value(key)

    def __lt__(self, other_item: 'TreeWidgetItem') -> bool:
        """Compare this item with another item to determine the sort order.

        Args:
            other_item (TreeWidgetItem): Item to compare against.

        Returns:
            bool: True if this item is less than the other item, False otherwise.
        """
        # Get the column that is currently being sorted
        column = self.treeWidget().sortColumn()

        # Get the UserRole data for the column for both this item and the other item
        self_data = self.get_value(column)
        other_data = other_item.get_value(column)

        # If this item's UserRole data is None, consider it less; if other data is None, consider it greater
        if self_data is None:
            return True
        if other_data is None:
            return False

        # Try to compare data directly. If the comparison fails, compare their string representations
        try:
            return self_data < other_data
        except TypeError:
            return str(self_data) < str(other_data)

    def __hash__(self):
        """Return the hash of the item based on its ID.
        """
        return hash(self.id)

class ColumnManagementWidget(QtWidgets.QTreeWidget):

    # Initialization and Setup
    # ------------------------
    def __init__(self, tree_widget: 'GroupableTreeWidget'):
        super().__init__(tree_widget)

        # Store the arguments
        self.tree_widget = tree_widget

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setItemsExpandable(False)
        self.setRootIsDecorated(False)

        # Set the minimum width for the first column
        self.header().setMinimumSectionSize(20)
        self.setColumnWidth(0, 20)  # Adjust the size of the first column

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.tree_widget.header().sectionMoved.connect(self.update_columns)
        self.tree_widget.model().headerDataChanged.connect(self.update_columns)

        self.itemClicked.connect(self.toggle_check_state)
        self.itemChanged.connect(self.set_column_visibility)

    def toggle_check_state(self, tree_item: QtWidgets.QTreeWidgetItem, column: int):
        """Toggle the checkbox state when an item's text (second column) is clicked.
        """
        if column != 1:
            return

        current_state = tree_item.checkState(0)
        new_state = QtCore.Qt.CheckState.Checked if current_state == QtCore.Qt.CheckState.Unchecked else QtCore.Qt.CheckState.Unchecked
        tree_item.setCheckState(0, new_state)  # Toggle the check state

    def sync_column_order(self):
        """Synchronize the column order.
        """
        for i in range(self.topLevelItemCount()):
            column_name = self.topLevelItem(i).text(1)
            visual_index = self.tree_widget.get_column_visual_index(column_name)
            self.tree_widget.header().moveSection(visual_index, i)

    def set_column_visibility(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """Set the visibility of a column based on the item's check state.
        """
        column_name = item.text(1)
        is_hidden = item.checkState(0) == QtCore.Qt.CheckState.Unchecked
        column_index = self.tree_widget.get_column_index(column_name)

        self.tree_widget.setColumnHidden(column_index, is_hidden)

    def update_columns(self):
        """Update the columns.
        """
        self.clear()

        if not self.tree_widget.column_names:
            return

        logical_indexes = [self.tree_widget.get_column_logical_index(i) for i in range(self.tree_widget.columnCount())]
        header_names = [self.tree_widget.column_names[i] for i in logical_indexes]

        self.addItems(header_names)

    def addItem(self, label: str, is_checked: bool = False):
        """Add an item to the tree.

        Args:
            label (str): The label for the tree item.
            is_checked (bool): Whether the item should be checked by default.
        """
        # Create a new tree widget item with an empty first column and the specified label
        tree_item = QtWidgets.QTreeWidgetItem(self, ['', label])
        # Convert boolean is_checked to Qt.CheckState, then set the tree item's check state
        check_state = QtCore.Qt.CheckState.Checked if is_checked else QtCore.Qt.CheckState.Unchecked
        tree_item.setCheckState(0, check_state)

    def addItems(self, labels: Iterable[str]):
        """Add multiple items to the tree.
        """
        for column_visual_index, label in enumerate(labels):
            column_logical_index = self.tree_widget.get_column_logical_index(column_visual_index)
            is_checked = not self.tree_widget.isColumnHidden(column_logical_index)
            self.addItem(label, is_checked)

    def dropEvent(self, event: QtGui.QDropEvent):
        """Handle the drop event.
        """
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
        """Initialize the attributes.
        """
        # Attributes
        # ----------
        self.tabler_icon = TablerQIcon(opacity=0.8)

        # Private Attributes
        # ------------------
        ...

    def __init_ui(self):
        """Initialize the UI of the widget.
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
        """Initialize signal-slot connections.
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

class GroupableTreeWidget(MomentumScrollTreeWidget):
    """A QTreeWidget subclass that displays data in a tree structure with the ability to group data by a specific column.

    Attributes:
        column_names (List[str]): The list of column names to be displayed in the tree widget.
        groups (Dict[str, TreeWidgetItem]): A dictionary mapping group names to their tree widget items.
    """
    # Default value
    DEFAULT_ROW_HEIGHT = 24

    # Signals emitted by the GroupableTreeWidget
    ungrouped_all = QtCore.Signal()
    item_added = QtCore.Signal(TreeWidgetItem)
    drag_started = QtCore.Signal(QtCore.Qt.DropActions)
    about_to_show_header_menu = QtCore.Signal(int)

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
        """Initialize the attributes.
        """
        # Attributes
        # ----------
        # Store the current grouped column name
        self.column_names: List[str] = []
        self.color_adaptive_columns: List[int] = []
        self.grouped_column_names: List[str] = []

        # Initialize the HighlightItemDelegate object to highlight items in the tree widget
        self.highlight_item_delegate = widgets.HighlightItemDelegate()
        self.thumbnail_delegate = widgets.ThumbnailDelegate(self)

        # Private Attributes
        # ------------------
        self._primary_key = None
        self._row_height = self.DEFAULT_ROW_HEIGHT
        self._current_column_index = 0
        self._item_widget_connections: List[QtWidgets.QWidget] = []

        self._id_to_tree_item: Dict[Any, QtWidgets.QTreeWidgetItem] = {}

        # TODO: Separate class to handle this
        self.generator = None
        self._current_task = None

        self.batch_size = 50
        self.threshold_to_fetch_more = 50
        self.has_more_items_to_fetch = False
        self._vertical_scroll_connection = None
        # ---

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)

        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)

        # Set up the context menu
        self.header().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

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

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signal of header
        self.header().customContextMenuRequested.connect(self._show_header_context_menu)
        self.header().sortIndicatorChanged.connect(lambda _: self.set_row_height())

        self.itemExpanded.connect(self.toggle_expansion_for_selected)
        self.itemCollapsed.connect(self.toggle_expansion_for_selected)
        self.itemSelectionChanged.connect(self._highlight_selected_items)

        self.highlight_item_delegate.highlight_changed.connect(self.update)

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
            | Grouping                      | - [0]
            | - Group by this column        |
            | - Ungroup all                 |
            | ----------------------------- |
            | Visualization                 | - [1]
            | - Set Color Adaptive          |
            | - Reset All Color Adaptive    |
            | ----------------------------- |
            | - Fit in View                 |
            | ----------------------------- |
            | Manage Columns                | - [2]
            | - Show/Hide Columns >         |
            | - Hide This Column            |
            +-------------------------------+
        """
        # Create the context menu
        self.header_menu = ContextMenu()

        # [0] - Add 'Grouping' section with actions: 'Group by this column' and 'Ungroup all'
        grouping_section_action = self.header_menu.addSection('Grouping')
        self.group_by_action = grouping_section_action.addAction('Group by this column')
        ungroup_all_action = grouping_section_action.addAction('Ungroup all')
        # [1] - Add 'Visualization' section with actions: 'Set Color Adaptive', 'Reset All Color Adaptive', and 'Fit in View'
        visualization_section_action = self.header_menu.addSection('Visualization')
        apply_color_adaptive_action = visualization_section_action.addAction('Set Color Adaptive')
        reset_all_color_adaptive_action = visualization_section_action.addAction('Reset All Color Adaptive')
        visualization_section_action.addSeparator()
        fit_column_in_view_action = visualization_section_action.addAction('Fit in View')
        # [2] - Add 'Manage Columns' section with actions for column management
        manage_columns_section_action = self.header_menu.addSection('Manage Columns')
        show_hide_column_menu = manage_columns_section_action.addMenu('Show/Hide Columns')
        self.column_management_widget = ColumnManagementWidget(self)
        column_management_widget_action = QtWidgets.QWidgetAction(self)
        column_management_widget_action.setDefaultWidget(self.column_management_widget)
        show_hide_column_menu.addAction(column_management_widget_action)
        hide_this_column = manage_columns_section_action.addAction('Hide This Column')

        # Connect actions to their corresponding methods
        self.group_by_action.triggered.connect(lambda: self.group_by_column(self._current_column_index))
        ungroup_all_action.triggered.connect(self.ungroup_all)
        apply_color_adaptive_action.triggered.connect(lambda: self.apply_column_color_adaptive(self._current_column_index))
        reset_all_color_adaptive_action.triggered.connect(self.reset_all_color_adaptive_column)
        fit_column_in_view_action.triggered.connect(self.fit_column_in_view)
        hide_this_column.triggered.connect(lambda: self.hideColumn(self._current_column_index))

    def _show_header_context_menu(self, pos: QtCore.QPoint):
        """Show a context menu for the header of the tree widget.

        Args:
            pos (QtCore.QPoint): The position where the right-click occurred.
        """
        # Get the index of the column where the right click occurred
        self._current_column_index = self.header().logicalIndexAt(pos)

        # Emit the custom signal with the column index
        self.about_to_show_header_menu.emit(self._current_column_index)

        # Disable 'Group by this column' on the first column
        self.group_by_action.setEnabled(bool(self._current_column_index))
        if self.column_names[self._current_column_index] in self.grouped_column_names:
            self.group_by_action.setEnabled(False)

        # Show the context menu
        self.header_menu.popup(QtGui.QCursor.pos())

    # TODO: Move to util
    def _create_item_groups(self, items: List[QtWidgets.QTreeWidgetItem], column: int) -> Dict[str, List[QtWidgets.QTreeWidgetItem]]:
        """Group the data into a dictionary mapping group names to lists of tree items.

        Args:
            items (List[QtWidgets.QTreeWidgetItem]): The data to be grouped.
            column (int):

        Returns:
            Dict[str, List[QtWidgets.QTreeWidgetItem]]: A dictionary mapping group names to lists of tree items.
        """
        # Create a defaultdict to store the groups
        group_name_to_tree_items = defaultdict(list)

        for item in items:
            key_data = item.data(column, QtCore.Qt.ItemDataRole.UserRole) or '_others'
            group_name_to_tree_items[key_data].append(item)

        return group_name_to_tree_items

    def _highlight_selected_items(self):
        """Highlight the specified `tree_items` in the tree widget.
        """
        self.highlight_item_delegate.set_selected_items(self.selectedItems())

    # Public Methods
    # --------------
    def create_thumbnail_column(self, source_column_name: str = 'file_path', sequence_range_column_name: str = 'sequence_range'):
        """Create a thumbnail column with specific source and sequence range columns.

        Args:
            source_column_name (str): The name of the source column. Defaults to 'file_path'.
            sequence_range_column_name (str): The name of the sequence range column. Defaults to 'sequence_range'.
        """
        if 'thumbnail' not in self.column_names:
            self.column_names.append('thumbnail')
        self.setHeaderLabels(self.column_names)

        source_column = self.column_names.index(source_column_name)
        thumbnail_column = self.column_names.index('thumbnail')
        sequence_range_column = self.column_names.index(sequence_range_column_name) if sequence_range_column_name in self.column_names else None

        self.thumbnail_delegate.set_thumbnail_column(thumbnail_column)
        self.thumbnail_delegate.set_source_column(source_column)
        self.thumbnail_delegate.set_sequence_range_column(sequence_range_column)

        self.setItemDelegateForColumn(thumbnail_column, self.thumbnail_delegate)

    def highlight_items(self, tree_items: Iterable['TreeWidgetItem'], focused_column_index: int = None):
        """Highlight the specified `tree_items` in the tree widget.

        Args:
            tree_items (Iterable[TreeWidgetItem]): The tree items to highlight.
            focused_column_index (Optional[int]): The focused column index. Defaults to None.
        """
        self.highlight_item_delegate.add_highlight_items(tree_items, focused_column_index)

    def clear_highlight(self):
        """Reset the highlight for all items.
        """
        self.highlight_item_delegate.clear_highlight_items()

    def set_row_height(self, height: Optional[int] = None):
        """Set the row height for all items in the tree widget.

        Args:
            height (Optional[int]): The desired row height. If None, use the current row height.
        """
        # Set the row height for all items
        self._row_height = height or self._row_height

        if self._row_height == -1:
            self.reset_row_height()
            return

        top_level_item = self.topLevelItem(0)
        if not top_level_item:
            return

        self.setUniformRowHeights(True)

        for column_index in range(self.columnCount()):
            size_hint = self.sizeHintForColumn(column_index)
            top_level_item.setSizeHint(column_index, QtCore.QSize(size_hint, self._row_height))

        # Force a visual update
        self.model().layoutChanged.emit()

    def reset_row_height(self):
        """Reset the row height to default.
        """
        top_level_item = self.topLevelItem(0)
        if not top_level_item:
            return

        self.setUniformRowHeights(False)

        for column_index in range(self.columnCount()):
            size_hint = self.sizeHintForColumn(column_index)
            top_level_item.setSizeHint(column_index, QtCore.QSize(size_hint, -1))

        # Force a visual update
        self.model().layoutChanged.emit()

    def toggle_expansion_for_selected(self, reference_item: QtWidgets.QTreeWidgetItem):
        """Toggle the expansion state of selected items.

        Args:
            reference_item (QtWidgets.QTreeWidgetItem): The clicked item whose expansion state will be used as a reference.
        """
        # Get the currently selected items
        selected_items = self.selectedItems()

        # If no items are selected, return early
        if not selected_items:
            return

        # Set the expanded state of all selected items to match the expanded state of the clicked item
        for i in selected_items:
            i.setExpanded(reference_item.isExpanded())

    def get_column_value_range(self, column: int, child_level: int = 0) -> Tuple[Optional['Number'], Optional['Number']]:
        """Get the value range of a specific column at a given child level.

        Args:
            column (int): The index of the column.
            child_level (int): The child level to calculate the range for. Defaults to 0 (top-level items).

        Returns:
            Tuple[Optional[Number], Optional[Number]]: A tuple containing the minimum and maximum values,
            or (None, None) if no valid values are found.
        """
        # Get the items at the specified child level
        items = TreeUtil.get_child_items(self, target_depth=child_level)

        # Collect the values from the specified column in the items
        try:
            values = [
                item.get_value(column)
                for item in items
                if isinstance(item.get_value(column), Number)
            ]
        except AttributeError:
            values = [
                item.data(column, QtCore.Qt.ItemDataRole.UserRole) or item.data(column, QtCore.Qt.ItemDataRole.DisplayRole)
                for item in items
                if isinstance(item.data(column, QtCore.Qt.ItemDataRole.UserRole) or item.data(column, QtCore.Qt.ItemDataRole.DisplayRole), Number)
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
        child_level = len(self.grouped_column_names)

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

    def get_column_index(self, column_name: str) -> Optional[int]:
        """Retrieve the index of the specified column name.

        Args:
            column_name (str): The name of the column.

        Returns:
            Optional[int]: The index of the column if found, otherwise None.
        """
        return self.column_names.index(column_name) if column_name in self.column_names else None

    def get_column_visual_index(self, column: Union[str, int]) -> int:
        """Retrieve the visual index of the specified column.

        Args:
            column (Union[str, int]): The column name or index.

        Returns:
            int: The visual index of the column.
        """
        if isinstance(column, str):
            column = self.get_column_index(column)

        return self.header().visualIndex(column)

    def get_column_logical_index(self, visual_index: int) -> int:
        """Retrieve the logical index of the specified visual index.

        Args:
            visual_index (int): The visual index.

        Returns:
            int: The logical index of the visual index.
        """
        return self.header().logicalIndex(visual_index)

    def add_items(self, item_names: Union[Dict[str, List[str]], List[str]], parent: Optional[QtWidgets.QTreeWidgetItem] = None):
        """Add items to the tree widget.

        Args:
            item_names (Union[Dict[str, List[str]], List[str]]): If a dictionary is provided, it represents parent-child relationships where keys are parent item names and values are lists of child item names. If a list is provided, it contains item names to be added at the root level.
            parent (Optional[QtWidgets.QTreeWidgetItem]): The parent item. Defaults to None.
        """
        if isinstance(item_names, dict):
            self._add_items_from_id_to_data_dict(item_names, parent)
        elif isinstance(item_names, list):
            self._add_items_from_data_dicts(item_names, parent)
        else:
            raise ValueError("Invalid type for item_names. Expected a list or a dictionary.")

    def add_item(self, data_dict: Dict[str, Any], item_id: Optional[Union[str, Tuple[str, ...]]] = None, parent: Optional[QtWidgets.QTreeWidgetItem] = None) -> TreeWidgetItem:
        """Add an item to the tree widget, considering groupings if applicable.

        Args:
            data_dict (Dict[str, Any]): The data for the new item.
            item_id (Optional[Union[str, Tuple[str, ...]]]): The ID of the item. If None, the primary key from data_dict is used.
            parent (Optional[QtWidgets.QTreeWidgetItem]): The parent item. Defaults to None.

        Returns:
            TreeWidgetItem: The newly added tree item.
        """
        # Capture the current first top-level item, if any
        previous_first_item = self.topLevelItem(0) if self.topLevelItemCount() > 0 else None
        parent = parent or self.invisibleRootItem()

        # Generate a unique ID if not provided
        if not item_id:
            if isinstance(self._primary_key, list):
                # Handle composite key
                item_id = tuple(data_dict.get(key) for key in self._primary_key)
            else:
                # Handle single key
                item_id = data_dict.get(self._primary_key) or uuid.uuid1()

        # Determine the parent for the new item
        if parent is self.invisibleRootItem() and self.grouped_column_names:
            for grouped_column_name in self.grouped_column_names:
                # If the tree is grouped, find the appropriate parent group item
                group_value = data_dict.get(grouped_column_name, "_others")

                if group_value not in parent.child_grouped_dict:
                    new_grouped_item = TreeWidgetItem(parent, [group_value])
                    new_grouped_item.setExpanded(True)
                    new_grouped_item.child_grouped_dict = {}
                    parent.child_grouped_dict[group_value] = new_grouped_item
                    parent = new_grouped_item
                else:
                    parent = parent.child_grouped_dict[group_value]

        # Create a new TreeWidgetItem and add it to the parent
        tree_item = TreeWidgetItem(parent, item_data=data_dict, item_id=item_id)

        # Update dictionary
        self._id_to_tree_item[item_id] = tree_item

        # Check the current first top-level item after the potential sort
        current_first_item = self.topLevelItem(0)

        # If the first item has changed (by comparing object references), emit the signal
        if current_first_item != previous_first_item:
            self.set_row_height()

        # Emit a signal that an item has been added
        self.item_added.emit(tree_item)

        return tree_item

    def _add_items_from_id_to_data_dict(self, id_to_data_dict: Dict[str, Dict[str, Any]], parent: Optional[QtWidgets.QTreeWidgetItem]):
        """Add items to the tree widget.

        Args:
            id_to_data_dict (Dict[str, Dict[str, Any]]): A dictionary mapping item IDs to their data as a dictionary.
            parent (Optional[QtWidgets.QTreeWidgetItem]): The parent item. Defaults to None.
        """
        # Iterate through the dictionary of items
        for item_id, data_dict in id_to_data_dict.items():
            # Create a new custom QTreeWidgetItem for sorting by type of the item data, and add to the self tree widget
            self.add_item(data_dict, item_id, parent)

    # TODO: Handle id or primary key
    def _add_items_from_data_dicts(self, data_dicts: List[Dict[str, Any]], parent: Optional[QtWidgets.QTreeWidgetItem] = None):
        """Add items to the tree widget at the root level from a list of data dictionaries.

        Args:
            data_dicts (List[Dict[str, Any]]): A list of data dictionaries to be added at the root level.
            parent (Optional[QtWidgets.QTreeWidgetItem]): The parent item. Defaults to None.
        """
        for data_dict in data_dicts:
            self.add_item(data_dict, parent=parent)

    def get_item_by_id(self, item_id: Any) -> Optional[TreeWidgetItem]:
        return self._id_to_tree_item.get(item_id)

    def set_primary_key(self, primary_key: Union[str, List[str]]):
        """Set the primary key for the tree widget.

        Args:
            primary_key (Union[str, List[str]]): The primary key, either as a single string or a list of strings for composite keys.
        """
        self._primary_key = primary_key

    def update_item(self, data_dict: Dict[str, Any], update_key: Optional[Union[str, List[str]]] = None, add_if_not_exist: bool = False) -> Optional[TreeWidgetItem]:
        """Update an item in the tree widget based on a specified update key or add it as a new item if it doesn't exist.

        Args:
            data_dict (Dict[str, Any]): The data to update the item with.
            update_key (Optional[Union[str, Tuple[str]]]): The key(s) to use for identifying the item to update. If None, the primary key is used.
            add_if_not_exist (bool): If True, add a new item if the specified item doesn't exist. Defaults to False.

        Returns:
            Optional[TreeWidgetItem]: The updated or newly added tree item, or None if not found and add_if_not_exist is False.
        """
        # Use the provided update_key or fall back to the primary key
        update_key = update_key or self._primary_key

        if not update_key:
            item_id = uuid.uuid1()
        # Handle single key or composite key
        elif isinstance(update_key, list):
            # Create a tuple of item_id values from the composite key
            item_id = tuple(data_dict[key] for key in update_key)
        else:
            # Single key case
            item_id = data_dict[update_key]

        # Find the item by ID
        tree_item = self.get_item_by_id(item_id)

        # If item doesn't exist and add_if_not_exist is True, add a new item
        if not tree_item:
            if add_if_not_exist:
                tree_item = self.add_item(data_dict, item_id=item_id)
            else:
                return None

        # Update the item data
        for key, value in data_dict.items():
            if key not in self.column_names:
                continue
            tree_item.set_value(key, value)

        # Refresh the display
        self.update()

        return tree_item

    def group_by_column(self, column: Union[int, str]):
        """Group the items in the tree widget by the values in the specified column.

        Args:
            column (Union[int, str]): The index or name of the column to group by.
        """
        if not isinstance(column, int):
            column = self.get_column_index(column)

        # Hide the grouped column
        self.setColumnHidden(column, True)

        # Group the data and add the tree items to the appropriate group
        if not self.grouped_column_names:
            parent_item = self.invisibleRootItem()
            parent_item.child_grouped_dict = {}
            self.group_items(parent_item, column)
        else:
            lowest_grouped_items = TreeUtil.get_child_items(self, target_depth=len(self.grouped_column_names) - 1)
            for lowest_grouped_item in lowest_grouped_items:
                self.group_items(lowest_grouped_item, column)

        # Get the label for the column that we want to group by and the label for the first column 
        grouped_column_name = self.headerItem().text(column)
        self.grouped_column_names.append(grouped_column_name)

        # Store original and rename the first column
        first_column_name = self.column_names[0]
        self.headerItem().setData(0, QtCore.Qt.ItemDataRole.UserRole, first_column_name)
        grouped_column_names_str = ' / '.join(self.grouped_column_names + [first_column_name])
        self.setHeaderLabel(grouped_column_names_str)

        # Expand all items
        self.expandAll()

        # Resize first columns to fit their contents
        self.resizeColumnToContents(0)

    # TODO: Move to util
    def group_items(self, parent_item: QtWidgets.QTreeWidgetItem, column: int):
        """Group items under the parent item based on the values in the specified column.

        Args:
            parent_item (QtWidgets.QTreeWidgetItem): The parent item for grouping.
            column (int): The column index to group by.
        """
        # Take all children from the parent item
        target_items = parent_item.takeChildren()
        # Create groups based on the target items
        grouped_name_to_tree_items = self._create_item_groups(target_items, column)

        # Iterate through each group and its items
        for grouped_name, items in grouped_name_to_tree_items.items():
            # Create a new QTreeWidgetItem for the group
            grouped_item = TreeWidgetItem(parent_item, [grouped_name])
            grouped_item.child_grouped_dict = {}
            parent_item.child_grouped_dict[grouped_name] = grouped_item
            grouped_item.addChildren(items)

    def fit_column_in_view(self):
        """Adjust the width of all columns to fit the entire view.
    
        This method resizes columns so that their sum is equal to the width of the view minus the width of the vertical scroll bar. 
        It starts by reducing the width of the column with the largest width by 10% until all columns fit within the expected width.
        """
        TreeUtil.fit_column_in_view(self)

    def ungroup_all(self):
        """Ungroup all the items in the tree widget.
        """
        # Return if there are no groups to ungroup
        if not self.grouped_column_names:
            return

        # Reset the header label
        self.setHeaderLabel(self.column_names[0])
        
        # Show hidden column
        for grouped_column_name in self.grouped_column_names:
            column_index = self.get_column_index(grouped_column_name)
            self.setColumnHidden(column_index, False)

        # Get target items at a specific child level
        target_items = TreeUtil.get_child_items(self, target_depth=len(self.grouped_column_names))

        # Reparent to root and remove the empty grouped items
        TreeItemUtil.remove_items(target_items)
        self.clear()
        self.addTopLevelItems(target_items)

        # Clear the grouped columns
        self.grouped_column_names.clear()

        # Resize first columns to fit their contents
        self.resizeColumnToContents(0)

        # Emit signal for ungrouped all
        self.ungrouped_all.emit()

    def copy_selected_cells(self):
        """Copy selected cells to the clipboard.
        """
        # Get selected indexes from the view
        selected_indexes = self.selectedIndexes()
        all_items = TreeUtil.get_child_items(self)

        # Sort the cells based on their global row and column
        sorted_indexes = sorted(
            selected_indexes, 
            key=lambda index: (
                all_items.index(self.itemFromIndex(index)),
                index.column()
            )
        )

        # Initialize a dictionary to store cell texts and a set to store columns
        cell_dict: Dict[int, Dict[int, str]] = defaultdict(lambda: defaultdict(str))
        columns = set()

        # Fill the cell_dict with cell texts
        for index in sorted_indexes:
            tree_item = self.itemFromIndex(index)
            global_row = all_items.index(tree_item)
            column = index.column()

            cell_value = tree_item.get_value(column)
            cell_text = '' if cell_value is None else str(cell_value)
            cell_text = f'"{cell_text}"' if ('\t' in cell_text or '\n' in cell_text) else cell_text

            cell_dict[global_row][column] = cell_text
            columns.add(column)

        # Create row texts ensuring all columns are included
        row_texts = ['\t'.join(row[column] for column in sorted(columns)) for row in cell_dict.values()]
        full_text = '\n'.join(row_texts)

        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(full_text)

        # Show tooltip message
        self.show_tool_tip(f'Copied:\n{full_text}', 5000)

    def show_tool_tip(self, text: str, msc_show_time: int = 1000):
        """Show a tooltip message.

        Args:
            text (str): The text to display in the tooltip.
            msc_show_time (int): The time to display the tooltip in milliseconds. Defaults to 1000.
        """
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text, self, QtCore.QRect(), msc_show_time)

    def paste_cells_from_clipboard(self):
        """Paste cells from the clipboard. Further implementation is required.
        """
        # NOTE: Further Implementation Required
        # TODO: Implement popup window to confirm pasting data into each column.
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

        print('Not implemented')

    def save_state(self, settings: QtCore.QSettings, group_name='tree_widget'):
        """Save the state of the tree widget.

        Args:
            settings (QtCore.QSettings): The settings object to save the state.
            group_name (str): The group name for the settings. Defaults to 'tree_widget'.
        """
        settings.beginGroup(group_name)
        settings.setValue('header_state', self.header().saveState())
        settings.setValue('color_adaptive_columns', self.color_adaptive_columns)
        settings.setValue('group_column_names', self.grouped_column_names)
        settings.setValue('uniform_row_height', self._row_height)
        settings.endGroup()

    def load_state(self, settings: QtCore.QSettings, group_name='tree_widget'):
        """Load the state of the tree widget.

        Args:
            settings (QtCore.QSettings): The settings object to load the state.
            group_name (str): The group name for the settings. Defaults to 'tree_widget'.
        """
        settings.beginGroup(group_name)
        header_state = settings.value('header_state', QtCore.QByteArray)
        color_adaptive_columns = settings.value('color_adaptive_columns', type=list)
        grouped_column_names = settings.value('grouped_column_names', type=list)
        uniform_row_height = int(settings.value('uniform_row_height', -1))
        settings.endGroup()

        if not header_state:
            return

        self.header().restoreState(header_state)
        self._restore_color_adaptive_column(color_adaptive_columns)
        for grouped_column_name in grouped_column_names:
            self.group_by_column(grouped_column_name)
        self.set_row_height(uniform_row_height)
        self.column_management_widget.update_columns()

    # TODO: Separate class
    # Generator
    # ---------
    def set_generator(self, generator: Optional[Generator]):
        """Set a new generator, clearing the existing task before setting the new generator.

        Args:
            generator (Optional[Generator]): The generator to set.
        """
        self.clear()

        self.generator = generator

        if not self.generator:
            return

        self.has_more_items_to_fetch = True
        self._vertical_scroll_connection = self.verticalScrollBar().valueChanged.connect(self._check_scroll_position)

        first_batch_size = self.calculate_dynamic_batch_size()

        self.data_fetching_buttons.show()
        self._fetch_more_data(first_batch_size)

    def calculate_dynamic_batch_size(self) -> int:
        """Estimate the number of items that can fit in the current view.

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
        return max(estimated_items, self.batch_size)

    def stop_fetch(self):
        """Pause the current fetching task."""
        if self._current_task:
            self._current_task.pause()

    def fetch_more(self):
        """Fetch more data."""
        self._fetch_more_data(self.batch_size)

    def fetch_all(self):
        """Fetch all remaining data."""
        self._fetch_more_data()

    def show_fetching_indicator(self):
        """Show the fetching indicator."""
        self.fetch_more_button.hide()
        self.fetch_all_button.hide()
        self.stop_fetch_button.show()

    def show_fetch_buttons(self):
        """Show the fetch buttons."""
        # Once fetching is finished, change the button text back to "Fetch More" and enable it
        self.fetch_more_button.show()
        self.fetch_all_button.show()
        self.stop_fetch_button.hide()
        self._current_task = None

    def position_fetch_more_button(self):
        """Position the 'Fetch More' button."""
        if self.data_fetching_buttons.isHidden():
            return

        # Position the Fetch More button at the center bottom of the tree widget
        x = (self.width() - self.data_fetching_buttons.width()) / 2
        y = self.height() - self.data_fetching_buttons.height() - 30

        self.data_fetching_buttons.move(int(x), int(y))

    def _restore_color_adaptive_column(self, columns: List[int]):
        """Restore the color adaptive columns.

        Args:
            columns (List[int]): The columns to restore.
        """
        self.reset_all_color_adaptive_column()

        for column in columns:
            self.apply_column_color_adaptive(column)

    def _fetch_more_data(self, batch_size: Optional[int] = None):
        """Fetch more data using the generator.

        Args:
            batch_size (Optional[int]): The batch size to fetch. If None, fetch all remaining data.
        """
        if self._current_task is not None or not self.has_more_items_to_fetch:
            return

        items_to_fetch = islice(self.generator, batch_size) if batch_size else self.generator

        # Create the self._current_task
        self._current_task = GeneratorWorker(items_to_fetch, desired_size=batch_size)
        # Connect signals to slots for handling placeholders and real data
        self._current_task.result.connect(lambda data_dict: self.update_item(data_dict, add_if_not_exist=True))
        self._current_task.started.connect(self.show_fetching_indicator)
        self._current_task.finished.connect(self.show_fetch_buttons)
        self._current_task.loaded_all.connect(self._handle_no_more_items)

        # Start the self._current_task using ThreadPoolManager
        ThreadPoolManager.thread_pool().start(self._current_task.run)

    def _handle_no_more_items(self):
        """Handle the event when there are no more items to fetch."""
        self.has_more_items_to_fetch = False
        self._disconnect_check_scroll_position()
        self.data_fetching_buttons.hide()
        self.show_tool_tip("All items have been fetched.", 5000)

    def _disconnect_check_scroll_position(self):
        """Disconnect the scroll position check.
        """
        if not self._vertical_scroll_connection:
            return

        self.verticalScrollBar().valueChanged.disconnect(self._vertical_scroll_connection)
        self._vertical_scroll_connection = None

    def _check_scroll_position(self, value: int):
        """Check the scroll position and fetch more data if the threshold is reached.

        Args:
            value (int): The current scroll value.
        """
        scroll_bar = self.verticalScrollBar()
        if value >= scroll_bar.maximum() - self.threshold_to_fetch_more:
            self._fetch_more_data(self.batch_size)

    # Override Methods
    # ----------------
    def setHeaderLabels(self, labels: Iterable[str]):
        """Set the names of the columns in the tree widget.

        Args:
            labels (Iterable[str]): The iterable of column names to be set.
        """
        # Store the column names for later use
        self.column_names = labels

        # Set the number of columns and the column labels
        self.setColumnCount(len(self.column_names))
        super().setHeaderLabels(self.column_names)

    def hideColumn(self, column: Union[int, str]):
        """Hide the specified column.

        Args:
            column (Union[int, str]): The column index or name.
        """
        column_index = self.get_column_index(column) if isinstance(column, str) else column
        super().hideColumn(column_index)

    def startDrag(self, supported_actions: QtCore.Qt.DropActions):
        """Handle drag event of the tree widget.

        Args:
            supported_actions (QtCore.Qt.DropActions): The supported actions for the drag event.
        """
        self.drag_started.emit(supported_actions)

    def clear(self):
        """Clear the tree widget and stop any current tasks.
        """
        if self._current_task is not None:
            self._current_task.stop()
            self._current_task = None

        self._id_to_tree_item.clear()

        # NOTE: Disconnect all stored signal connections
        for  connection in self._item_widget_connections:
            self.header().sectionResized.disconnect(connection)
        self._item_widget_connections.clear()

        super().clear()

    def scrollContentsBy(self, dx: int, dy: int):
        """Update positions of visible item widgets during scrolling.
        """
        super().scrollContentsBy(dx, dy)

        if widgets.ScalableView.is_scalable(self):
            self.model().layoutChanged.emit()

    def setItemWidget(self, item: QtWidgets.QTreeWidgetItem, column: int, widget: QtWidgets.QWidget):
        """Add a widget to an item and tracking the new one for position updates.
        """
        # NOTE: This ensures that the layout of the `TagListView` is updated dynamically when the section is resized
        if isinstance(widget, widgets.TagListView):
            connection = self.header().sectionResized.connect(widget.model().layoutChanged.emit)
            self._item_widget_connections.append(connection)

        super().setItemWidget(item, column, widget)


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

    # tree_widget = GroupableTreeWidget()
    # tree_widget.setHeaderLabels(COLUMN_NAME_LIST)
    # tree_widget.add_items(ID_TO_DATA_DICT)

    # Show the window and run the application
    tree_widget.show()

    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
