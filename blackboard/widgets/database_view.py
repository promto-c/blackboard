# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, List, Type, Tuple, Union
if TYPE_CHECKING:
    from blackboard.utils.database_manager import DatabaseManager, ManyToManyField, FieldInfo
    from blackboard.widgets.groupable_tree_widget import TreeWidgetItem
    from blackboard.widgets.filter_widget import FilterCondition

# Standard Library Imports
# ------------------------
import uuid
from enum import Enum
from functools import partial

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets


# Class Definitions
# -----------------
class ColumnType(Enum):
    """Enum representing user-friendly column types and their associated filter widgets."""
    TEXT = ('Text', widgets.TextFilterWidget)
    INT = ('Whole Number', widgets.NumericFilterWidget)
    FLOAT = ('Decimal Number', widgets.NumericFilterWidget)
    DATE = ('Date', widgets.DateRangeFilterWidget)
    DATETIME = ('Date & Time', widgets.DateTimeRangeFilterWidget)
    BOOLEAN = ('True/False', widgets.BooleanFilterWidget)
    ENUM = ('Single Select', widgets.MultiSelectFilterWidget)
    LIST = ('Multiple Select', widgets.MultiSelectFilterWidget)

    def __init__(self, display_type: str, filter_widget_cls: Type[widgets.FilterWidget]):
        """Initialize the ColumnType enum with a user-friendly display type and filter widget class."""
        self.display_type = display_type
        self.filter_widget_cls = filter_widget_cls

    @property
    def filter_widget(self) -> Type[widgets.FilterWidget]:
        """Return the filter widget class associated with the column type."""
        return self.filter_widget_cls

    @property
    def type_name(self) -> str:
        """Return the user-friendly display type of the column."""
        return self.display_type

    def __str__(self):
        """Return a string representation of the ColumnType enum."""
        return f"ColumnType({self.display_type}, Filter Widget: {self.filter_widget_cls.__name__})"

    @staticmethod
    def from_sql(sql_type: str) -> 'ColumnType':
        """Map SQL column type to the corresponding ColumnType enum.

        Args:
            sql_type (str): The SQL type of the column.

        Returns:
            ColumnType: The corresponding ColumnType enum instance.
        """
        sql_type = sql_type.upper()

        # Map common SQL types to ColumnType enum
        if any(keyword in sql_type for keyword in ['CHAR', 'VARCHAR', 'TEXT', 'CLOB']):
            return ColumnType.TEXT
        elif any(keyword in sql_type for keyword in ['INT', 'INTEGER', 'TINYINT', 'SMALLINT', 'BIGINT', 'SERIAL']):
            return ColumnType.INT
        elif any(keyword in sql_type for keyword in ['REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC', 'MONEY']):
            return ColumnType.FLOAT
        elif 'DATETIME' in sql_type or 'TIMESTAMP' in sql_type:
            return ColumnType.DATETIME  # Support DATETIME types
        elif 'DATE' in sql_type:
            return ColumnType.DATE
        elif any(keyword in sql_type for keyword in ['BOOLEAN', 'BOOL']):
            return ColumnType.BOOLEAN
        elif 'ENUM' in sql_type:  # Assumption: Custom enum or select types include 'ENUM' keyword
            return ColumnType.ENUM
        elif 'LIST' in sql_type or 'ARRAY' in sql_type:  # Use 'LIST' for PostgreSQL array types
            return ColumnType.LIST

        # PostgreSQL-Specific Types
        elif 'UUID' in sql_type:
            return ColumnType.TEXT
        elif 'JSON' in sql_type or 'JSONB' in sql_type:
            return ColumnType.TEXT
        elif 'TSVECTOR' in sql_type or 'TSQUERY' in sql_type:
            return ColumnType.TEXT
        elif 'HSTORE' in sql_type:
            return ColumnType.TEXT
        elif 'CIDR' in sql_type or 'INET' in sql_type or 'MACADDR' in sql_type:
            return ColumnType.TEXT
        elif 'BIT' in sql_type:
            return ColumnType.INT
        elif 'INTERVAL' in sql_type:
            return ColumnType.TEXT
        elif 'BYTEA' in sql_type:
            return ColumnType.TEXT

        else:
            raise ValueError(f"Unsupported SQL type: {sql_type}")

