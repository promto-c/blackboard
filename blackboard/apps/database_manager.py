from typing import List, Tuple, Optional, Dict

import sqlite3
from dataclasses import dataclass
import os
import sys
from qtpy import QtCore, QtGui, QtWidgets

from blackboard.widgets.main_window import MainWindow
from blackboard.widgets import GroupableTreeWidget, TreeWidgetItem
from blackboard.widgets.header_view import SearchableHeaderView

@dataclass
class ForeignKey:
    """Represents a foreign key constraint in a database table."""
    table: str          # The referenced table name
    from_column: str    # The column in the current table
    to_column: str      # The column in the referenced table
    on_update: str      # The action on update (e.g., "CASCADE", "RESTRICT")
    on_delete: str      # The action on delete (e.g., "CASCADE", "RESTRICT")

@dataclass
class ColumnInfo:
    cid: int
    name: str
    type: str
    notnull: int
    dflt_value: str
    pk: int

class DatabaseManager:

    FIELD_TYPES = ["INTEGER", "REAL", "TEXT", "BLOB", "NULL", "DATETIME", "ENUM"]

    def __init__(self, db_name: str):
        """Initialize a DatabaseManager instance to interact with a SQLite database.

        Args:
            db_name (str): The name of the SQLite database file.

        Raises:
            sqlite3.Error: If there is an error connecting to the database.
        """
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_metadata_table()

    def create_metadata_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                is_enum BOOLEAN NOT NULL,
                enum_table_name TEXT,
                description TEXT
            );
        ''')
        self.connection.commit()

    def add_enum_metadata(self, table_name: str, column_name: str, enum_table_name: str, description: str = ""):
        self.cursor.execute('''
            INSERT INTO metadata (table_name, column_name, is_enum, enum_table_name, description)
            VALUES (?, ?, 1, ?, ?);
        ''', (table_name, column_name, enum_table_name, description))
        self.connection.commit()

    def get_existing_enum_tables(self) -> List[str]:
        """Get a list of existing enum tables.

        Returns:
            List[str]: A list of table names that match the 'enum_%' pattern.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'enum_%'")
        return [row[0] for row in self.cursor.fetchall()]

    def is_enum_field(self, table_name: str, column_name: str) -> bool:
        """Check if a field is an enum based on metadata.
        """
        self.cursor.execute('''
            SELECT is_enum FROM metadata
            WHERE table_name = ? AND column_name = ?;
        ''', (table_name, column_name))
        result = self.cursor.fetchone()
        return result is not None and result[0] == 1

    def get_enum_table_name(self, table_name: str, column_name: str) -> Optional[str]:
        """Retrieve the name of the enum table associated with a given field.
        """
        self.cursor.execute('''
            SELECT enum_table_name FROM metadata
            WHERE table_name = ? AND column_name = ?;
        ''', (table_name, column_name))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_enum_values(self, enum_table_name: str) -> List[str]:
        """Retrieve all values from an enum table.

        Args:
            enum_table_name (str): The name of the enum table.

        Returns:
            List[str]: A list of enum values.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        self.cursor.execute(f"SELECT value FROM {enum_table_name}")
        return [row[0] for row in self.cursor.fetchall()]

    def create_enum_table(self, enum_name: str, values: List[str]):
        """Create a table to store enum values.

        Args:
            enum_name (str): The name of the enum.
            values (List[str]): The values of the enum.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not enum_name.isidentifier():
            raise ValueError("Invalid enum name")

        table_name = f"enum_{enum_name}"
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT UNIQUE)")

        # Insert enum values
        for value in values:
            self.cursor.execute(f"INSERT OR IGNORE INTO {table_name} (value) VALUES (?)", (value,))

        self.connection.commit()

    def create_table(self, table_name: str, fields: Dict[str, str]):
        """Create a new table in the database with specified fields.

        Args:
            table_name (str): The name of the table to create.
            fields (Dict[str, str]): A dictionary mapping field names to their SQLite data types.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        fields_str = ', '.join([f"{name} {type_}" for name, type_ in fields.items()])
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({fields_str})")
        self.connection.commit()

    def get_table_info(self, table_name: str) -> List[ColumnInfo]:
        """Retrieve information about the columns of a specified table.

        Args:
            table_name (str): The name of the table to retrieve information from.

        Returns:
            List[ColumnInfo]: A list of ColumnInfo dataclass instances, each representing a column in the table.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        return [ColumnInfo(*col) for col in columns]

    def get_field_names(self, table_name: str) -> List[str]:
        """Retrieve the names of the fields (columns) in a specified table.

        Args:
            table_name (str): The name of the table to retrieve field names from.

        Returns:
            List[str]: A list of field names in the specified table.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        return [column[1] for column in columns]

    def get_foreign_keys(self, table_name: str) -> List[ForeignKey]:
        """Retrieve the foreign keys of a specified table.

        Args:
            table_name (str): The name of the table to retrieve foreign keys from.

        Returns:
            List[ForeignKey]: A list of ForeignKey data class instances, each representing a foreign key in the table.
                Each ForeignKey instance contains the following attributes:
                    - table: The name of the referenced table.
                    - from_column: The column in the current table.
                    - to_column: The column in the referenced table.
                    - on_update: The action on update (e.g., "CASCADE", "RESTRICT").
                    - on_delete: The action on delete (e.g., "CASCADE", "RESTRICT").

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = self.cursor.fetchall()

        return [
            ForeignKey(
                table=fk[2],
                from_column=fk[3],
                to_column=fk[4],
                on_update=fk[5],
                on_delete=fk[6]
            )
            for fk in foreign_keys
        ]

    def add_column(self, table_name: str, field_name: str, field_type: str, foreign_key: Optional[str] = None, enum_values: Optional[List[str]] = None, enum_table: Optional[str] = None):
        """Add a new column to an existing table, optionally with a foreign key or enum constraint.

        Args:
            table_name (str): The name of the table to add the column to.
            field_name (str): The name of the new column.
            field_type (str): The data type of the new column.
            foreign_key (Optional[str]): A foreign key constraint in the form of "referenced_table(referenced_column)".
            enum_values (Optional[List[str]]): A list of enum values if the field is of enum type.
            enum_table (Optional[str]): The name of an existing enum table if the field is an enum.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # Handle enum values if provided
        if enum_values:
            # Create a new enum table and update the metadata
            enum_table_name = f"enum_{field_name}"
            self.create_enum_table(field_name, enum_values)
            field_type = "TEXT"
            foreign_key = f"{enum_table_name}(id)"
            self.add_enum_metadata(table_name, field_name, enum_table_name)
        elif enum_table:
            # Use an existing enum table and update the metadata
            field_type = "TEXT"
            foreign_key = f"{enum_table}(id)"
            self.add_enum_metadata(table_name, field_name, enum_table)

        # Update the table schema
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()

        self.cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = self.cursor.fetchall()

        # Create a new table schema with the new column
        new_columns = []
        pk_columns = []

        for col in columns:
            col_def = f"{col[1]} {col[2]}"
            if col[3]:
                col_def += " NOT NULL"
            if col[5]:
                pk_columns.append(col[1])
            new_columns.append(col_def)

        # Add the new column definition
        new_columns.append(f"{field_name} {field_type}")

        # Add primary key constraint if it exists
        if pk_columns:
            new_columns.append(f"PRIMARY KEY ({', '.join(pk_columns)})")

        # Include existing foreign keys
        for fk in foreign_keys:
            new_columns.append(f"FOREIGN KEY({fk[3]}) REFERENCES {fk[2]}({fk[4]}) ON UPDATE {fk[5]} ON DELETE {fk[6]}")

        if foreign_key:
            new_columns.append(f"FOREIGN KEY({field_name}) REFERENCES {foreign_key}")

        new_columns_str = ', '.join(new_columns)

        temp_table_name = f"{table_name}_temp"
        self.cursor.execute(f"CREATE TABLE {temp_table_name} ({new_columns_str})")

        # Copy data from the old table to the new table
        old_columns_str = ', '.join([col[1] for col in columns])
        self.cursor.execute(f"INSERT INTO {temp_table_name} ({old_columns_str}) SELECT {old_columns_str} FROM {table_name}")

        # Drop the old table and rename the new table
        self.cursor.execute(f"DROP TABLE {table_name}")
        self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")

        self.connection.commit()

    def delete_column(self, table_name: str, field_name: str):
        """Delete a column from a table by recreating the table without that column.

        Args:
            table_name (str): The name of the table to delete the column from.
            field_name (str): The name of the column to delete.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # SQLite does not support direct deletion of columns, so the table must be recreated
        self.cursor.execute(f"PRAGMA foreign_keys=off;")
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        self.cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = self.cursor.fetchall()

        # Create a new table schema without the specified column
        new_columns = [col for col in columns if col[1] != field_name]
        column_definitions = [f"{col[1]} {col[2]}" + (" NOT NULL" if col[3] else "") + (" PRIMARY KEY" if col[5] else "") for col in new_columns]

        # Add foreign key constraints
        for fk in foreign_keys:
            if fk[3] != field_name:
                column_definitions.append(f"FOREIGN KEY({fk[3]}) REFERENCES {fk[2]}({fk[4]}) ON UPDATE {fk[5]} ON DELETE {fk[6]}")

        new_columns_str = ', '.join(column_definitions)

        temp_table_name = f"{table_name}_temp"
        self.cursor.execute(f"CREATE TABLE {temp_table_name} ({new_columns_str})")

        old_columns_str = ', '.join([col[1] for col in new_columns])
        self.cursor.execute(f"INSERT INTO {temp_table_name} ({old_columns_str}) SELECT {old_columns_str} FROM {table_name}")

        self.cursor.execute(f"DROP TABLE {table_name}")
        self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")
        self.cursor.execute(f"PRAGMA foreign_keys=on;")

        self.connection.commit()

    def delete_table(self, table_name: str):
        """Delete an entire table from the database.

        Args:
            table_name (str): The name of the table to delete.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.connection.commit()

    def delete_record(self, table_name: str, rowid: int):
        """Delete a specific record from a table by rowid.

        Args:
            table_name (str): The name of the table to delete the record from.
            rowid (int): The unique rowid of the record to delete.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (rowid,))
        self.connection.commit()

    def get_table_names(self) -> List[str]:
        """Retrieve the names of all tables in the database.

        Returns:
            List[str]: A list of table names present in the database.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in self.cursor.fetchall()]

    def get_table_data(self, table_name: str) -> Tuple[List[Tuple], List[str]]:
        """Retrieve all data and column headers from a specified table.

        Args:
            table_name (str): The name of the table to retrieve data from.

        Returns:
            Tuple[List[Tuple], List[str]]: A tuple containing:
                - List of rows, where each row is a tuple of field values.
                - List of column headers, including 'rowid'.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"SELECT rowid, * FROM {table_name}")
        rows = self.cursor.fetchall()
        headers = ['rowid'] + [description[0] for description in self.cursor.description[1:]]
        return rows, headers

    def get_database_size(self) -> int:
        """Get the size of the database file on disk.

        Returns:
            int: The size of the database file in bytes.

        Raises:
            OSError: If there is an error accessing the file system.
        """
        return os.path.getsize(self.db_name)

    def insert_record(self, table_name: str, fields: List[str], values: List):
        """Insert a new record into a table.

        Args:
            table_name (str): The name of the table to insert the record into.
            fields (List[str]): A list of field names where the values should be inserted.
            values (List): A list of values corresponding to the fields.

        Raises:
            ValueError: If the table name or field names are not valid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not all(f.isidentifier() for f in fields):
            raise ValueError("Invalid table name or field names")

        placeholders = ', '.join(['?'] * len(values))
        field_names = ', '.join(fields)
        sql = f"INSERT INTO {table_name} ({field_names}) VALUES ({placeholders})"
        self.cursor.execute(sql, values)
        self.connection.commit()

    def update_record(self, table_name: str, fields: List[str], values: List, rowid: int):
        """Update an existing record in a table by rowid.

        Args:
            table_name (str): The name of the table containing the record to update.
            fields (List[str]): A list of field names to update.
            values (List): A list of new values corresponding to the fields.
            rowid (int): The unique rowid of the record to update.

        Raises:
            ValueError: If the table name or field names are not valid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not all(f.isidentifier() for f in fields):
            raise ValueError("Invalid table name or field names")

        set_clause = ', '.join([f"{field} = ?" for field in fields])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?"
        self.cursor.execute(sql, values + [rowid])
        self.connection.commit()

    def get_field_type(self, table_name: str, field_name: str) -> str:
        """Retrieve the data type of a specific field in a specified table.

        Args:
            table_name (str): The name of the table.
            field_name (str): The name of the field.

        Returns:
            str: The data type of the field.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        for col in columns:
            if col[1] == field_name:
                return col[2]  # Return the data type

        raise ValueError(f"Field '{field_name}' not found in table '{table_name}'")

class AddTableDialog(QtWidgets.QDialog):
    """
    AddTableDialog UI Design:
    
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

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Add Table")
        self.layout = QtWidgets.QVBoxLayout(self)

        # Table Name Section
        self.table_name_label = QtWidgets.QLabel("Table Name:")
        self.table_name_input = QtWidgets.QLineEdit()

        # Primary Key Field Section
        self.primary_key_label = QtWidgets.QLabel("Primary Key Field:")
        self.primary_key_name_label = QtWidgets.QLabel("Name:")
        self.primary_key_name_input = QtWidgets.QLineEdit()

        self.primary_key_type_label = QtWidgets.QLabel("Type:")
        self.primary_key_type_dropdown = QtWidgets.QComboBox()
        self.primary_key_type_dropdown.addItems(["INTEGER", "TEXT"])  # Limiting to common PK types

        # Create Table Button
        self.create_table_button = QtWidgets.QPushButton("Create Table")
        self.create_table_button.clicked.connect(self.accept)

        # Layout Setup
        self.layout.addWidget(self.table_name_label)
        self.layout.addWidget(self.table_name_input)
        self.layout.addWidget(self.primary_key_label)
        self.layout.addWidget(self.primary_key_name_label)
        self.layout.addWidget(self.primary_key_name_input)
        self.layout.addWidget(self.primary_key_type_label)
        self.layout.addWidget(self.primary_key_type_dropdown)
        self.layout.addWidget(self.create_table_button)

        self.setLayout(self.layout)

    def get_table_data(self):
        table_name = self.table_name_input.text()
        primary_key_name = self.primary_key_name_input.text()
        primary_key_type = self.primary_key_type_dropdown.currentText()

        primary_key_definition = f"{primary_key_type} PRIMARY KEY".strip()

        return table_name, [(primary_key_name, primary_key_definition)]

class AddFieldDialog(QtWidgets.QDialog):
    """
    AddFieldDialog UI Design:
    
    +--------------------------------------+
    |           Add Field                  |
    +--------------------------------------+
    | Field Name: [____________________]   |
    |                                      |
    | Field Type: [INTEGER      v]         |
    |                                      |
    | [ ] NOT NULL                         |
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

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.db_manager = db_manager

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.use_existing_enum = False
        self.existing_enum_tables = self.db_manager.get_existing_enum_tables()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle(self.WINDOW_TITLE)

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        self.field_name_label = QtWidgets.QLabel("Field Name:")
        self.field_name_input = QtWidgets.QLineEdit()

        self.field_type_label = QtWidgets.QLabel("Field Type:")
        self.field_type_dropdown = QtWidgets.QComboBox()
        self.field_type_dropdown.addItems(DatabaseManager.FIELD_TYPES)

        self.not_null_checkbox = QtWidgets.QCheckBox("NOT NULL")

        self.enum_option_button = QtWidgets.QPushButton("Use Existing Enum Table")
        self.enum_values_label = QtWidgets.QLabel("Enum Values:")
        self.enum_values_list = QtWidgets.QListWidget()
        self.add_enum_value_button = QtWidgets.QPushButton("Add New Value")

        self.existing_enum_label = QtWidgets.QLabel("Select Existing Enum Table:")
        self.existing_enum_dropdown = QtWidgets.QComboBox()
        self.existing_enum_dropdown.addItems(self.existing_enum_tables)

        self.add_button = QtWidgets.QPushButton("Add Field")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.field_name_label)
        layout.addWidget(self.field_name_input)
        layout.addWidget(self.field_type_label)
        layout.addWidget(self.field_type_dropdown)
        layout.addWidget(self.not_null_checkbox)
        layout.addWidget(self.enum_option_button)
        layout.addWidget(self.enum_values_label)
        layout.addWidget(self.enum_values_list)
        layout.addWidget(self.add_enum_value_button)
        layout.addWidget(self.existing_enum_label)
        layout.addWidget(self.existing_enum_dropdown)
        layout.addWidget(self.add_button)

        # Hide enum-related fields by default
        self.toggle_enum_fields(False)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.field_type_dropdown.currentTextChanged.connect(self.toggle_enum_input)
        self.enum_option_button.clicked.connect(self.toggle_enum_source)
        self.add_enum_value_button.clicked.connect(self.add_enum_value)
        self.add_button.clicked.connect(self.accept)

    # Public Methods
    # --------------
    def toggle_enum_input(self, field_type):
        is_enum = field_type == "ENUM"
        self.toggle_enum_fields(is_enum)

    def toggle_enum_fields(self, visible):
        self.enum_values_label.setVisible(visible and not self.use_existing_enum)
        self.enum_values_list.setVisible(visible and not self.use_existing_enum)
        self.add_enum_value_button.setVisible(visible and not self.use_existing_enum)
        self.existing_enum_label.setVisible(visible and self.use_existing_enum)
        self.existing_enum_dropdown.setVisible(visible and self.use_existing_enum)
        self.enum_option_button.setVisible(visible)

    def toggle_enum_source(self):
        self.use_existing_enum = not self.use_existing_enum
        if self.use_existing_enum:
            self.enum_option_button.setText("Create New Enum Table")
        else:
            self.enum_option_button.setText("Use Existing Enum Table")
        self.toggle_enum_fields(True)

    def add_enum_value(self):
        item = QtWidgets.QListWidgetItem()
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)

        value_input = QtWidgets.QLineEdit()
        remove_button = QtWidgets.QPushButton("-")
        move_up_button = QtWidgets.QPushButton("^")
        move_down_button = QtWidgets.QPushButton("v")

        layout.addWidget(value_input)
        layout.addWidget(remove_button)
        layout.addWidget(move_up_button)
        layout.addWidget(move_down_button)
        layout.setContentsMargins(0, 0, 0, 0)

        widget.setLayout(layout)
        item.setSizeHint(widget.sizeHint())

        self.enum_values_list.addItem(item)
        self.enum_values_list.setItemWidget(item, widget)

        remove_button.clicked.connect(lambda: self.enum_values_list.takeItem(self.enum_values_list.row(item)))
        move_up_button.clicked.connect(lambda: self.move_enum_value_up(item))
        move_down_button.clicked.connect(lambda: self.move_enum_value_down(item))

    def move_enum_value_up(self, item):
        row = self.enum_values_list.row(item)
        if row > 0:
            self.enum_values_list.takeItem(row)
            self.enum_values_list.insertItem(row - 1, item)

    def move_enum_value_down(self, item):
        row = self.enum_values_list.row(item)
        if row < self.enum_values_list.count() - 1:
            self.enum_values_list.takeItem(row)
            self.enum_values_list.insertItem(row + 1, item)

    def get_enum_values(self):
        values = []
        for i in range(self.enum_values_list.count()):
            item = self.enum_values_list.item(i)
            widget = self.enum_values_list.itemWidget(item)
            value_input = widget.findChild(QtWidgets.QLineEdit)
            values.append(value_input.text().strip())
        return values

    def get_field_data(self):
        field_name = self.field_name_input.text()
        field_type = self.field_type_dropdown.currentText()
        not_null = "NOT NULL" if self.not_null_checkbox.isChecked() else ""

        field_definition = f"{field_type} {not_null}".strip()

        enum_values = None
        enum_table = None

        if field_type == "ENUM":
            if self.use_existing_enum:
                enum_table = self.existing_enum_dropdown.currentText()
            else:
                enum_values = self.get_enum_values()

        return field_name, field_definition, enum_values, enum_table

class AddRelationFieldDialog(QtWidgets.QDialog):
    """
    AddRelationFieldDialog UI Design:
    
    +--------------------------------------+
    |          Add Relation Field          |
    +--------------------------------------+
    | Field Name: [table_field           ] |
    |                                      |
    | Reference Table: [ Table1       v]   |
    |                                      |
    | Reference Field: [ Field1       v]   |
    |                                      |
    | [ ] NOT NULL                         |
    |                                      |
    |                (Add Button)          |
    |       [ Add Relation Field ]         |
    +--------------------------------------+
    """

    def __init__(self, tables, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.tables = tables

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes."""
        self.relation_table = None
        self.relation_field = None

    def __init_ui(self):
        """Initialize the UI of the widget."""
        self.setWindowTitle("Add Relation Field")

        # Create Layouts
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        self.field_name_label = QtWidgets.QLabel("Field Name:")
        self.field_name_input = QtWidgets.QLineEdit()

        self.table_label = QtWidgets.QLabel("Reference Table:")
        self.table_dropdown = QtWidgets.QComboBox()
        self.table_dropdown.addItems(self.tables)

        self.field_label = QtWidgets.QLabel("Reference Field:")
        self.field_dropdown = QtWidgets.QComboBox()

        self.not_null_checkbox = QtWidgets.QCheckBox("NOT NULL")

        self.add_button = QtWidgets.QPushButton("Add Relation Field")

        # Add Widgets to Layouts
        layout.addWidget(self.field_name_label)
        layout.addWidget(self.field_name_input)
        layout.addWidget(self.table_label)
        layout.addWidget(self.table_dropdown)
        layout.addWidget(self.field_label)
        layout.addWidget(self.field_dropdown)
        layout.addWidget(self.not_null_checkbox)
        layout.addWidget(self.add_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections."""
        self.table_dropdown.currentTextChanged.connect(self.update_fields)
        self.add_button.clicked.connect(self.accept)

    def update_fields(self):
        selected_table = self.table_dropdown.currentText()
        if selected_table:
            field_names = self.parent().db_manager.get_field_names(selected_table)
            self.field_dropdown.clear()
            self.field_dropdown.addItems(field_names)
            self.field_name_input.setText(f"{selected_table}_{self.field_dropdown.currentText()}")

    def get_relation_data(self):
        field_name = self.field_name_input.text()
        reference_table = self.table_dropdown.currentText()
        reference_field = self.field_dropdown.currentText()
        not_null = "NOT NULL" if self.not_null_checkbox.isChecked() else ""
        return field_name, reference_table, reference_field, not_null

class AddEditRecordDialog(QtWidgets.QDialog):
    def __init__(self, column_metadata, record=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Record")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.column_metadata = column_metadata
        self.inputs = {}
        self.db_manager = parent.db_manager  # Reference to DatabaseManager for enum values

        for field, metadata in self.column_metadata.items():
            if metadata['primary_key']:
                continue  # Skip the primary key field; it is usually auto-managed by SQLite

            label = QtWidgets.QLabel(field)
            input_widget = self.create_input_widget(field, metadata)
            self.layout.addWidget(label)
            self.layout.addWidget(input_widget)
            self.inputs[field] = input_widget

        if record:
            for field, value in record.items():
                if field in self.inputs:
                    self.set_input_value(self.inputs[field], value)

        self.submit_button = QtWidgets.QPushButton("Submit")
        self.submit_button.clicked.connect(self.accept)
        self.layout.addWidget(self.submit_button)

    def create_input_widget(self, field, metadata):
        if metadata["foreign_key"]:
            # You might want to handle foreign keys differently, such as offering a dropdown of related records
            pass  # Implementation for handling foreign keys

        if self.db_manager.is_enum_field(self.parent().current_table, field):
            enum_table_name = self.db_manager.get_enum_table_name(self.parent().current_table, field)
            enum_values = self.db_manager.get_enum_values(enum_table_name)
            widget = QtWidgets.QComboBox()
            widget.addItems(enum_values)
            return widget

        if metadata["type"] == "INTEGER":
            widget = QtWidgets.QSpinBox()
            widget.setRange(-2147483648, 2147483647)  # Set the range for typical 32-bit integers
            widget.setSpecialValueText("")  # Allow clearing the value
            return widget
        elif metadata["type"] == "REAL":
            widget = QtWidgets.QDoubleSpinBox()
            widget.setSpecialValueText("")  # Allow clearing the value
            return widget
        elif metadata["type"] == "TEXT":
            return QtWidgets.QLineEdit()
        elif metadata["type"] == "BLOB":
            return self.create_blob_widget()
        elif metadata["type"] == "DATETIME":
            return QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        else:
            return QtWidgets.QLineEdit()

    def create_blob_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        line_edit = QtWidgets.QLineEdit()
        button = QtWidgets.QPushButton("Browse")
        button.clicked.connect(lambda: self.browse_file(line_edit))
        layout.addWidget(line_edit)
        layout.addWidget(button)
        widget.setLayout(layout)
        return widget

    def browse_file(self, line_edit):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File")
        if file_name:
            line_edit.setText(file_name)

    def set_input_value(self, input_widget, value):
        if isinstance(input_widget, QtWidgets.QComboBox):
            index = input_widget.findText(value)
            if index == -1:
                input_widget.addItem(value)
                index = input_widget.findText(value)
            input_widget.setCurrentIndex(index)
        elif isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
            if value is None or value == "None":
                input_widget.clear()
            else:
                input_widget.setValue(int(value) if isinstance(input_widget, QtWidgets.QSpinBox) else float(value))
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
            return input_widget.currentText()
        if isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
            return input_widget.value() if input_widget.value() != input_widget.minimum() else None
        elif isinstance(input_widget, QtWidgets.QLineEdit):
            return input_widget.text() or None
        elif isinstance(input_widget, QtWidgets.QDateTimeEdit):
            return input_widget.dateTime().toString("yyyy-MM-dd HH:mm:ss") if input_widget.dateTime() != input_widget.minimumDateTime() else None
        elif isinstance(input_widget, QtWidgets.QWidget):
            line_edit = input_widget.findChild(QtWidgets.QLineEdit)
            if line_edit:
                return line_edit.text() or None
        return None

class DBWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SQLite Database Manager")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and set layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.tree_data_widget = self.create_tree_data_widget()
        self.main_layout = self.create_main_layout()

        self.central_widget.setLayout(self.main_layout)
        self.dock_widget = self.create_dock_widget()

        self.db_manager = None
        self.current_table = None

    def create_tree_data_widget(self):
        """Create and configure the tree data widget."""
        tree_data_widget = GroupableTreeWidget()

        tree_data_widget.setHeaderLabels([])  # Header labels will be set dynamically
        tree_data_widget.itemDoubleClicked.connect(self.edit_record)
        tree_data_widget.about_to_show_header_menu.connect(self.handle_header_context_menu)

        self.add_relation_column_menu = tree_data_widget.header_menu.addMenu('Add Relation Column')

        return tree_data_widget

    def create_main_layout(self):
        """Create and configure the main layout."""
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.create_actions_layout())
        layout.addWidget(QtWidgets.QLabel("Table Data"))
        layout.addWidget(self.tree_data_widget)

        return layout

    def create_actions_layout(self):
        """Create and configure the actions layout."""
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Actions:"))

        self.refresh_button = self.create_action_button("Refresh", self.refresh_data)
        self.add_record_button = self.create_action_button("Add Record", self.show_add_record_dialog)
        self.delete_record_button = self.create_action_button("Delete Record", self.delete_record)

        self.filter_input = QtWidgets.QLineEdit()  # Initialize the QLineEdit

        for widget in [
            self.refresh_button,
            self.add_record_button,
            self.delete_record_button,
            QtWidgets.QLabel("Filter:"),
            self.filter_input,  # Add the initialized QLineEdit to the layout
        ]:
            layout.addWidget(widget)

        return layout

    def create_action_button(self, text, callback):
        """Helper method to create a QPushButton with a callback."""
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(callback)
        return button

    def create_dock_widget(self):
        """Create and configure the dock widget."""
        dock_widget = QtWidgets.QDockWidget("SQLite Database Info", self)
        dock_widget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        self.left_widget = self.create_left_widget()
        dock_widget.setWidget(self.left_widget)

        return dock_widget

    def create_left_widget(self):
        """Create and configure the left widget."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)

        self.db_name_label, self.db_name_display = self.create_label_pair("Database Name:")
        self.db_path_label, self.db_path_display = self.create_label_pair("Database Path:")
        self.db_size_label, self.db_size_display = self.create_label_pair("Size:")

        self.open_db_button = self.create_action_button("Open Database", self.open_database)
        self.create_db_button = self.create_action_button("Create Database", self.create_database)
        self.tables_list = QtWidgets.QListWidget()
        self.tables_list.currentItemChanged.connect(self.load_table_info)
        self.columns_list = QtWidgets.QListWidget()

        self.add_field_button = self.create_action_button("Add Field", self.show_add_field_dialog)
        self.add_relation_field_button = self.create_action_button("Add Relation Field", self.show_add_relation_field_dialog)
        self.delete_field_button = self.create_action_button("Delete Field", self.delete_field)

        self.add_table_button = self.create_action_button("Add Table", self.show_add_table_dialog)
        self.delete_table_button = self.create_action_button("Delete Table", self.delete_table)

        self.setup_left_layout(layout)

        return widget

    def create_label_pair(self, text):
        """Create a label with a corresponding display label."""
        label = QtWidgets.QLabel(text)
        display = QtWidgets.QLabel("")
        return label, display

    def setup_left_layout(self, layout):
        """Add widgets to the left layout."""
        layout.addWidget(self.open_db_button)
        layout.addWidget(self.create_db_button)

        layout.addWidget(self.db_name_label)
        layout.addWidget(self.db_name_display)
        layout.addWidget(self.db_path_label)
        layout.addWidget(self.db_path_display)
        layout.addWidget(self.db_size_label)
        layout.addWidget(self.db_size_display)

        layout.addLayout(self.create_sub_layout("Tables", self.add_table_button, self.delete_table_button))
        layout.addWidget(self.tables_list)
        layout.addLayout(self.create_sub_layout("Columns", self.add_field_button, self.add_relation_field_button, self.delete_field_button))
        layout.addWidget(self.columns_list)

    def create_sub_layout(self, label_text, *buttons):
        """Create a horizontal layout with a label and buttons."""
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(label_text))

        for button in buttons:
            layout.addWidget(button)

        return layout

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
            current_table, column_name = tree_column_name.split('.')
        else:
            # Use the original current table
            current_table = self.current_table
            column_name = tree_column_name

        # Get foreign key information for the determined table
        foreign_keys = self.db_manager.get_foreign_keys(current_table)

        # Check if the selected column has a foreign key relation
        related_fk = next(
            (fk for fk in foreign_keys if fk.from_column == column_name),
            None
        )

        if not related_fk:
            return

        # Retrieve related table and field from the foreign key data
        related_table = related_fk.table
        current_foreign_key_field = related_fk.from_column
        related_primary_key_field = related_fk.to_column

        # Retrieve fields from the related table
        related_field_names = self.db_manager.get_field_names(related_table)

        # Create a menu action for each foreign key relation
        for related_field_name in related_field_names[1:]:
            action = QtWidgets.QAction(f"{related_table}.{related_field_name}", self)

            # Pass the correct arguments to add_relation_column
            action.triggered.connect(
                lambda: self.add_relation_column(current_table, related_table, related_field_name, current_foreign_key_field, related_primary_key_field)
            )

            self.add_relation_column_menu.addAction(action)

        self.add_relation_column_menu.setEnabled(True)

    def add_relation_column(self, current_table: str, related_table: str, related_column: str, current_foreign_key_field: str, related_primary_key_field: str):
        """Add a relation column to the tree widget.

        Args:
            current_table (str): The table from which the relation is originating.
            related_table (str): The name of the related table to join.
            related_column (str): The column from the related table to display.
            current_foreign_key_field (str): The foreign key field in the current table.
            related_primary_key_field (str): The primary key field in the related table.
        """
        # Fetch data from the related table
        related_data, related_headers = self.db_manager.get_table_data(related_table)
        current_column_names = self.tree_data_widget.column_names

        if self.current_table != current_table:
            _data, current_headers = self.db_manager.get_table_data(current_table)
        else:
            # Use the current headers from the tree widget
            current_headers = current_column_names.copy()

        # Check if the related column header already exists
        new_column_name = f"{related_table}.{related_column}"
        if new_column_name not in current_column_names:
            current_column_names.append(new_column_name)
            self.tree_data_widget.setHeaderLabels(current_column_names)

        # Fetch data from the current table
        current_data, _ = self.db_manager.get_table_data(current_table)

        # Get the index of the foreign key in the current table and the primary key in the related table
        current_foreign_key_index = current_headers.index(current_foreign_key_field)
        related_primary_key_index = related_headers.index(related_primary_key_field)
        related_column_index = related_headers.index(related_column)

        # Calculate the index for the new related column
        new_column_index = current_column_names.index(new_column_name)

        # Update the tree widget with the new column data
        for i, current_row in enumerate(current_data):
            related_value = self._find_related_value(
                current_row[current_foreign_key_index], related_data, related_primary_key_index, related_column_index
            )

            # TODO: Get items from appropriate depth as len(self.tree_data_widget.group_column_names)
            # TODO: Fix bug missing data when group by some relation column
            item = self.tree_data_widget.topLevelItem(i)
            if item:
                item.setText(new_column_index, str(related_value) if related_value is not None else "")
                item.setData(new_column_index, QtCore.Qt.ItemDataRole.UserRole, related_value)

    def _find_related_value(self, current_fk_value, related_data, related_primary_key_index, related_column_index):
        """Find the related value based on the foreign key.

        Args:
            current_fk_value: The foreign key value in the current row.
            related_data: The data from the related table.
            related_primary_key_index: The index of the primary key in the related table.
            related_column_index: The index of the related column.

        Returns:
            The related value or None if not found.
        """
        return next(
            (
                related_row[related_column_index]
                for related_row in related_data
                if related_row[related_primary_key_index] == current_fk_value
            ),
            None,
        )

    def open_database(self):
        db_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Database", "", "SQLite Database Files (*.db *.sqlite)")
        if db_name:
            self.db_manager = DatabaseManager(db_name)
            self.db_name_display.setText(os.path.basename(db_name))
            self.db_path_display.setText(db_name)
            self.db_size_display.setText(f"{self.db_manager.get_database_size()} bytes")
            self.load_table_names()

    def create_database(self):
        db_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Create Database", "", "SQLite Database Files (*.db *.sqlite)")
        if db_name:
            # Ensure the database file does not already exist
            if not os.path.exists(db_name):
                self.db_manager = DatabaseManager(db_name)
                open(db_name, 'w').close()  # Create an empty file
                self.db_name_display.setText(os.path.basename(db_name))
                self.db_path_display.setText(db_name)
                self.db_size_display.setText(f"{self.db_manager.get_database_size()} bytes")
                self.load_table_names()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Database file already exists.")

    def load_table_names(self):
        if self.db_manager:
            tables = self.db_manager.get_table_names()
            self.tables_list.clear()
            self.tables_list.addItems(tables)

    def load_table_info(self, current_item: Optional[QtWidgets.QListWidgetItem]):
        """Load information about the selected table and display its columns and foreign keys.

        Args:
            current_item (Optional[QtWidgets.QListWidgetItem]): The currently selected item in the table list.

        Raises:
            ValueError: If there is an issue retrieving data from the database.
        """
        if current_item:
            table_name = current_item.text()
            self.current_table = table_name
            columns = self.db_manager.get_table_info(table_name)
            foreign_keys = self.db_manager.get_foreign_keys(table_name)
            
            self.columns_list.clear()
            self.column_metadata = {}

            for column in columns:
                column_name = column.name
                column_type = column.type
                is_not_null = column.notnull == 1
                is_primary_key = column.pk == 1
                foreign_key_info = None

                # Check for foreign key constraints
                for fk in foreign_keys:
                    if fk.from_column == column_name:
                        foreign_key_info = {
                            "table": fk.table,
                            "column": fk.to_column,
                        }

                # Store detailed metadata
                self.column_metadata[column_name] = {
                    "type": column_type,
                    "not_null": is_not_null,
                    "primary_key": is_primary_key,
                    "foreign_key": foreign_key_info,
                }

                # Display the column information
                column_definition = f"{column_name} {column_type} {'NOT NULL' if is_not_null else ''} {'PRIMARY KEY' if is_primary_key else ''}".strip()
                if foreign_key_info:
                    column_definition += f" (FK to {foreign_key_info['table']}({foreign_key_info['column']}))"

                self.columns_list.addItem(column_definition)

            self.load_table_data()

    def load_table_data(self):
        if self.db_manager and self.current_table:
            data, headers = self.db_manager.get_table_data(self.current_table)
            self.tree_data_widget.clear()
            self.tree_data_widget.setHeaderLabels(headers)

            for row_data in data:
                parent_item = TreeWidgetItem(self.tree_data_widget, list(row_data))
                # for col_idx, cell_data in enumerate(row_data):
                #     parent_item.setText(col_idx, str(cell_data))
                #     parent_item.setData(col_idx, QtCore.Qt.ItemDataRole.UserRole, cell_data)

    def show_add_field_dialog(self):
        if self.current_table:
            dialog = AddFieldDialog(self.db_manager, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                field_name, field_definition, enum_values, enum_table = dialog.get_field_data()
                if field_name and field_definition:
                    self.db_manager.add_column(
                        self.current_table, 
                        field_name, 
                        field_definition, 
                        enum_values=enum_values, 
                        enum_table=enum_table
                    )
                    QtWidgets.QMessageBox.information(self, "Success", f"Field '{field_name}' added successfully.")
                    self.load_table_info(self.tables_list.currentItem())
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please enter valid field data.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def show_add_relation_field_dialog(self):
        if self.current_table:
            dialog = AddRelationFieldDialog(self.db_manager.get_table_names(), self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                field_name, reference_table, reference_field, not_null = dialog.get_relation_data()
                if field_name and reference_table and reference_field:
                    self.db_manager.add_column(self.current_table, field_name, "INTEGER", foreign_key=f"{reference_table}({reference_field})", enum_values=None)
                    QtWidgets.QMessageBox.information(self, "Success", f"Relation Field '{field_name}' added successfully.")
                    self.load_table_info(self.tables_list.currentItem())
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please enter valid relation field data.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")


    def show_add_table_dialog(self):
        dialog = AddTableDialog(self.db_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            table_name, fields = dialog.get_table_data()
            if table_name and fields:
                fields_dict = {field[0]: field[1] for field in fields}
                self.db_manager.create_table(table_name, fields_dict)
                self.load_table_names()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Please enter a valid table name and fields.")

    def show_add_record_dialog(self):
        if self.current_table:
            dialog = AddEditRecordDialog(self.column_metadata, parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                values = dialog.get_record_data()

                # Filter out primary key columns from both values and column names
                values_filtered = [values[c] for c, meta in self.column_metadata.items() if not meta.get("primary_key")]
                column_names_filtered = [c for c, meta in self.column_metadata.items() if not meta.get("primary_key")]

                # Check only NOT NULL fields, excluding the primary key
                not_null_fields = [c for c, meta in self.column_metadata.items() if meta.get("not_null") and not meta.get("primary_key")]
                if all(values.get(field) is not None for field in not_null_fields):
                    self.db_manager.insert_record(self.current_table, column_names_filtered, values_filtered)
                    self.load_table_data()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please fill in all required fields.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def edit_record(self, item, column):
        if self.current_table:
            # Fetching row data and mapping it to column names
            row_data = {self.tree_data_widget.headerItem().text(col): item.text(col) for col in range(self.tree_data_widget.columnCount())}
            dialog = AddEditRecordDialog(self.column_metadata, row_data, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_values = dialog.get_record_data()

                # Check only NOT NULL fields, skipping INTEGER PRIMARY KEY fields
                not_null_fields = [
                    field for field, meta in self.column_metadata.items() 
                    if meta.get("not_null") and not (meta.get("type") == "INTEGER" and meta.get("primary_key"))
                ]

                if all(new_values.get(field) is not None for field in not_null_fields):
                    # Determine which fields have changed
                    updated_fields = {}
                    for field, new_value in new_values.items():
                        old_value = row_data.get(field)
                        field_type = self.column_metadata[field].get("type")

                        # Convert old_value to the appropriate type based on column metadata
                        if field_type == "INTEGER":
                            old_value = int(old_value) if old_value != 'None' else None
                        elif field_type == "REAL":
                            old_value = float(old_value) if old_value != 'None' else None
                        elif field_type == "TEXT":
                            old_value = str(old_value)
                        # Add other type conversions if needed

                        if new_value != old_value:
                            updated_fields[field] = new_value

                    if updated_fields:
                        rowid = int(row_data['rowid'])  # Fetch rowid from row_data
                        self.db_manager.update_record(
                            self.current_table, 
                            list(updated_fields.keys()), 
                            list(updated_fields.values()), 
                            rowid
                        )
                        self.load_table_data()
                    else:
                        QtWidgets.QMessageBox.information(self, "No Changes", "No changes were made.")
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please fill in all required fields.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def delete_table(self):
        if self.current_table:
            confirm = QtWidgets.QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete the table '{self.current_table}'?",
                                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if confirm == QtWidgets.QMessageBox.Yes:
                self.db_manager.delete_table(self.current_table)
                self.current_table = None
                self.load_table_names()
                self.columns_list.clear()
                self.tree_data_widget.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def delete_field(self):
        if self.current_table:
            current_item = self.columns_list.currentItem()
            if current_item:
                field_name = current_item.text().split()[0]
                confirm = QtWidgets.QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete the field '{field_name}'?",
                                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if confirm == QtWidgets.QMessageBox.Yes:
                    self.db_manager.delete_column(self.current_table, field_name)
                    self.load_table_info(self.tables_list.currentItem())
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Please select a field first.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def delete_record(self):
        if self.current_table:
            current_item = self.tree_data_widget.currentItem()
            if current_item:
                rowid = int(current_item.text(0))  # Assuming the first column is the rowid
                confirm = QtWidgets.QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete the record with rowid '{rowid}'?",
                                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if confirm == QtWidgets.QMessageBox.Yes:
                    self.db_manager.delete_record(self.current_table, rowid)
                    self.load_table_data()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Please select a record first.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def refresh_data(self):
        self.load_table_names()
        if self.current_table:
            self.load_table_info(self.tables_list.currentItem())


if __name__ == '__main__':
    from blackboard import theme
    app = QtWidgets.QApplication(sys.argv)
    theme.set_theme(app, 'dark')
    widget = DBWidget()
    main_window = MainWindow(widget)
    main_window.show()
    sys.exit(app.exec_())
