# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, List, Type, Tuple, Union
if TYPE_CHECKING:
    from blackboard.utils.database import AbstractModel, DatabaseManager, ManyToManyField, FieldInfo
    from blackboard.widgets.groupable_tree_widget import TreeWidgetItem
    from blackboard.widgets.filter_widget import FilterCondition, FilterWidget

# Standard Library Imports
# ------------------------
import uuid
from enum import Enum
from functools import partial
import ast
import operator
import re

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets
from blackboard.widgets.filter_widget import FilterCondition


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
        self.top_bar_area_layout.addWidget(self.filter_bar_widget, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.top_bar_area_layout.addWidget(self.search_edit, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # Add [W3], [W4] to [L2]
        # Add left general tool bar and right view tool bar
        self.utility_area_layout.addWidget(self.general_tool_bar, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.utility_area_layout.addWidget(self.view_tool_bar, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # Add [W5] to [L3]
        # Add tree widget to main tree widget
        self.main_view_layout.addWidget(self.tree_widget)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.view_tool_bar.refresh_action.triggered.connect(self.activate_filter)
        bb.utils.KeyBinder.bind_key('Ctrl+F', self.tree_widget, self.search_edit.set_text_as_selection)

    # Public Methods
    # --------------
    def add_filter_widget(self, filter_widget: 'FilterWidget'):
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
    def __init__(self, db_manager: 'DatabaseManager', model: 'AbstractModel', data_dict: dict = None, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.model = model
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
        self.field_name_to_info = self.model.get_fields()
        self.many_to_many_fields = self.model.get_many_to_many_fields()

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
        layout.addWidget(self.submit_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

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
            pk_field = self.model.get_primary_keys()[0]
            pk_value = self.data_dict.get(pk_field)

            self.model.update_record(updated_data_dict, pk_value, pk_field, handle_m2m=bool(self.many_to_many_fields))

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
            self.model.insert_record(data_filtered, handle_m2m=bool(self.many_to_many_fields))

        self.accept()

    def create_input_widget(self, field_info: 'FieldInfo'):
        if field_info.is_foreign_key:
            # Handle foreign keys by offering a dropdown of related records
            fk = field_info.fk
            referenced_model = self.db_manager.get_model(fk.referenced_table)
            display_field = self.model.get_display_field(field_info.name)
            display_field_info = referenced_model.get_field(display_field)

            if display_field:
                related_records = list(referenced_model.query(fields=[fk.referenced_field, display_field], as_dict=True))

                widget = QtWidgets.QComboBox()
                for record in related_records:
                    if not display_field_info.is_unique:
                        display_value = self.format_combined_display(record[display_field], record[fk.referenced_field], fk.referenced_field)
                    else:
                        display_value = record[display_field]

                    key_value = record[fk.referenced_field]
                    widget.addItem(display_value, key_value)

                return widget

        if enum_table_name := self.db_manager.get_enum_table_name(self.model.name, field_info.name):
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
        """Format the display field combined with the key value and key name.
        """
        return f"{display_value} ({key_name}: {key_value})"

    def set_input_value(self, field_name, value):
        input_widget = self.field_name_to_input_widgets.get(field_name)
        field_info = self.field_name_to_info.get(field_name)

        if isinstance(input_widget, QtWidgets.QComboBox):
            if field_info and field_info.is_foreign_key:
                # If the field is a foreign key, find the corresponding display value
                fk = field_info.fk
                referenced_model = self.db_manager.get_model(fk.referenced_table)
                display_field = self.model.get_display_field(field_info.name)
                display_field_info = referenced_model.get_field(display_field)

                if display_field:
                    display_text = referenced_model.fetch_one(display_field, fk.referenced_field, value)
                    display_text = self.format_combined_display(display_text, value, fk.referenced_field) if display_field_info.is_unique else display_text

                    input_widget.setCurrentText(display_text)
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
        """Create a QListWidget with checkable items for a many-to-many relationship.
        """
        widget = QtWidgets.QListWidget()

        # Get all possible related records
        display_field = self.model.get_display_field(many_to_many_field.track_field_name)
        referenced_model = self.db_manager.get_model(many_to_many_field.remote_fk.referenced_table)
        related_records = referenced_model.query(
            fields=[many_to_many_field.local_fk.referenced_field, display_field],
            as_dict=True
        )

        # Add items to the list widget
        for record in related_records:
            item = QtWidgets.QListWidgetItem(record[display_field])
            item.setData(QtCore.Qt.UserRole, record[many_to_many_field.local_fk.referenced_field])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            widget.addItem(item)

        return widget

# NOTE: WIP
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

class FunctionalColumnDialog(QtWidgets.QDialog):
    def __init__(self, db_manager, model, sample_data, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.model = model
        self.sample_data = sample_data
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Create Functional Column")
        layout = QtWidgets.QVBoxLayout(self)

        # Column Selector
        self.column_selector = QtWidgets.QListWidget()
        self.column_selector.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.column_selector.addItems(self.model.get_field_names())
        layout.addWidget(QtWidgets.QLabel("Select Columns:"))
        layout.addWidget(self.column_selector)

        # Function Input
        self.function_input = QtWidgets.QLineEdit()
        self.function_input.setPlaceholderText("Enter function, e.g., <col1> - <col2>")
        layout.addWidget(QtWidgets.QLabel("Define Function:"))
        layout.addWidget(self.function_input)

        # Tree Widget for Preview
        self.preview_tree = QtWidgets.QTreeWidget()
        self.preview_tree.setColumnCount(len(self.sample_data[0]) + 1)  # +1 for the new column
        self.preview_tree.setHeaderLabels(list(self.sample_data[0].keys()) + ['New Column'])
        layout.addWidget(QtWidgets.QLabel("Preview:"))
        layout.addWidget(self.preview_tree)

        # Buttons
        self.create_button = QtWidgets.QPushButton("Create Column")
        self.create_button.clicked.connect(self.create_column)
        layout.addWidget(self.create_button)

        # Connect signals
        self.column_selector.itemSelectionChanged.connect(self.update_preview)
        self.function_input.textChanged.connect(self.auto_select_columns)
        self.function_input.textChanged.connect(self.update_preview)

        # Initial Preview
        self.update_preview()

    def auto_select_columns(self):
        """Automatically select columns in the list based on the function input."""
        function_text = self.function_input.text()
        used_columns = self.extract_used_columns(function_text)

        # Auto-select columns in the list widget
        for i in range(self.column_selector.count()):
            item = self.column_selector.item(i)
            item.setSelected(item.text() in used_columns)

    def extract_used_columns(self, function_text):
        """Extract column names used in the function."""
        # Use regex to find patterns like <col_name>
        return set(re.findall(r"<(.*?)>", function_text))

    def update_preview(self):
        """Update the tree preview of the functional column based on sample data."""
        selected_columns = [item.text() for item in self.column_selector.selectedItems()]
        function_text = self.function_input.text()

        # Clear previous items
        self.preview_tree.clear()

        # Check if the function is valid and safe
        try:
            for row in self.sample_data:
                preview_row = {col: row[col] for col in selected_columns if col in row}
                result = self.evaluate_function(function_text, preview_row)
                
                # Create tree widget items for each row
                item = QtWidgets.QTreeWidgetItem([str(row[col]) for col in row.keys()] + [str(result)])
                self.preview_tree.addTopLevelItem(item)

        except Exception as e:
            error_item = QtWidgets.QTreeWidgetItem(["Error: " + str(e)])
            self.preview_tree.addTopLevelItem(error_item)

    def evaluate_function(self, function_text, row):
        """Evaluate the function safely using the provided row data."""
        for col, value in row.items():
            function_text = function_text.replace(f"<{col}>", str(value))

        node = ast.parse(function_text, mode='eval')
        return self.safe_eval(node.body)

    def safe_eval(self, node):
        """Evaluate an expression node safely."""
        if isinstance(node, ast.BinOp):
            left = self.safe_eval(node.left)
            right = self.safe_eval(node.right)
            operator_func = SAFE_OPERATORS.get(type(node.op))
            if operator_func:
                return operator_func(left, right)
        elif isinstance(node, ast.Num):
            return node.n
        raise ValueError("Invalid expression")

    def create_column(self):
        """Create the new functional column in the database."""
        column_name, ok = QtWidgets.QInputDialog.getText(self, "Column Name", "Enter name for new column:")
        if ok and column_name:
            QtWidgets.QMessageBox.information(self, "Success", f"Column '{column_name}' created successfully.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Column creation cancelled.")

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
        self._visible_filter_columns = set()
        self._column_to_relation_chain_dict: Dict[str, str] = {}

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.add_relation_column_menu = self.tree_widget.header_menu.addMenu('Add Relation Column')
        self.add_functional_column_action = self.tree_widget.header_menu.addAction('Add Functional Column')

        self.add_record_button = QtWidgets.QPushButton(TablerQIcon.file_plus, 'Add Record')
        self.delete_record_button = QtWidgets.QPushButton(TablerQIcon.file_minus, 'Delete Record')

        self.general_tool_bar.addWidget(self.add_record_button)
        self.general_tool_bar.addWidget(self.delete_record_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.add_filter_button.clicked.connect(self.show_column_selection_menu)
        self.filter_bar_widget.filter_widget_removed.connect(self._visible_filter_columns.discard)
        self.tree_widget.about_to_show_header_menu.connect(self.handle_header_context_menu)
        self.add_record_button.clicked.connect(self.show_add_record_dialog)
        self.delete_record_button.clicked.connect(self.delete_record)
        self.tree_widget.itemDoubleClicked.connect(self.edit_record)

        # NOTE: WIP
        self.add_functional_column_action.triggered.connect(self.open_functional_column_dialog)

    def handle_header_context_menu(self, column_index: int):
        """Handle the header context menu signal.

        Args:
            column_index (int): The index of the column where the context menu was requested.
        """
        self.add_relation_column_menu.clear()
        self.add_relation_column_menu.setDisabled(True)

        if not self._current_table:
            return

        # Determine the current table based on the selected column's header
        tree_column_name = self.tree_widget.column_names[column_index]

        # TODO: Store relation path in header item to be extract from item directly
        # Check if the column header includes a related table
        if '.' in tree_column_name:
            # The column represents a relation, split to get the table name
            local_table, local_field = tree_column_name.split('.')
        else:
            # Use the original current table
            local_table = self._current_table
            local_field = tree_column_name

        local_model = self.db_manager.get_model(local_table)

        # Get foreign key information for the determined table
        related_fk = local_model.get_foreign_key(local_field)

        # Check for many-to-many fields if no direct foreign key was found
        if not related_fk:
            # TODO: Handle m2m > relation > relation
            many_to_many_fields = local_model.get_many_to_many_fields()

            if local_field in many_to_many_fields:
                m2m_field = many_to_many_fields[local_field]

                remote_model = self.db_manager.get_model(m2m_field.remote_table)

                # Get the related fields from the 'to' table
                related_field_names = remote_model.get_field_names()

                # Add actions for each field in the related table to handle m2m relation columns
                for display_field in related_field_names[1:]:
                    display_column_label = f"{m2m_field.remote_table}.{display_field}"
                    action = QtWidgets.QAction(display_column_label, self)

                    # Connect the action to the m2m-specific add relation function
                    action.triggered.connect(
                        partial(self.add_relation_column_m2m, local_table, display_field, m2m_field, display_column_label)
                    )

                    self.add_relation_column_menu.addAction(action)

                self.add_relation_column_menu.setEnabled(True)
            return

        # If a direct foreign key relation is found, handle it as before
        referenced_table = related_fk.referenced_table
        referenced_field = related_fk.referenced_field

        referenced_model = self.db_manager.get_model(referenced_table)

        # Retrieve fields from the related table
        related_field_names = referenced_model.get_field_names()

        # Create a menu action for each foreign key relation
        for display_field in related_field_names[1:]:
            action = QtWidgets.QAction(f"{referenced_table}.{display_field}", self)

            # Pass the correct arguments to add_relation_column
            action.triggered.connect(
                partial(self.add_relation_column, local_table, referenced_table, display_field, local_field, referenced_field)
            )

            self.add_relation_column_menu.addAction(action)

        self.add_relation_column_menu.setEnabled(True)

    @staticmethod
    def generate_sql_query(column_name: str, filter_condition: 'FilterCondition', values: Tuple) -> str:
        """Generate an SQL condition string for a given column and filter condition.

        Args:
            column_name (str): The name of the column to filter.
            filter_condition (FilterCondition): The filter condition to apply.
            values (Tuple): The values to use in the filter.

        Returns:
            str: An SQL condition string.
        """
        if filter_condition in (FilterCondition.IN, FilterCondition.NOT_IN):
            placeholders = ', '.join('?' for _ in values)
            sql_condition = filter_condition.sql_format.format(column=column_name, placeholders=placeholders)
        else:
            sql_condition = filter_condition.sql_format.format(column=column_name)
        return sql_condition

    # NOTE: WIP
    def open_functional_column_dialog(self):
        """Open the Functional Column Dialog to create a new column.
        """
        if not self._current_table:
            QtWidgets.QMessageBox.warning(self, "Error", "No table selected.")
            return

        # Fetch sample data for preview (e.g., first 5 rows)
        sample_data = list(self._current_model.query(as_dict=True))[:5]

        # Create and show the Functional Column Dialog
        dialog = FunctionalColumnDialog(self.db_manager, self._current_model, sample_data, self)
        dialog.exec_()

    def set_database_manager(self, db_manager: 'DatabaseManager'):
        """Set the database manager for handling database operations.
        """
        self.db_manager = db_manager

    def set_table(self, table_name: str):
        """Set the current table and load its data.
        """
        self._current_table = table_name
        self._current_model = self.db_manager.get_model(table_name)
        self.load_table_data()

    def load_table_data(self):
        """Load the data for the current table into the tree widget.
        """
        if not self.db_manager or not self._current_table:
            return

        primary_key = self._current_model.get_primary_keys()
        fields = self._current_model.get_field_names()
        many_to_many_field_names = self._current_model.get_many_to_many_field_names()

        if not primary_key:
            primary_key = 'rowid'
            fields.insert(0, primary_key)

        self.tree_widget.clear()
        self.tree_widget.set_primary_key(primary_key)
        self.tree_widget.setHeaderLabels(fields + many_to_many_field_names)
        generator = self._current_model.query(
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

        dialog = AddEditRecordDialog(self.db_manager, self._current_model, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.load_table_data()

    def edit_record(self, item: 'TreeWidgetItem', column):
        """Edit the selected record from the tree widget.
        """
        row_data = {self.tree_widget.headerItem().text(col): item.get_value(col) for col in range(self.tree_widget.columnCount())}
        dialog = AddEditRecordDialog(self.db_manager, self._current_model, row_data, self)

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
        pk_fields = self._current_model.get_primary_keys()
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
            self._current_model.delete_record(pk_values)
            self.load_table_data()

    def show_column_selection_menu(self):
        """Show a context menu with available columns for creating filters.
        """
        menu = QtWidgets.QMenu(self)

        for column in self.tree_widget.column_names:
            # Only add columns to the menu that don't already have an active filter
            if column not in self._visible_filter_columns:
                action = menu.addAction(column)
                action.triggered.connect(partial(self.create_filter_widget, column))

        menu.exec_(QtGui.QCursor.pos())

    def create_filter_widget(self, column_name: str):
        """Create a filter widget based on the selected column and its data type.
        """
        is_relation_column = False

        # TODO: Store relation chain in header item to be extract from item directly instead of extract from split '.'
        if '.' in column_name:
            # The column represents a relation, split to get the table and field names
            related_table, display_field = column_name.split('.')
            is_relation_column = True
        else:
            # Get field information for the column
            field_info = self._current_model.get_field(column_name)

            # Handle relation columns
            if field_info.is_foreign_key:
                related_table = field_info.fk.referenced_table
                display_field = None
                is_relation_column = True
            elif field_info.is_many_to_many:
                # Handle many-to-many relationship fields
                related_table = field_info.m2m.remote_table
                display_field = field_info.m2m.remote_fk.referenced_field
                is_relation_column = True

        # Check if the column is a foreign key or a many-to-many field
        if is_relation_column:
            # TODO: Handle the column based on its type if it is not TEXT
            # Fetch possible values from the related table
            related_model = self.db_manager.get_model(related_table)
            possible_values = related_model.get_possible_values(display_field)

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
            self._visible_filter_columns.add(column_name)

    def add_relation_column(self, local_table: str, referenced_table: str, display_field: str, local_field: str, referenced_field: str):
        """Add a relation column to the tree widget.

        Args:
            local_table (str): The table from which the relation is originating.
            referenced_table (str): The name of the related table to join.
            display_field (str): The column from the related table to display.
            local_field (str): The foreign key field in the current table.
            referenced_field (str): The primary key field in the related table.
        """
        current_column_names = self.tree_widget.column_names.copy()

        # Check if the related column header already exists
        target_column_name = f"{referenced_table}.{display_field}"
        if target_column_name not in current_column_names:
            current_column_names.append(target_column_name)
            self.tree_widget.setHeaderLabels(current_column_names)

        # TODO: Set `relation_chain` in tooltip of header column
        column_name = local_field if local_table == self._current_table else f'{local_table}.{local_field}'
        relation_chain = self._column_to_relation_chain_dict.get(column_name, f'{local_table}.{local_field}')
        relation_chain +=  f'.{display_field}'
        self._column_to_relation_chain_dict[target_column_name] = relation_chain

        local_model = self.db_manager.get_model(local_table)
        referenced_model = self.db_manager.get_model(referenced_table)

        # Fetch data from the current table
        data_tuples = local_model.query(fields=[local_field])

        # Update the tree widget with the new column data
        for i, data_tuple in enumerate(list(data_tuples)):
            target_value = referenced_model.fetch_one(display_field, referenced_field, data_tuple[0])

            # TODO: Handle when grouping
            item: 'TreeWidgetItem' = self.tree_widget.topLevelItem(i)
            if item:
                item.set_value(target_column_name, target_value)

    def add_relation_column_m2m(self, local_table: str, display_field: str, m2m_field: 'ManyToManyField', display_column_label: str):
        """Add a many-to-many relation column to the tree widget.

        Args:
            local_table (str): The name of the originating table.
            display_field (str): The field in the related table to display.
            m2m_field (ManyToManyField): The ManyToManyField object containing information about the relationship.
        """
        current_column_names = self.tree_widget.column_names.copy()

        # Check if the related column header already exists
        if display_column_label not in current_column_names:
            current_column_names.append(display_column_label)
            self.tree_widget.setHeaderLabels(current_column_names)

        local_model = self.db_manager.get_model(local_table)
        data_dicts = local_model.get_many_to_many_data(m2m_field.track_field_name, display_field=display_field, display_field_label=display_column_label)
        for data_dict in data_dicts:
            self.tree_widget.update_item(data_dict)

    def activate_filter(self):
        """Apply the active filters to the database query and update the tree widget.
        """
        if not self._current_table or not self.db_manager:
            return

        # Start building the WHERE clause
        where_clauses = []
        parameters = []

        # Iterate over all active filter widgets
        for filter_widget in self.filter_bar_widget.get_active_filters():
            column_name = filter_widget.filter_name

            # TODO: Handle on relation column
            #       WIP
            relation_chain = self._column_to_relation_chain_dict.get(column_name)
            if relation_chain:
                print(relation_chain)
                local_table, *relation_fields = relation_chain.split('.')

                local_model = self.db_manager.get_model(local_table)

                for field in relation_fields:
                    fk = local_model.get_foreign_key(field)

                print(local_table)
                print(relation_fields)
            # ---

            # Get field information for the column
            field_info = self._current_model.get_field(column_name)
            if not field_info:
                continue  # Skip if field info is not available

            # Get the filter condition and values from the filter widget
            filter_condition = filter_widget.get_filter_condition()
            values = filter_widget.filtered_list

            if not filter_condition or values is None:
                continue  # Skip if there's no condition or values

            # Generate the SQL condition for this filter
            sql_condition = self.generate_sql_query(column_name, filter_condition, values)

            # Add to the WHERE clauses
            where_clauses.append(sql_condition)

            # Add the values to the parameters list
            parameters.extend(values)

        # Build the final WHERE clause
        where_clause = " AND ".join(where_clauses) if where_clauses else ""

        # Get the fields to select
        fields = self._current_model.get_field_names()
        many_to_many_field_names = self._current_model.get_many_to_many_field_names()
        all_fields = fields + many_to_many_field_names

        # Execute the query
        results = self._current_model.query(
            fields=all_fields,
            where_clause=where_clause,
            parameters=parameters,
            as_dict=True,
            handle_m2m=True
        )

        # Clear the tree widget and populate with new data
        self.tree_widget.clear()
        self.tree_widget.setHeaderLabels(all_fields)
        self.tree_widget.set_generator(results)

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