class DataViewWidget(QtWidgets.QWidget):
    """A widget for displaying and interacting with a data view.
    """

    LABEL: str = 'Data View'

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None, identifier: Optional[str] = None):
        """Initialize the widget and set up the UI, signal connections.
        """
        # Initialize the super class
        super().__init__(parent)

        # Generate a unique identifier if none is provided
        self.identifier = identifier or str(uuid.uuid4())

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.

        UI Wireframe:

            |--[W1]: filter_bar_widget--|

            +---------------------------------------------------+ -+
            | [Filter 1][Filter 2][+]       [[W2]: search_edit] |  | -> [L1]: top_bar_area_layout
            +---------------------------------------------------+ -+
            | [W3]: general_tool_bar| - - | [W4]: view_tool_bar |  | -> [L2]: utility_area_layout
            |                                                   |  |
            |                                                   |  |
            |               [[W5]: tree_widget]                 |  | -> [L3]: main_view_layout
            |                                                   |  |
            |                                                   |  |
            +---------------------------------------------------+ -+
        """
        # Create Layouts
        # --------------
        # [L0]: Set main layout as vertical layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # [L1]: Add top bar layout as horizontal layout
        self.top_bar_area_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.top_bar_area_layout)

        # [L2]: Add utility layout
        self.utility_area_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.utility_area_layout)

        # [L3]: Add main tree layout
        self.main_view_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.main_view_layout)

        # Create Widgets
        # --------------
        # [W1]: Create top left filter bar
        self.filter_bar_widget = widgets.FilterBarWidget(self)
        self.add_filter_button = self.filter_bar_widget.add_filter_button

        # [W5]: Create asset tree widget
        self.tree_widget = widgets.GroupableTreeWidget(parent=self)

        # [W2]: Search field
        self.search_edit = widgets.SimpleSearchEdit(tree_widget=self.tree_widget, parent=self)
        self.search_edit.setMinimumWidth(200)

        # [W3], [W4]: General tool bar and view utility bar
        self.general_tool_bar = QtWidgets.QToolBar(self)
        self.view_tool_bar = widgets.TreeUtilityToolBar(self.tree_widget)

        # Add Widgets to Layouts
        # ----------------------
        # Add [W1], [W2] to [L1]
        # Add left filter bar and right search edit to top bar layout
        self.top_bar_area_layout.addWidget(self.filter_bar_widget)
        self.top_bar_area_layout.addStretch()
        self.top_bar_area_layout.addWidget(self.search_edit)

        # Add [W3], [W4] to [L2]
        # Add left general tool bar and right view tool bar
        self.utility_area_layout.addWidget(self.general_tool_bar)
        self.utility_area_layout.addStretch()
        self.utility_area_layout.addWidget(self.view_tool_bar)

        # Add [W5] to [L3]
        # Add tree widget to main tree widget
        self.main_view_layout.addWidget(self.tree_widget)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.view_tool_bar.refresh_button.clicked.connect(self.activate_filter)
        bb.utils.KeyBinder.bind_key('Ctrl+F', self.tree_widget, self.search_edit.set_text_as_selection)

    # Public Methods
    # --------------
    def add_filter_widget(self, filter_widget: 'widgets.FilterWidget'):
        self.filter_bar_widget.add_filter_widget(filter_widget)
        filter_widget.activated.connect(self.activate_filter)

    def save_state(self, settings: QtCore.QSettings, group_name: str = 'data_view'):
        self.tree_widget.save_state(settings, group_name)
    
    def load_state(self, settings: QtCore.QSettings, group_name: str = 'data_view'):
        self.tree_widget.load_state(settings, group_name)

    def activate_filter(self):
        # Logic to filter data then populate
        ...
        # Example Implementation:
        # ---
        # id_to_data_dict = ...
        # self.populate(id_to_data_dict)

        raise NotImplementedError(f"{self.__class__.__name__}.activate_filter must be implemented by subclasses.")

    def populate(self, id_to_data_dict: Dict[Iterable, Dict[str, Any]]):
        # Clear old items
        self.tree_widget.clear()

        # Add items to tree
        self.tree_widget.add_items(id_to_data_dict)

        self.search_edit.update()

    # Special Methods
    # ---------------
    def __hash__(self):
        return hash(self.identifier)

class FileBrowseWidget(QtWidgets.QWidget):

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None):
        """Initializes the FileBrowseWidget with a line edit and a browse button.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(parent)

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        layout = QtWidgets.QHBoxLayout(self)

        # Create Widgets
        # --------------
        self.line_edit = QtWidgets.QLineEdit()
        self.browse_button = QtWidgets.QPushButton("Browse")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.line_edit)
        layout.addWidget(self.browse_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.browse_button.clicked.connect(self.browse_file)

    # Public Methods
    # --------------
    def browse_file(self):
        """Opens a file dialog to allow the user to select a file and populates the line edit.
        """
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File")
        if not file_name:
            return
        self.line_edit.setText(file_name)
    
    def get_value(self) -> str:
        """Returns the current text in the line edit, or None if it is empty.
        """
        return self.line_edit.text()

class AddEditRecordDialog(QtWidgets.QDialog):

    # Initialization and Setup
    # ------------------------
    def __init__(self, db_manager: 'DatabaseManager', table_name: str, data_dict: dict = None, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.table_name = table_name
        self.db_manager = db_manager
        self.data_dict = data_dict

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.field_name_to_input_widgets: Dict[str, QtWidgets.QWidget] = {}
        self.field_name_to_info = self.db_manager.get_fields(self.table_name)
        self.many_to_many_fields = self.db_manager.get_many_to_many_fields(self.table_name)

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle("Add/Edit Record")

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        for field_name, field_info in self.field_name_to_info.items():
            # Skip the primary key field; it is usually auto-managed by SQLite
            if field_info.type == 'INTEGER' and field_info.is_primary_key:
                continue

            input_widget = self.create_input_widget(field_info)
            label = widgets.LabelEmbedderWidget(input_widget, field_name)
            layout.addWidget(label)
            self.field_name_to_input_widgets[field_name] = input_widget

        for track_field_name, many_to_many_field in self.many_to_many_fields.items():
            m2m_widget = self.create_many_to_many_widget(many_to_many_field)
            label = widgets.LabelEmbedderWidget(m2m_widget, track_field_name)
            layout.addWidget(label)
            self.field_name_to_input_widgets[track_field_name] = m2m_widget

        if self.data_dict:
            for field, value in self.data_dict.items():
                if field not in self.field_name_to_input_widgets:
                    continue

                self.set_input_value(field, value)

        self.submit_button = QtWidgets.QPushButton("Submit")

        # Add Widgets to Layouts
        # ----------------------
        layout.addStretch()
        layout.addWidget(self.submit_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.submit_button.clicked.connect(self.update_record)

    # Public Methods
    # --------------
    def update_record(self):
        new_values = self.get_record_data()

        # Check only required fields, excluding INTEGER PRIMARY KEY fields
        required_fields = [
            field_name for field_name, field_info in self.field_name_to_info.items()
            if field_info.is_not_null and not (field_info.type == 'INTEGER' and field_info.is_primary_key)
        ]

        if not all(new_values.get(field) is not None for field in required_fields):
            QtWidgets.QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return

        if self.data_dict:
            # Determine which fields have changed
            updated_data_dict = {field: new_value for field, new_value in new_values.items() if new_value != self.data_dict.get(field)}

            if not updated_data_dict:
                QtWidgets.QMessageBox.information(self, "No Changes", "No changes were made.")
                return
 
            # Get the primary key field name and its value
            pk_field = self.db_manager.get_primary_keys(self.table_name)[0]
            pk_value = self.data_dict.get(pk_field)

            self.db_manager.update_record(self.table_name, updated_data_dict, pk_value, pk_field, handle_m2m=bool(self.many_to_many_fields))

        else:
            # Filter out primary key fields and create a dictionary for insertion
            data_filtered = {
                field_name: new_values[field_name]
                for field_name, field_info in self.field_name_to_info.items()
                if not (field_info.type == 'INTEGER' and field_info.is_primary_key)
            }

            for track_field_name in self.many_to_many_fields.keys():
                if track_field_name not in new_values:
                    continue
                data_filtered[track_field_name] = new_values[track_field_name]

            # Insert the record using the updated insert_record method
            self.db_manager.insert_record(self.table_name, data_filtered, handle_m2m=bool(self.many_to_many_fields))

        self.accept()

    def create_input_widget(self, field_info: 'FieldInfo'):
        if field_info.is_foreign_key:
            # Handle foreign keys by offering a dropdown of related records
            fk = field_info.fk
            display_field = self.db_manager.get_display_field(self.table_name, field_info.name)

            if display_field:
                related_records = list(self.db_manager.query_table_data(fk.table, fields=[fk.to_field, display_field], as_dict=True))

                widget = QtWidgets.QComboBox()
                for record in related_records:
                    display_value = self.format_combined_display(record[display_field], record[fk.to_field], fk.to_field)
                    key_value = record[fk.to_field]
                    widget.addItem(display_value, key_value)

                return widget

        if enum_table_name := self.db_manager.get_enum_table_name(self.table_name, field_info.name):
            enum_values = self.db_manager.get_enum_values(enum_table_name)
            widget = QtWidgets.QComboBox()
            widget.addItems(enum_values)
            return widget

        if field_info.type == "INTEGER":
            widget = QtWidgets.QSpinBox()
            widget.setRange(-2147483648, 2147483647)
            widget.setSpecialValueText("")
            return widget
        elif field_info.type == "REAL":
            widget = QtWidgets.QDoubleSpinBox()
            widget.setSpecialValueText("")
            return widget
        elif field_info.type == "TEXT":
            return QtWidgets.QLineEdit()
        elif field_info.type == "BLOB":
            return FileBrowseWidget()
        elif field_info.type == "DATETIME":
            return QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        else:
            return QtWidgets.QLineEdit()

    def format_combined_display(self, display_value: str, key_value: Union[int, str], key_name: str) -> str:
        """Format the display field combined with the key value and key name."""
        return f"{display_value} ({key_name}: {key_value})"

    def set_input_value(self, field_name, value):
        input_widget = self.field_name_to_input_widgets.get(field_name)
        field_info = self.field_name_to_info.get(field_name)

        if isinstance(input_widget, QtWidgets.QComboBox):
            if field_info and field_info.is_foreign_key:
                # If the field is a foreign key, find the corresponding display value
                fk = field_info.fk
                display_field = self.db_manager.get_display_field(self.table_name, field_info.name)

                if display_field:
                    display_text = self.db_manager.fetch_related_value(fk.table, display_field, fk.to_field, value)
                    formatted_display_text = self.format_combined_display(display_text, value, fk.to_field)
                    input_widget.setCurrentText(formatted_display_text)
                    return

            # Fallback to using the value directly if no display field is set
            index = input_widget.findText(value)
            if index == -1:
                input_widget.addItem(value)
                index = input_widget.findText(value)
            input_widget.setCurrentIndex(index)

        elif isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
            if value is None or value == 'None':
                input_widget.clear()
            else:
                input_widget.setValue(value)

        elif isinstance(input_widget, QtWidgets.QLineEdit):
            input_widget.setText("" if value is None else str(value))

        elif isinstance(input_widget, QtWidgets.QDateTimeEdit):
            input_widget.setDateTime(QtCore.QDateTime.fromString(value, "yyyy-MM-dd HH:mm:ss") if value else QtCore.QDateTime.currentDateTime())

        elif isinstance(input_widget, QtWidgets.QListWidget):
            selected_values = set(value)
            for i in range(input_widget.count()):
                item = input_widget.item(i)
                item_value = item.data(QtCore.Qt.ItemDataRole.UserRole)
                item.setCheckState(QtCore.Qt.Checked if item_value in selected_values else QtCore.Qt.Unchecked)

    def get_record_data(self):
        return {field: self.get_input_value(input_widget) for field, input_widget in self.field_name_to_input_widgets.items()}

    def get_input_value(self, input_widget):
        if isinstance(input_widget, QtWidgets.QComboBox):
            return input_widget.currentData() or input_widget.currentText()
        elif isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
            return input_widget.value()
        elif isinstance(input_widget, QtWidgets.QLineEdit):
            return input_widget.text() or None
        elif isinstance(input_widget, QtWidgets.QDateTimeEdit):
            return input_widget.dateTime().toString("yyyy-MM-dd HH:mm:ss") if input_widget.dateTime() != input_widget.minimumDateTime() else None
        elif isinstance(input_widget, FileBrowseWidget):
            return input_widget.get_value() or None
        elif isinstance(input_widget, QtWidgets.QListWidget):
            # Retrieve the checked items from the QListWidget
            selected_items = []
            for index in range(input_widget.count()):
                item = input_widget.item(index)
                if item.checkState() == QtCore.Qt.Checked:
                    selected_items.append(item.data(QtCore.Qt.ItemDataRole.UserRole) or item.text())
            return selected_items

        return None

    def create_many_to_many_widget(self, many_to_many_field: 'ManyToManyField'):
        """Create a QListWidget with checkable items for a many-to-many relationship."""
        widget = QtWidgets.QListWidget()

        fks = self.db_manager.get_foreign_keys(many_to_many_field.junction_table)
        for fk in fks:
            if fk.table == self.table_name:
                from_table_fk = fk
            else:
                to_table_fk = fk

        # Get all possible related records
        display_field = self.db_manager.get_display_field(self.table_name, many_to_many_field.track_field_name)
        related_records = self.db_manager.query_table_data(
            to_table_fk.table,
            fields=[from_table_fk.to_field, display_field],
            as_dict=True
        )

        # Add items to the list widget
        for record in related_records:
            item = QtWidgets.QListWidgetItem(record[display_field])
            item.setData(QtCore.Qt.UserRole, record[from_table_fk.to_field])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            widget.addItem(item)

        return widget

class DatabaseViewWidget(DataViewWidget):

    LABEL: str = 'Database View'

    def __init__(self, db_manager: 'DatabaseManager' = None, parent: QtWidgets.QWidget = None, identifier: Optional[str] = None):
        super().__init__(parent, identifier)

        # Store the arguments
        self.db_manager = db_manager

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._current_table = ''
        self.active_filter_columns = set()  # Keep track of columns with active filters

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.add_record_button = QtWidgets.QPushButton(TablerQIcon.file_plus, 'Add Record')
        self.delete_record_button = QtWidgets.QPushButton(TablerQIcon.file_minus, 'Delete Record')

        self.general_tool_bar.addWidget(self.add_record_button)
        self.general_tool_bar.addWidget(self.delete_record_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.add_filter_button.clicked.connect(self.show_column_selection_menu)
        self.filter_bar_widget.filter_widget_removed.connect(self.active_filter_columns.discard)
        self.add_record_button.clicked.connect(self.show_add_record_dialog)
        self.delete_record_button.clicked.connect(self.delete_record)
        self.tree_widget.itemDoubleClicked.connect(self.edit_record)

    @staticmethod
    def generate_sql_query(column_name: str, filter_condition: 'FilterCondition', values: Tuple) -> str:
        """Generate an SQL query string for a given column and filter condition.

        Args:
            column_name (str): The name of the column to filter.
            filter_condition (FilterCondition): The filter condition to apply.
            values (Tuple): The values to use in the filter.

        Returns:
            str: An SQL query string.
        """
        return filter_condition.query_format.format(column=column_name)

    def set_database_manager(self, db_manager: 'DatabaseManager'):
        """Set the database manager for handling database operations.
        """
        self.db_manager = db_manager

    def set_table(self, table_name: str):
        """Set the current table and load its data.
        """
        self._current_table = table_name
        self.load_table_data()

    def load_table_data(self):
        """Load the data for the current table into the tree widget.
        """
        if not self.db_manager or not self._current_table:
            return

        primary_key = self.db_manager.get_primary_keys(self._current_table)
        fields = self.db_manager.get_field_names(self._current_table)
        many_to_many_field_names = self.db_manager.get_many_to_many_field_names(self._current_table)

        if not primary_key:
            primary_key = 'rowid'
            fields.insert(0, primary_key)

        self.tree_widget.clear()
        self.tree_widget.set_primary_key(primary_key)
        self.tree_widget.setHeaderLabels(fields + many_to_many_field_names)
        generator = self.db_manager.query_table_data(
            self._current_table, 
            fields + many_to_many_field_names, 
            as_dict=True, 
            handle_m2m=True
        )
        self.tree_widget.set_generator(generator)

    def show_add_record_dialog(self):
        """Show the dialog to add a new record to the current table.
        """
        if not self._current_table:
            return

        dialog = AddEditRecordDialog(self.db_manager, self._current_table, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.load_table_data()

    def edit_record(self, item: 'TreeWidgetItem', column):
        """Edit the selected record from the tree widget.
        """
        row_data = {self.tree_widget.headerItem().text(col): item.get_value(col) for col in range(self.tree_widget.columnCount())}
        dialog = AddEditRecordDialog(self.db_manager, self._current_table, row_data, self)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.load_table_data()

    # TODO: Add support composite pks
    def delete_record(self):
        """Delete the selected record from the database, supporting composite primary keys."""
        if not self._current_table:
            return

        if not (current_item := self.tree_widget.currentItem()):
            return

        # Get the primary key fields and their values
        pk_fields = self.db_manager.get_primary_keys(self._current_table)
        pk_values = {pk_field: current_item[pk_field] for pk_field in pk_fields}

        # Construct a human-readable representation of the primary key(s) for the confirmation dialog
        pk_display = ", ".join(f"{field}: '{value}'" for field, value in pk_values.items())

        # Show confirmation dialog
        confirm = QtWidgets.QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the record with {pk_display}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if confirm == QtWidgets.QMessageBox.Yes:
            self.db_manager.delete_record(self._current_table, pk_values)
            self.load_table_data()

    def show_column_selection_menu(self):
        """Show a context menu with available columns for creating filters.
        """
        menu = QtWidgets.QMenu(self)

        for column in self.tree_widget.column_names:
            # Only add columns to the menu that don't already have an active filter
            if column not in self.active_filter_columns:
                action = menu.addAction(column)
                action.triggered.connect(partial(self.create_filter_widget, column))

        menu.exec_(QtGui.QCursor.pos())

    def create_filter_widget(self, column_name: str):
        """Create a filter widget based on the selected column and its data type.
        """
        # Get field information for the column
        field_info = self.db_manager.get_field(self._current_table, column_name)

        # TODO: Store relation path in header item to be extract from item directly instead of extract from split '.'
        # Check if the column is a foreign key or a many-to-many field
        if '.' in column_name or field_info.is_foreign_key or field_info.is_many_to_many:
            # Handle relation columns
            if '.' in column_name:
                # TODO: Handle the column based on its type if it is not TEXT
                # The column represents a relation, split to get the table and field names
                related_table, display_field = column_name.split('.')
            elif field_info.is_foreign_key:
                related_table = field_info.fk.table
                display_field = None
            elif field_info.is_many_to_many:
                # Handle many-to-many relationship fields
                fks = self.db_manager.get_foreign_keys(field_info.m2m.junction_table)
                for fk in fks:
                    if fk.table != self._current_table:
                        to_table_fk = fk
                        break
                related_table = to_table_fk.table
                display_field = to_table_fk.to_field

            # Fetch possible values from the related table
            possible_values = self.db_manager.get_possible_values(related_table, display_field=display_field)

            # Create a MultiSelectFilterWidget with the possible values
            filter_widget = widgets.MultiSelectFilterWidget(filter_name=column_name)
            filter_widget.add_items(possible_values)
        else:
            # Use ColumnType enum to map SQL type to appropriate filter widget
            column_type = ColumnType.from_sql(field_info.type)

            # Get the filter widget class associated with the column type
            filter_widget_cls = column_type.filter_widget

            # Instantiate the filter widget
            filter_widget = filter_widget_cls(filter_name=column_name)

        if filter_widget:
            self.add_filter_widget(filter_widget)
            self.active_filter_columns.add(column_name)  # Mark this column as having an active filter

    def activate_filter(self):
        """Logic to filter data based on active filters and populate the tree widget."""
        ...

# Main Function
# -------------
def main():
    """Create the application and main window, and show the widget.
    """
    import sys
    from blackboard.utils.file_path_utils import FilePatternQuery

    # Create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    # Set theme of QApplication to the dark theme
    bb.theme.set_theme(app, 'dark')

    # Mock up data
    pattern = "blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/{asset_type}"
    work_file_query = FilePatternQuery(pattern)
    filters = {
        'project_name': ['ProjectA'],
        'shot_name': ['shot01', 'shot02'],
    }
    generator = work_file_query.query_files(filters)

    # Create an instance of the widget
    database_view_widget = DataViewWidget()
    database_view_widget.tree_widget.setHeaderLabels(['id'] + work_file_query.fields)
    database_view_widget.search_edit.skip_columns.add(database_view_widget.tree_widget.get_column_index('id'))
    database_view_widget.tree_widget.create_thumbnail_column('file_path')
    database_view_widget.tree_widget.set_generator(generator)

    # Date Filter Setup
    date_filter_widget = widgets.DateRangeFilterWidget(filter_name="Date")
    date_filter_widget.activated.connect(print)
    # Shot Filter Setup
    shot_filter_widget = widgets.MultiSelectFilterWidget(filter_name="Shot")
    sequence_to_shots = {
        "100": [
            "100_010_001", 
            "100_020_050",
        ],
        "101": [
            "101_022_232", 
            "101_023_200",
        ],
    }
    shot_filter_widget.add_items(sequence_to_shots)
    shot_filter_widget.activated.connect(print)

    # File Type Filter Setup
    file_type_filter_widget = widgets.FileTypeFilterWidget(filter_name="File Type")
    file_type_filter_widget.activated.connect(print)

    show_hidden_filter_widget = widgets.BooleanFilterWidget(filter_name='Show Hidden')
    show_hidden_filter_widget.activated.connect(print)

    # Filter bar
    database_view_widget.add_filter_widget(date_filter_widget)
    database_view_widget.add_filter_widget(shot_filter_widget)
    database_view_widget.add_filter_widget(file_type_filter_widget)
    database_view_widget.add_filter_widget(show_hidden_filter_widget)

    # Create the scalable view and set the tree widget as its central widget
    scalable_view = widgets.ScalableView(widget=database_view_widget)

    # Show the widget
    scalable_view.show()

    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
