# Type Checking Imports
# ---------------------
from typing import List, Tuple, Optional, Dict

# Standard Library Imports
# ------------------------
import os
import sys
from functools import partial

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

class AddEditRecordDialog(QtWidgets.QDialog):

    # Initialization and Setup
    # ------------------------
    def __init__(self, db_manager: DatabaseManager, table_name: str, data_dict: dict = None, parent=None):
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
        self.field_name_to_info = self.db_manager.get_table_info(self.table_name)
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
            label = LabelEmbedderWidget(input_widget, field_name)
            layout.addWidget(label)
            self.field_name_to_input_widgets[field_name] = input_widget

        for many_to_many_field in self.many_to_many_fields:
            m2m_widget = self.create_many_to_many_widget(many_to_many_field)
            label = LabelEmbedderWidget(m2m_widget, many_to_many_field.track_field_name)
            layout.addWidget(label)
            self.field_name_to_input_widgets[many_to_many_field.track_field_name] = m2m_widget

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

            for many_to_many_field in self.many_to_many_fields:
                field_name = many_to_many_field.track_field_name
                if field_name not in new_values:
                    continue
                data_filtered[field_name] = new_values[field_name]

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
    | From Display Field: [name            v]   |
    |                                      |
    | To Table: [Table2               v]   |
    |                                      |
    | To Key Field: [id               v]   |
    |                                      |
    | To Display Field: [name            v]   |
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

        self.add_record_button.clicked.connect(self.show_add_record_dialog)
        self.delete_record_button.clicked.connect(self.delete_record)

        self.tree_data_widget.itemDoubleClicked.connect(self.edit_record)
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

        self.data_view = DatabaseViewWidget(self)

        self.tree_data_widget = self.data_view.tree_widget
        self.add_relation_column_menu = self.tree_data_widget.header_menu.addMenu('Add Relation Column')

        # Data View
        self.add_record_button = QtWidgets.QPushButton(TablerQIcon.file_plus, 'Add Record')
        self.delete_record_button = QtWidgets.QPushButton(TablerQIcon.file_minus, 'Delete Record')

        # Add Widgets to Layouts
        # ----------------------
        # Data View
        self.data_view.general_tool_bar.addWidget(self.add_record_button)
        self.data_view.general_tool_bar.addWidget(self.delete_record_button)
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
            m2m_field_map = {m2m.track_field_name: m2m for m2m in many_to_many_fields}

            if from_field in m2m_field_map:
                m2m_field = m2m_field_map[from_field]
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

        # TODO: Add Many-to-Many track fields to fields_list_widget
        many_to_many_fields = self.db_manager.get_many_to_many_fields(self.current_table)
        for m2m in many_to_many_fields:
            field_name = m2m.track_field_name
            column_definition = f"{field_name} ({m2m.junction_table})"
            self.fields_list_widget.addItem(column_definition)
        # ---

        # Check if a view exists for the table and load its data
        self.load_table_data()

    def load_table_data(self):
        if not self.db_manager or not self.current_table:
            return

        primary_key = self.db_manager.get_primary_keys(self.current_table)
        fields = self.db_manager.get_field_names(self.current_table)
        many_to_many_field_names = self.db_manager.get_many_to_many_field_names(self.current_table)

        if not primary_key:
            primary_key = 'rowid'
            fields.insert(0, primary_key)

        self.tree_data_widget.clear()
        self.tree_data_widget.set_primary_key(primary_key)
        self.tree_data_widget.setHeaderLabels(fields + many_to_many_field_names)

        generator = self.db_manager.query_table_data(self.current_table, fields + many_to_many_field_names, as_dict=True, handle_m2m=True)
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

    # TODO: Add support composite pks
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
    main_window = MainWindow(widget, use_scalable_view=True)
    main_window.show()
    sys.exit(app.exec_())
