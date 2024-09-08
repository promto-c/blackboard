# Type Checking Imports
# ---------------------
from typing import List, Tuple, Optional, Dict

# Standard Library Imports
# ------------------------
import os
import sys
from functools import partial
import ast
import operator
import re

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.utils.database_manager import DatabaseManager, FieldInfo, ManyToManyField
from blackboard.widgets.main_window import MainWindow
from blackboard.widgets import TreeWidgetItem, DatabaseViewWidget
from blackboard.widgets.header_view import SearchableHeaderView
from blackboard.widgets.list_widget import EnumListWidget
from blackboard.widgets.label import LabelEmbedderWidget
from blackboard.widgets.button import ItemOverlayButton


# Class Definitions
# -----------------

class AddTableDialog(QtWidgets.QDialog):
    """
    UI Design:
    
    +--------------------------------------+
    |           Add Table                  |
    +--------------------------------------+
    | Table Name: [____________________]   |
    |                                      |
    | Primary Key Field:                   |
    |                                      |
    |   Name: [____________________]       |
    |   Type: [INTEGER      v]             |
    |                                      |
    | [ Create Table ]                     |
    +--------------------------------------+
    
    UI Components:
    - Table Name Input: QLineEdit for entering the table name.
    - Primary Key Field: Inputs for defining the primary key field:
      - Name: QLineEdit for the primary key field name.
      - Type: QComboBox for selecting the data type (e.g., INTEGER).
      - Autoincrement: QCheckBox for enabling auto-increment if the type is INTEGER.
    - Create Table Button: QPushButton to create the table with the primary key field.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.db_manager = db_manager

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle("Add Table")

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        # Table Name Section
        self.table_name_input = QtWidgets.QLineEdit()
        self.table_name_label = LabelEmbedderWidget(self.table_name_input, "Table Name")

        # Primary Key Field Section
        self.primary_key_name_input = QtWidgets.QLineEdit("id")
        self.primary_key_name_label = LabelEmbedderWidget(self.primary_key_name_input, "Primary Key Name")

        self.primary_key_type_dropdown = QtWidgets.QComboBox()
        self.primary_key_type_dropdown.addItems(DatabaseManager.PRIMARY_KEY_TYPES)
        self.primary_key_type_label = LabelEmbedderWidget(self.primary_key_type_dropdown, "Type")

        # Create Table Button
        self.create_table_button = QtWidgets.QPushButton("Create Table")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.table_name_label)
        layout.addWidget(self.primary_key_name_label)
        layout.addWidget(self.primary_key_type_label)
        layout.addStretch()
        layout.addWidget(self.create_table_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.create_table_button.clicked.connect(self.add_table)

    # Public Methods
    # --------------
    def add_table(self):
        table_name = self.table_name_input.text()
        primary_key_name = self.primary_key_name_input.text()
        primary_key_type = self.primary_key_type_dropdown.currentText()

        primary_key_definition = f"{primary_key_type} PRIMARY KEY".strip()

        self.db_manager.create_table(table_name, {primary_key_name: primary_key_definition})

        self.accept()

class AddFieldDialog(QtWidgets.QDialog):
    """
    UI Design:
    
    +--------------------------------------+
    |              Add Field               |
    +--------------------------------------+
    | Field Name: [____________________]   |
    |                                      |
    | Field Type: [INTEGER      v]         |
    |                                      |
    | [ ] NOT NULL                         |
    |                                      |
    | Select Enum Table:                   |
    | [enum_table_dropdown]                |
    |                                      |
    | Enum Values:                         |
    | +----------------------------+       |
    | | [Value 1         ] [ - ] [^] [v]   |
    | | [Value 2         ] [ - ] [^] [v]   |
    | | [Value 3         ] [ - ] [^] [v]   |
    | +----------------------------+       |
    | [ Add New Value ]                    |
    |                                      |
    |                (Add Button)          |
    |                [ Add Field ]         |
    +--------------------------------------+
    """

    WINDOW_TITLE = 'Add Field'

    def __init__(self, db_manager: DatabaseManager, table_name: str, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.db_manager = db_manager
        self.table_name = table_name

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.existing_enum_tables = ["Create New Enum Table"] + self.db_manager.get_existing_enum_tables()
        self.use_existing_enum = False

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle(self.WINDOW_TITLE)

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        self.field_name_input = QtWidgets.QLineEdit()
        self.field_name_label = LabelEmbedderWidget(self.field_name_input, "Field Name")

        self.field_type_dropdown = QtWidgets.QComboBox()
        self.field_type_dropdown.addItems(DatabaseManager.FIELD_TYPES)
        self.field_type_label = LabelEmbedderWidget(self.field_type_dropdown, "Field Type")

        self.enum_table_dropdown = QtWidgets.QComboBox()
        self.enum_table_dropdown.addItems(self.existing_enum_tables)
        self.enum_table_label = LabelEmbedderWidget(self.enum_table_dropdown, "Enum Table")

        self.enum_list_widget = EnumListWidget(self)
        self.enum_values_label = LabelEmbedderWidget(self.enum_list_widget, "Enum Values")
        self.add_enum_value_button = QtWidgets.QPushButton("Add New Value")

        self.not_null_checkbox = QtWidgets.QCheckBox("NOT NULL")
        self.unique_checkbox = QtWidgets.QCheckBox("UNIQUE")
        self.add_button = QtWidgets.QPushButton("Add Field")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.field_name_label)
        layout.addWidget(self.field_type_label)

        layout.addWidget(self.enum_table_label)
        layout.addWidget(self.enum_values_label)
        layout.addWidget(self.add_enum_value_button)
        layout.addWidget(self.not_null_checkbox)
        layout.addWidget(self.unique_checkbox)

        layout.addStretch()
        layout.addWidget(self.add_button)
        
        # Hide enum-related fields by default
        self.toggle_enum_fields(False)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.field_name_input.textChanged.connect(lambda text: self.add_button.setEnabled(bool(text)))
        self.field_type_dropdown.currentTextChanged.connect(self.toggle_enum_input)
        self.enum_table_dropdown.currentIndexChanged.connect(self.update_enum_list_based_on_selection)
        self.add_enum_value_button.clicked.connect(lambda: self.enum_list_widget.add_item())
        self.add_button.clicked.connect(self.add_field)

        self.add_button.setEnabled(False)

    # Public Methods
    # --------------
    def toggle_enum_input(self, field_type):
        is_enum = field_type == "ENUM"
        self.toggle_enum_fields(is_enum)

    def toggle_enum_fields(self, visible):
        self.enum_table_label.setVisible(visible)
        self.enum_values_label.setVisible(visible)
        self.add_enum_value_button.setVisible(visible and not self.use_existing_enum)

    def update_enum_list_based_on_selection(self):
        selected_enum_table = self.enum_table_dropdown.currentText()
        if selected_enum_table == "Create New Enum Table":
            self.use_existing_enum = False
            self.enum_list_widget.clear()
            self.enum_list_widget.setEnabled(True)
        else:
            self.use_existing_enum = True
            enum_values = self.db_manager.get_enum_values(selected_enum_table)
            self.enum_list_widget.set_values(enum_values)
            self.enum_list_widget.setDisabled(True)
        self.toggle_enum_fields(True)

    def add_field(self):
        field_name = self.field_name_input.text().strip()
        field_type = self.field_type_dropdown.currentText()
        not_null = "NOT NULL" if self.not_null_checkbox.isChecked() else ""
        unique = "UNIQUE" if self.unique_checkbox.isChecked() else ""

        field_definition = ' '.join([field_type, not_null, unique])

        enum_values = None
        enum_table = None

        if field_type == "ENUM":
            if self.use_existing_enum:
                enum_table = self.enum_table_dropdown.currentText()
            else:
                enum_values = self.enum_list_widget.get_values()

        if field_name and field_definition:
            self.db_manager.add_field(
                self.table_name,
                field_name,
                field_definition,
                enum_values=enum_values,
                enum_table_name=enum_table
            )

        self.accept()

class AddRelationFieldDialog(QtWidgets.QDialog):
    """
    UI Design:
    
    +--------------------------------------+
    |          Add Relation Field          |
    +--------------------------------------+
    | Field Name: [table_field           ] |
    |                                      |
    | Reference Table: [ Table1       v]   |
    |                                      |
    | Reference Key Field: [ id       v]   |
    |                                      |
    | Reference Display Field: [ name   v] |
    |                                      |
    | [ ] NOT NULL                         |
    |                                      |
    | Relationship Type: [Many-to-One  v]  |
    |                                      |
    |                (Add Button)          |
    |       [ Add Relation Field ]         |
    +--------------------------------------+
    """

    def __init__(self, db_manager: DatabaseManager, table_name: str, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.db_manager = db_manager
        self.table_name = table_name

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle("Add Relation Field")

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        self.field_name_input = QtWidgets.QLineEdit()
        self.field_name_label = LabelEmbedderWidget(self.field_name_input, "Field Name")

        self.table_dropdown = QtWidgets.QComboBox()
        
        # Exclude current table from the list of reference tables
        table_names = self.db_manager.get_table_names()
        table_names.remove(self.table_name)
        self.table_dropdown.addItems(table_names)
        self.table_dropdown.setCurrentIndex(-1)
        self.table_label = LabelEmbedderWidget(self.table_dropdown, "Reference Table:")

        self.key_field_dropdown = QtWidgets.QComboBox()
        self.key_field_label = LabelEmbedderWidget(self.key_field_dropdown, "Reference Key Field")

        self.display_field_dropdown = QtWidgets.QComboBox()
        self.display_field_label = LabelEmbedderWidget(self.display_field_dropdown, "Reference Display Field")

        self.relationship_type_dropdown = QtWidgets.QComboBox()
        self.relationship_type_dropdown.addItems(["Many-to-One", "One-to-One"])
        self.relationship_type_label = LabelEmbedderWidget(self.relationship_type_dropdown, "Relationship Type")

        self.not_null_checkbox = QtWidgets.QCheckBox("NOT NULL")

        self.add_button = QtWidgets.QPushButton("Add Relation Field")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.field_name_label)
        layout.addWidget(self.table_label)
        layout.addWidget(self.key_field_label)
        layout.addWidget(self.display_field_label)
        layout.addWidget(self.relationship_type_label)
        layout.addWidget(self.not_null_checkbox)
        layout.addStretch()
        layout.addWidget(self.add_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.field_name_input.textChanged.connect(self._handle_add_button_state)
        self.table_dropdown.currentTextChanged.connect(self._handle_add_button_state)
        self.key_field_dropdown.currentTextChanged.connect(self._handle_add_button_state)

        self.table_dropdown.currentTextChanged.connect(self._update_fields)
        self.key_field_dropdown.currentTextChanged.connect(self._update_field_name)

        self.add_button.clicked.connect(self.add_relation_column)

        self._handle_add_button_state()

    # Public Methods
    # --------------
    def add_relation_column(self):
        field_name = self.field_name_input.text()
        reference_table = self.table_dropdown.currentText()
        key_field = self.key_field_dropdown.currentText()
        display_field = self.display_field_dropdown.currentText()
        relationship_type = self.relationship_type_dropdown.currentText()
        is_not_null = self.not_null_checkbox.isChecked()

        # Fetch the type of the referenced key field
        field_definition = self.db_manager.get_field_type(reference_table, key_field)

        if is_not_null:
            field_definition += " NOT NULL"

        if relationship_type == "Many-to-One":
            self.db_manager.add_field(
                self.table_name,
                field_name,
                field_definition,
                foreign_key=f"{reference_table}({key_field})"
            )

        elif relationship_type == "One-to-One":
            # Add the column with a UNIQUE constraint
            self.db_manager.add_field(
                self.table_name,
                field_name,
                field_definition + ' UNIQUE',
                foreign_key=f"{reference_table}({key_field})"
            )

        if display_field != key_field:
            # Store the display field information
            self.db_manager.add_display_field(self.table_name, field_name, display_field)

        self.accept()

    # Private Methods
    # ---------------
    def _handle_add_button_state(self, text: str = ''):
        if not text.strip():
            self.add_button.setDisabled(True)
        elif self.field_name_input.text() and self.table_dropdown.currentText() and self.key_field_dropdown.currentText():
            self.add_button.setEnabled(True)

    # TODO: Handle composite primary keys
    def _update_fields(self, table_name: str = None):
        table_name = table_name or self.table_dropdown.currentText()
        if not table_name:
            return

        # Retrieve primary keys and unique fields
        primary_keys = self.db_manager.get_primary_keys(table_name)
        unique_fields = self.db_manager.get_unique_fields(table_name)

        # Combine unique fields and primary keys
        reference_fields = primary_keys + unique_fields

        # Clear and populate the dropdowns
        self.key_field_dropdown.clear()
        self.key_field_dropdown.addItems(reference_fields)
        self.display_field_dropdown.clear()
        self.display_field_dropdown.addItems(reference_fields)

    def _update_field_name(self, field_name: str):
        if not field_name:
            return
        self.field_name_input.setText(f"{self.table_dropdown.currentText()}_{field_name}")

class AddManyToManyFieldDialog(QtWidgets.QDialog):
    """
    UI Design:
    
    +--------------------------------------+
    |        Add Many-to-Many Field        |
    +--------------------------------------+
    | Junction Table Name: [_____________] |
    |                                      |
    | From Table: [Table1             v]   |
    |                                      |
    | From Key Field: [id             v]   |
    |                                      |
    | From Display Field: [name       v]   |
    |                                      |
    | To Table: [Table2               v]   |
    |                                      |
    | To Key Field: [id               v]   |
    |                                      |
    | To Display Field: [name         v]   |
    |                                      |
    | Track Vice Versa: [ ]                |
    |                                      |
    |                (Add Button)          |
    |       [ Add Many-to-Many Field ]     |
    +--------------------------------------+
    """

    def __init__(self, db_manager: DatabaseManager, from_table: str, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.db_manager = db_manager
        self.from_table = from_table

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget."""
        self.setWindowTitle("Add Many-to-Many Field")

        # Create Layouts
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        self.junction_table_input = QtWidgets.QLineEdit()
        self.junction_table_label = LabelEmbedderWidget(self.junction_table_input, "Junction Table Name")

        self.from_table_dropdown = QtWidgets.QComboBox()
        self.from_table_dropdown.addItems([self.from_table])
        self.from_table_dropdown.setEnabled(False)
        self.from_key_field_dropdown = QtWidgets.QComboBox()
        self.from_display_field_dropdown = QtWidgets.QComboBox()

        self.to_table_dropdown = QtWidgets.QComboBox()
        table_names = self.db_manager.get_table_names()
        table_names.remove(self.from_table)
        self.to_table_dropdown.addItems(table_names)
        self.to_table_dropdown.setCurrentIndex(-1)
        self.to_table_label = LabelEmbedderWidget(self.to_table_dropdown, "To Table")

        self.to_key_field_dropdown = QtWidgets.QComboBox()
        self.to_display_field_dropdown = QtWidgets.QComboBox()

        self.track_vice_versa_checkbox = QtWidgets.QCheckBox("Track Vice Versa")

        self.add_button = QtWidgets.QPushButton("Add Many-to-Many Field")

        # Add Widgets to Layouts
        layout.addWidget(self.junction_table_label)
        layout.addWidget(self.from_table_dropdown)
        layout.addWidget(LabelEmbedderWidget(self.from_key_field_dropdown, "From Key Field"))
        layout.addWidget(LabelEmbedderWidget(self.from_display_field_dropdown, "From Display Field"))
        layout.addWidget(self.to_table_label)
        layout.addWidget(LabelEmbedderWidget(self.to_key_field_dropdown, "To Key Field"))
        layout.addWidget(LabelEmbedderWidget(self.to_display_field_dropdown, "To Display Field"))
        layout.addWidget(self.track_vice_versa_checkbox)
        layout.addStretch()
        layout.addWidget(self.add_button)

        # Initialize from_table key and display fields based on defaults
        self._init_from_table_fields()

    def __init_signal_connections(self):
        """Initialize signal-slot connections."""
        self.to_table_dropdown.currentTextChanged.connect(self._update_to_table_fields)
        self.add_button.clicked.connect(self.add_many_to_many_field)

    def _init_from_table_fields(self):
        """Initialize the 'from' table's key and display fields."""
        primary_keys = self.db_manager.get_primary_keys(self.from_table)
        unique_fields = self.db_manager.get_unique_fields(self.from_table)

        # Combine unique fields and primary keys
        reference_fields = primary_keys + unique_fields

        # Set default key and display fields for the "from" table
        self.from_key_field_dropdown.clear()
        self.from_key_field_dropdown.addItems(reference_fields)
        self.from_key_field_dropdown.setCurrentText('id' if 'id' in reference_fields else primary_keys[0] if primary_keys else reference_fields[0])

        self.from_display_field_dropdown.clear()
        self.from_display_field_dropdown.addItems(reference_fields)
        self.from_display_field_dropdown.setCurrentText('name' if 'name' in reference_fields else reference_fields[0])

    def _update_to_table_fields(self):
        """Update the 'to' table's key and display fields based on the selected table."""
        table_name = self.to_table_dropdown.currentText()
        if not table_name:
            return

        primary_keys = self.db_manager.get_primary_keys(table_name)
        unique_fields = self.db_manager.get_unique_fields(table_name)

        # Combine unique fields and primary keys
        reference_fields = primary_keys + unique_fields

        # Update the key and display fields for the "to" table
        self.to_key_field_dropdown.clear()
        self.to_key_field_dropdown.addItems(reference_fields)
        self.to_key_field_dropdown.setCurrentText('id' if 'id' in reference_fields else primary_keys[0] if primary_keys else reference_fields[0])

        self.to_display_field_dropdown.clear()
        self.to_display_field_dropdown.addItems(reference_fields)
        self.to_display_field_dropdown.setCurrentText('name' if 'name' in reference_fields else reference_fields[0])

    def add_many_to_many_field(self):
        """Handle adding the many-to-many relationship field."""
        junction_table_name = self.junction_table_input.text()
        to_table = self.to_table_dropdown.currentText()
        from_key_field = self.from_key_field_dropdown.currentText()
        from_display_field = self.from_display_field_dropdown.currentText()
        to_key_field = self.to_key_field_dropdown.currentText()
        to_display_field = self.to_display_field_dropdown.currentText()
        track_vice_versa = self.track_vice_versa_checkbox.isChecked()

        self.db_manager.create_junction_table(
            from_table=self.from_table,
            to_table=to_table,
            from_field=from_key_field,
            to_field=to_key_field,
            junction_table_name=junction_table_name,
            track_field_name=f"{to_table}_{to_key_field}s",
            track_field_vice_versa_name=f"{self.from_table}_{from_key_field}s",
            from_display_field=from_display_field,
            to_display_field=to_display_field,
            track_vice_versa=track_vice_versa
        )

        self.accept()

