# Type Checking Imports
# ---------------------
from typing import List, Tuple, Optional, Dict

# Standard Library Imports
# ------------------------
import os
import sys

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.utils.database_manager import DatabaseManager, FieldInfo
from blackboard.widgets.main_window import MainWindow
from blackboard.widgets import GroupableTreeWidget, TreeWidgetItem
from blackboard.widgets.header_view import SearchableHeaderView
from blackboard.widgets.list_widget import EnumListWidget
from blackboard.widgets.label import LabelEmbedderWidget
from blackboard.widgets.button import ItemOverlayButton


# Class Definitions
# -----------------
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
    | [enum_table_dropdown]             |
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
        self.relationship_type_dropdown.addItems(["Many-to-One", "One-to-One", "Many-to-Many"])
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

        elif relationship_type == "Many-to-Many":
            junction_table_name = f"{self.table_name}_{reference_table}_junction"
            # TODO: Implement this
            self.db_manager.create_junction_table(junction_table_name, self.table_name, key_field, reference_table, key_field)

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

class AddEditRecordDialog(QtWidgets.QDialog):

    # Initialization and Setup
    # ------------------------
    def __init__(self, db_manager: DatabaseManager, table_name: str, record: dict = None, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.table_name = table_name
        self.db_manager = db_manager
        self.record = record

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.inputs = {}
        self.field_name_to_info = self.db_manager.get_table_info(self.table_name)

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle("Add/Edit Record")

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        for field_info in self.field_name_to_info.values():
            if field_info.is_primary_key:
                continue  # Skip the primary key field; it is usually auto-managed by SQLite

            input_widget = self.create_input_widget(field_info)
            label = LabelEmbedderWidget(input_widget, field_info.name)
            layout.addWidget(label)
            self.inputs[field_info.name] = input_widget

        if self.record:
            for field, value in self.record.items():
                if field in self.inputs:
                    self.set_input_value(self.inputs[field], value, field_info)

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

        if self.record:
            # Determine which fields have changed
            updated_fields = {}
            for field, new_value in new_values.items():
                old_value = self.record.get(field)

                if new_value != old_value:
                    updated_fields[field] = new_value

            if not updated_fields:
                QtWidgets.QMessageBox.information(self, "No Changes", "No changes were made.")
                return
 
            # Get the primary key field name and its value
            pk_field = self.db_manager.get_primary_keys(self.table_name)[0]
            pk_value = self.record.get(pk_field)

            self.db_manager.update_record(
                self.table_name, 
                list(updated_fields.keys()), 
                list(updated_fields.values()), 
                pk_value, pk_field,
            )

        else:
            # Filter out primary key columns from both values and column names
            column_names_filtered = [field_name for field_name, field_info in self.field_name_to_info.items() if not field_info.is_primary_key]
            values_filtered = [new_values[field_name] for field_name in column_names_filtered]

            self.db_manager.insert_record(self.table_name, column_names_filtered, values_filtered)

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
                    display_value = record[display_field]
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
            widget.setRange(-2147483648, 2147483647)  # Set the range for typical 32-bit integers
            widget.setSpecialValueText("")  # Allow clearing the value
            return widget
        elif field_info.type == "REAL":
            widget = QtWidgets.QDoubleSpinBox()
            widget.setSpecialValueText("")  # Allow clearing the value
            return widget
        elif field_info.type == "TEXT":
            return QtWidgets.QLineEdit()
        elif field_info.type == "BLOB":
            return FileBrowseWidget()
        elif field_info.type == "DATETIME":
            return QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        else:
            return QtWidgets.QLineEdit()

    def browse_file(self, line_edit):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File")
        if file_name:
            line_edit.setText(file_name)

    def set_input_value(self, input_widget, value, field_info: 'FieldInfo'=None):
        if isinstance(input_widget, QtWidgets.QComboBox):
            if field_info and field_info.is_foreign_key:
                # If the field is a foreign key, find the corresponding display value
                fk = field_info.fk
                display_field = self.db_manager.get_display_field(self.table_name, field_info.name)

                if display_field:
                    display_text = self.db_manager.fetch_related_value(fk.table, display_field, fk.to_field, value)
                    input_widget.setCurrentText(display_text)
                    return

            # Fallback to using the value directly if no display field is set
            index = input_widget.findText(value)
            if index == -1:
                input_widget.addItem(value)
                index = input_widget.findText(value)
            input_widget.setCurrentIndex(index)

        elif isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
            if value is None or value == "None":
                input_widget.clear()
            else:
                input_widget.setValue(value)

        elif isinstance(input_widget, QtWidgets.QLineEdit):
            input_widget.setText("" if value is None else str(value))

        elif isinstance(input_widget, QtWidgets.QDateTimeEdit):
            input_widget.setDateTime(QtCore.QDateTime.fromString(value, "yyyy-MM-dd HH:mm:ss") if value else QtCore.QDateTime.currentDateTime())

        elif isinstance(input_widget, QtWidgets.QWidget):
            line_edit = input_widget.findChild(QtWidgets.QLineEdit)
            if line_edit:
                line_edit.setText("" if value is None else str(value))

    def get_record_data(self):
        return {field: self.get_input_value(input_widget) for field, input_widget in self.inputs.items()}

    def get_input_value(self, input_widget):
        if isinstance(input_widget, QtWidgets.QComboBox):
            return input_widget.currentData() or input_widget.currentText()
        if isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
            return input_widget.value()
        elif isinstance(input_widget, QtWidgets.QLineEdit):
            return input_widget.text() or None
        elif isinstance(input_widget, QtWidgets.QDateTimeEdit):
            return input_widget.dateTime().toString("yyyy-MM-dd HH:mm:ss") if input_widget.dateTime() != input_widget.minimumDateTime() else None
        elif isinstance(input_widget, FileBrowseWidget):
            return input_widget.get_value() or None
        elif isinstance(input_widget, QtWidgets.QWidget):
            line_edit = input_widget.findChild(QtWidgets.QLineEdit)
            if line_edit:
                return line_edit.text() or None
        return None

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

        self.data_view_widget = QtWidgets.QWidget()
        self.data_view_layout = QtWidgets.QVBoxLayout(self.data_view_widget)

        self.tree_data_widget = GroupableTreeWidget(self)
        self.add_relation_column_menu = self.tree_data_widget.header_menu.addMenu('Add Relation Column')
        self.left_widget = self.create_left_widget()

        # Add Widgets to Layouts
        # ----------------------
        self.main_layout.addWidget(splitter)
        splitter.addWidget(self.left_widget)
        splitter.addWidget(self.data_view_widget)
        self.data_view_layout.addLayout(self.create_actions_layout())
        self.data_view_layout.addWidget(LabelEmbedderWidget(self.tree_data_widget, "Table Data"))

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
        self.delete_field_button.triggered.connect(self.delete_field)

        self.add_record_button.clicked.connect(self.show_add_record_dialog)
        self.delete_record_button.clicked.connect(self.delete_record)

        self.tree_data_widget.itemDoubleClicked.connect(self.edit_record)
        self.tree_data_widget.about_to_show_header_menu.connect(self.handle_header_context_menu)

    def create_actions_layout(self):
        """Create and configure the actions layout.
        """
        # Create Layouts
        # --------------
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Actions:"))

        # Create Widgets
        # --------------
        self.add_record_button = QtWidgets.QPushButton(TablerQIcon.file_plus, 'Add Record')
        self.delete_record_button = QtWidgets.QPushButton(TablerQIcon.file_minus, 'Delete Record')

        self.filter_input = QtWidgets.QLineEdit()
        filter_label = LabelEmbedderWidget(self.filter_input, "Filter")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.add_record_button)
        layout.addWidget(self.delete_record_button)
        layout.addWidget(filter_label)

        return layout

    def create_left_widget(self):
        """Create and configure the left widget."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

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

        self.fields_list_widget = QtWidgets.QListWidget()
        self.fields_label = LabelEmbedderWidget(self.fields_list_widget, 'Fields')
        self.fields_label.add_actions(self.add_relation_field_button, self.add_field_button)
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

        return widget

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

        if not related_fk:
            return

        # Retrieve related table and field from the foreign key data
        to_table = related_fk.table
        to_field = related_fk.to_field

        # Retrieve fields from the related table
        related_field_names = self.db_manager.get_field_names(to_table)

        # Create a menu action for each foreign key relation
        for target_field in related_field_names[1:]:
            action = QtWidgets.QAction(f"{to_table}.{target_field}", self)

            # Pass the correct arguments to add_relation_column
            action.triggered.connect(
                lambda: self.add_relation_column(from_table, to_table, target_field, from_field, to_field)
            )

            self.add_relation_column_menu.addAction(action)

        self.add_relation_column_menu.setEnabled(True)

    def add_relation_column(self, from_table: str, to_table: str, target_field: str, from_field: str, to_field: str):
        """Add a relation column to the tree widget.

        Args:
            from_table (str): The table from which the relation is originating.
            to_table (str): The name of the related table to join.
            target_field (str): The column from the related table to display.
            from_field (str): The foreign key field in the current table.
            to_field (str): The primary key field in the related table.
        """
        current_column_names = self.tree_data_widget.column_names

        # Check if the related column header already exists
        target_column_name = f"{to_table}.{target_field}"
        if target_column_name not in current_column_names:
            current_column_names.append(target_column_name)
            self.tree_data_widget.setHeaderLabels(current_column_names)

        # Fetch data from the current table
        data_tuples = self.db_manager.query_table_data(from_table, fields=[from_field])

        # Update the tree widget with the new column data
        for i, data_tuple in enumerate(list(data_tuples)):
            target_value = self.db_manager.fetch_related_value(to_table, target_field, to_field, data_tuple[0])

            # TODO: Handle when grouping
            item: 'TreeWidgetItem' = self.tree_data_widget.topLevelItem(i)
            if item:
                item.set_value(target_column_name, target_value)

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
        self.field_name_to_info = self.db_manager.get_table_info(table_name)

        self.fields_list_widget.clear()

        for field_info in self.field_name_to_info.values():
            # Display the column information
            column_definition = field_info.get_field_definition()

            if field_info.is_foreign_key:
                column_definition += f" (FK to {field_info.fk.table}.{field_info.fk.to_field})"

            self.fields_list_widget.addItem(column_definition)

        # Check if a view exists for the table and load its data
        self.load_table_data()

    def load_table_data(self):
        if not self.db_manager or not self.current_table:
            return

        pks = self.db_manager.get_primary_keys(self.current_table)
        fields = self.db_manager.get_field_names(self.current_table)
        if not pks:
            fields.insert(0, 'rowid')

        generator = self.db_manager.query_table_data(self.current_table, fields, as_dict=True)

        self.tree_data_widget.clear()
        self.tree_data_widget.setHeaderLabels(fields)

        self.tree_data_widget.set_generator(generator)

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

    def show_add_table_dialog(self):
        dialog = AddTableDialog(self.db_manager, self)
        if dialog.exec_():
            self.load_table_and_view_names()

    def show_add_record_dialog(self):
        if not self.current_table:
            return

        dialog = AddEditRecordDialog(self.db_manager, self.current_table, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.load_table_data()

    def edit_record(self, item: 'TreeWidgetItem', column):
        # Fetching row data and mapping it to column names
        row_data = {self.tree_data_widget.headerItem().text(col): item.get_value(col) for col in range(self.tree_data_widget.columnCount())}
        dialog = AddEditRecordDialog(self.db_manager, self.current_table, row_data, self)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.load_table_data()

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

    def delete_record(self):
        if not self.current_table:
            return

        if not (current_item:= self.tree_data_widget.currentItem()):
            return

        # Get the primary key field name and its value
        pk_field = self.db_manager.get_primary_keys(self.current_table)[0]
        pk_value = current_item[pk_field]

        confirm = QtWidgets.QMessageBox.question(
            self, "Confirm Delete", f"Are you sure you want to delete the record with {pk_field} '{pk_value}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            self.db_manager.delete_record(self.current_table, pk_value, pk_field)
            self.load_table_data()

    def refresh_data(self):
        self.load_table_and_view_names()
        if self.current_table:
            self.load_table_info()


if __name__ == '__main__':
    from blackboard import theme
    app = QtWidgets.QApplication(sys.argv)
    theme.set_theme(app, 'dark')
    widget = DBWidget()
    main_window = MainWindow(widget)
    main_window.show()
    sys.exit(app.exec_())