# NOTE: WIP
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

class FunctionalColumnDialog(QtWidgets.QDialog):
    def __init__(self, db_manager, table_name, sample_data, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.table_name = table_name
        self.sample_data = sample_data
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Create Functional Column")
        layout = QtWidgets.QVBoxLayout(self)

        # Column Selector
        self.column_selector = QtWidgets.QListWidget()
        self.column_selector.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.column_selector.addItems(self.db_manager.get_field_names(self.table_name))
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

class DBWidget(QtWidgets.QWidget):

    # Initialization and Setup
    # ------------------------
    def __init__(self):
        super().__init__()

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        # Attributes
        # ----------
        self.db_manager = None
        self.current_table = None
        self.field_name_to_info: Dict[str, 'FieldInfo'] = {}

        # Private Attributes
        # ------------------
        ...

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle("SQLite Database Manager")
        self.setGeometry(100, 100, 1200, 800)

        # Create Layouts
        # --------------
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Create Widgets
        # --------------
        # Create a splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.__init_left_widget()
        self.__init_data_view_widget()

        # NOTE: WIP
        add_functional_column_action = QtWidgets.QAction('Add Functional Column', self)
        add_functional_column_action.triggered.connect(self.open_functional_column_dialog)
        self.tree_data_widget.header_menu.addAction(add_functional_column_action)

        # Add Widgets to Layouts
        # ----------------------
        self.main_layout.addWidget(splitter)
        splitter.addWidget(self.left_widget)
        splitter.addWidget(self.data_view_widget)
        splitter.setStretchFactor(0, 0)  # widget_a gets a stretch factor of 1
        splitter.setStretchFactor(1, 2)  # widget_b gets a stretch factor of 2

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.open_db_button.clicked.connect(self.open_database)
        self.create_db_button.clicked.connect(self.create_database)
        self.refresh_button.clicked.connect(self.refresh_data)

        self.add_table_button.clicked.connect(self.show_add_table_dialog)
        self.delete_table_button.triggered.connect(self.delete_table)
        self.tables_list_widget.currentItemChanged.connect(self.load_table_info)

        self.add_field_button.clicked.connect(self.show_add_field_dialog)
        self.add_relation_field_button.clicked.connect(self.show_add_relation_field_dialog)
        self.add_m2m_field_button.clicked.connect(self.show_add_many_to_many_field_dialog)
        self.delete_field_button.triggered.connect(self.delete_field)

        self.tree_data_widget.about_to_show_header_menu.connect(self.handle_header_context_menu)

    def __init_left_widget(self):
        """Create and configure the left widget.
        """
        self.left_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.left_widget)

        top_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(top_layout)

        self.db_path_line_edit = QtWidgets.QLineEdit()
        self.db_path_line_edit.setReadOnly(True)
        self.db_path_label = LabelEmbedderWidget(self.db_path_line_edit, 'Database Path')

        self.open_db_button = QtWidgets.QPushButton(TablerQIcon.folder_open, '')
        self.open_db_button.setToolTip('Open Database')
        self.create_db_button = QtWidgets.QPushButton(TablerQIcon.folder_plus, '')
        self.create_db_button.setToolTip('Create Database')
        self.refresh_button = QtWidgets.QPushButton(TablerQIcon.refresh, '')
        self.refresh_button.setToolTip('Refresh')

        self.add_table_button = QtWidgets.QPushButton(TablerQIcon.plus, '')
        self.add_table_button.setToolTip('Add Table')

        self.tables_list_widget = QtWidgets.QListWidget()
        self.tables_label = LabelEmbedderWidget(self.tables_list_widget, 'Tables')
        self.tables_label.add_actions(self.add_table_button)
        self.delete_table_button = ItemOverlayButton()
        self.delete_table_button.register_to(self.tables_list_widget)

        self.add_field_button = QtWidgets.QPushButton(TablerQIcon.plus, '')
        self.add_field_button.setToolTip('Add Field')
        self.add_relation_field_button = QtWidgets.QPushButton(TablerQIcon.link_plus, '')
        self.add_relation_field_button.setToolTip('Add Relation Field')
        self.add_m2m_field_button = QtWidgets.QPushButton(TablerQIcon.webhook, '')
        self.add_m2m_field_button.setToolTip('Add Many-to-Many Field')

        self.fields_list_widget = QtWidgets.QListWidget()
        self.fields_label = LabelEmbedderWidget(self.fields_list_widget, 'Fields')
        self.fields_label.add_actions(self.add_m2m_field_button, self.add_relation_field_button, self.add_field_button)
        self.delete_field_button = ItemOverlayButton()
        self.delete_field_button.register_to(self.fields_list_widget)

        # Add Widgets to Layouts
        # ----------------------
        top_layout.addWidget(self.db_path_label)
        top_layout.addWidget(self.open_db_button)
        top_layout.addWidget(self.create_db_button)
        top_layout.addWidget(self.refresh_button)
        top_layout.setAlignment(self.db_path_label, QtCore.Qt.AlignBottom)
        top_layout.setAlignment(self.open_db_button, QtCore.Qt.AlignBottom)
        top_layout.setAlignment(self.create_db_button, QtCore.Qt.AlignBottom)
        top_layout.setAlignment(self.refresh_button, QtCore.Qt.AlignBottom)
        layout.addWidget(self.tables_label)
        layout.addWidget(self.fields_label)

    def __init_data_view_widget(self):
        """Create and configure the data view widget.
        """
        # Create Widgets
        # --------------
        self.data_view_widget = QtWidgets.QWidget()
        data_view_layout = QtWidgets.QVBoxLayout(self.data_view_widget)

        self.data_view = DatabaseViewWidget(self.db_manager, parent=self)

        self.tree_data_widget = self.data_view.tree_widget
        self.add_relation_column_menu = self.tree_data_widget.header_menu.addMenu('Add Relation Column')

        # Add Widgets to Layouts
        # ----------------------
        data_view_layout.addWidget(self.data_view)

    def handle_header_context_menu(self, column_index: int):
        """Handle the header context menu signal.

        Args:
            column_index (int): The index of the column where the context menu was requested.
        """
        self.add_relation_column_menu.clear()
        self.add_relation_column_menu.setDisabled(True)

        if not self.current_table:
            return

        # Determine the current table based on the selected column's header
        tree_column_name = self.tree_data_widget.column_names[column_index]

        # TODO: Store relation path in header item to be extract from item directly
        # Check if the column header includes a related table
        if '.' in tree_column_name:
            # The column represents a relation, split to get the table name
            from_table, from_field = tree_column_name.split('.')
        else:
            # Use the original current table
            from_table = self.current_table
            from_field = tree_column_name

        # Get foreign key information for the determined table
        foreign_keys = self.db_manager.get_foreign_keys(from_table)

        # Check if the selected column has a foreign key relation
        related_fk = next((fk for fk in foreign_keys if fk.from_field == from_field), None)

        # Check for many-to-many fields if no direct foreign key was found
        if not related_fk:
            # TODO: Handle m2m > relation > relation
            many_to_many_fields = self.db_manager.get_many_to_many_fields(from_table)

            if from_field in many_to_many_fields:
                m2m_field = many_to_many_fields[from_field]
                junction_table = m2m_field.junction_table

                # Retrieve foreign keys from the junction table
                fks = self.db_manager.get_foreign_keys(junction_table)
                from_table_fk = next(fk for fk in fks if fk.table == from_table)
                to_table_fk = next(fk for fk in fks if fk != from_table_fk)

                # Get the related fields from the 'to' table
                related_field_names = self.db_manager.get_field_names(to_table_fk.table)

                # Add actions for each field in the related table to handle m2m relation columns
                for display_field in related_field_names[1:]:
                    display_column_label = f"{to_table_fk.table}.{display_field}"
                    action = QtWidgets.QAction(display_column_label, self)

                    # Connect the action to the m2m-specific add relation function
                    action.triggered.connect(
                        partial(self.add_relation_column_m2m, from_table, display_field, m2m_field, display_column_label)
                    )

                    self.add_relation_column_menu.addAction(action)

                self.add_relation_column_menu.setEnabled(True)
            return

        # If a direct foreign key relation is found, handle it as before
        to_table = related_fk.table
        to_field = related_fk.to_field

        # Retrieve fields from the related table
        related_field_names = self.db_manager.get_field_names(to_table)

        # Create a menu action for each foreign key relation
        for display_field in related_field_names[1:]:
            action = QtWidgets.QAction(f"{to_table}.{display_field}", self)

            # Pass the correct arguments to add_relation_column
            action.triggered.connect(
                partial(self.add_relation_column, from_table, to_table, display_field, from_field, to_field)
            )

            self.add_relation_column_menu.addAction(action)

        self.add_relation_column_menu.setEnabled(True)

    # NOTE: WIP
    def open_functional_column_dialog(self):
        """Open the Functional Column Dialog to create a new column.
        """
        if not self.current_table:
            QtWidgets.QMessageBox.warning(self, "Error", "No table selected.")
            return

        # Fetch sample data for preview (e.g., first 5 rows)
        sample_data = list(self.db_manager.query_table_data(self.current_table, as_dict=True))[:5]

        # Create and show the Functional Column Dialog
        dialog = FunctionalColumnDialog(self.db_manager, self.current_table, sample_data, self)
        dialog.exec_()

        # Update the view if a new column was successfully created
        self.refresh_data()

    def add_relation_column(self, from_table: str, to_table: str, display_field: str, from_field: str, to_field: str):
        """Add a relation column to the tree widget.

        Args:
            from_table (str): The table from which the relation is originating.
            to_table (str): The name of the related table to join.
            display_field (str): The column from the related table to display.
            from_field (str): The foreign key field in the current table.
            to_field (str): The primary key field in the related table.
        """
        current_column_names = self.tree_data_widget.column_names.copy()

        # Check if the related column header already exists
        target_column_name = f"{to_table}.{display_field}"
        if target_column_name not in current_column_names:
            current_column_names.append(target_column_name)
            self.tree_data_widget.setHeaderLabels(current_column_names)

        # Fetch data from the current table
        data_tuples = self.db_manager.query_table_data(from_table, fields=[from_field])

        # Update the tree widget with the new column data
        for i, data_tuple in enumerate(list(data_tuples)):
            target_value = self.db_manager.fetch_related_value(to_table, display_field, to_field, data_tuple[0])

            # TODO: Handle when grouping
            item: 'TreeWidgetItem' = self.tree_data_widget.topLevelItem(i)
            if item:
                item.set_value(target_column_name, target_value)

    def add_relation_column_m2m(self, from_table: str, display_field: str, m2m_field: ManyToManyField, display_column_label: str):
        """
        Add a many-to-many relation column to the tree widget.

        Args:
            from_table (str): The name of the originating table.
            display_field (str): The field in the related table to display.
            m2m_field (ManyToManyField): The ManyToManyField object containing information about the relationship.
        """
        current_column_names = self.tree_data_widget.column_names.copy()

        # Check if the related column header already exists
        if display_column_label not in current_column_names:
            current_column_names.append(display_column_label)
            self.tree_data_widget.setHeaderLabels(current_column_names)
        data_dicts = self.db_manager.get_many_to_many_data(from_table, m2m_field.track_field_name, display_field=display_field, display_field_label=display_column_label)
        for data_dict in data_dicts:
            self.tree_data_widget.update_item(data_dict)

    def open_database(self):
        db_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Database", "", "SQLite Database Files (*.db *.sqlite)")
        if not db_name:
            return

        self.db_manager = DatabaseManager(db_name)
        self.db_path_line_edit.setText(db_name)
        self.load_table_and_view_names()

    def create_database(self):
        db_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Create Database", "", "SQLite Database Files (*.db *.sqlite)")
        if not db_name:
            return

        # Ensure the database file does not already exist
        if not os.path.exists(db_name):
            # Create an empty file
            open(db_name, 'w').close()
            self.db_manager = DatabaseManager(db_name)
            self.db_path_line_edit.setText(db_name)
            self.load_table_and_view_names()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Database file already exists.")

    def load_table_and_view_names(self):
        """Load the names of tables and views into the UI."""
        if not self.db_manager:
            return

        tables = self.db_manager.get_table_names()
        views = self.db_manager.get_view_names()
        self.data_view.set_database_manager(self.db_manager)

        self.tables_list_widget.clear()
        self.tables_list_widget.addItems(tables + views)

    def load_table_info(self, current_item: Optional[QtWidgets.QListWidgetItem] = None):
        """Load information about the selected table and display its columns and foreign keys.

        Args:
            current_item (Optional[QtWidgets.QListWidgetItem]): The currently selected item in the table list.

        Raises:
            ValueError: If there is an issue retrieving data from the database.
        """
        current_item = current_item or self.tables_list_widget.currentItem()

        if not current_item:
            return

        table_name = current_item.text()
        self.current_table = table_name
        self.data_view.set_table(self.current_table)
        self.field_name_to_info = self.db_manager.get_fields(table_name)

        self.fields_list_widget.clear()

        for field_info in self.field_name_to_info.values():
            # Display the column information
            column_definition = field_info.get_field_definition()

            if field_info.is_foreign_key:
                column_definition += f" (FK to {field_info.fk.table}.{field_info.fk.to_field})"

            self.fields_list_widget.addItem(column_definition)

        # TODO: Add Many-to-Many track fields to fields_list_widget
        many_to_many_fields = self.db_manager.get_many_to_many_fields(self.current_table)
        for field_name, m2m in many_to_many_fields.items():
            column_definition = f"{field_name} ({m2m.junction_table})"
            self.fields_list_widget.addItem(column_definition)
        # ---

    def show_add_field_dialog(self):
        if not self.current_table:
            return

        dialog = AddFieldDialog(self.db_manager, self.current_table, self)
        if dialog.exec_():
            self.load_table_info()

    def show_add_relation_field_dialog(self):
        if not self.current_table:
            return

        dialog = AddRelationFieldDialog(self.db_manager, self.current_table, self)
        if dialog.exec_():
            self.load_table_info()

    def show_add_many_to_many_field_dialog(self):
        if not self.current_table:
            return

        dialog = AddManyToManyFieldDialog(self.db_manager, self.current_table, self)
        if dialog.exec_():
            self.load_table_info()

    def show_add_table_dialog(self):
        dialog = AddTableDialog(self.db_manager, self)
        if dialog.exec_():
            self.load_table_and_view_names()

    def delete_table(self, item: QtWidgets.QListWidgetItem):
        table_name = item.text()

        self.db_manager.delete_table(table_name)
        if table_name == self.current_table:
            self.current_table = None
        self.load_table_and_view_names()
        self.fields_list_widget.clear()
        self.tree_data_widget.clear()

    def delete_field(self, item: QtWidgets.QListWidgetItem):
        field_name = item.text().split()[0]
        self.db_manager.delete_field(self.current_table, field_name)
        self.load_table_info()

    def refresh_data(self):
        self.load_table_and_view_names()
        if self.current_table:
            self.load_table_info()


if __name__ == '__main__':
    from blackboard import theme
    app = QtWidgets.QApplication(sys.argv)
    theme.set_theme(app, 'dark')
    widget = DBWidget()
    main_window = MainWindow(widget, use_scalable_view=True)
    main_window.show()
    sys.exit(app.exec_())
