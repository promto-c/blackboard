import sqlite3
import os
import sys
from qtpy import QtCore, QtGui, QtWidgets

from blackboard.widgets.main_window import MainWindow
from blackboard.widgets import GroupableTreeWidget, TreeWidgetItem


class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()

    def create_table(self, table_name, fields):
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        fields_str = ', '.join([f"{name} {type_}" for name, type_ in fields.items()])
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({fields_str})")
        self.connection.commit()

    def get_table_info(self, table_name):
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return self.cursor.fetchall()

    def get_foreign_keys(self, table_name):
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        return self.cursor.fetchall()

    def add_column(self, table_name, field_name, field_type, foreign_key=None):
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        if foreign_key:
            # Handle the case with a foreign key constraint by recreating the table
            # Get the current schema of the table
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = self.cursor.fetchall()

            # Create a new table schema with the new column
            new_columns = [f"{col[1]} {col[2]}" for col in columns]
            new_columns.append(f"{field_name} {field_type}")
            new_columns.append(f"FOREIGN KEY({field_name}) REFERENCES {foreign_key}")

            # Recreate the table with the new schema
            temp_table_name = f"{table_name}_temp"
            new_columns_str = ', '.join(new_columns)
            self.cursor.execute(f"CREATE TABLE {temp_table_name} ({new_columns_str})")

            # Copy data from the old table to the new table
            old_columns_str = ', '.join([col[1] for col in columns])
            self.cursor.execute(f"INSERT INTO {temp_table_name} ({old_columns_str}) SELECT {old_columns_str} FROM {table_name}")

            # Drop the old table and rename the new table
            self.cursor.execute(f"DROP TABLE {table_name}")
            self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")
        else:
            # Directly add a column if no foreign key constraint is needed
            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type}")

        self.connection.commit()

    def delete_column(self, table_name, field_name):
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # SQLite does not support direct deletion of columns, so the table must be recreated
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        new_columns = [f"{col[1]} {col[2]}" for col in columns if col[1] != field_name]

        temp_table_name = f"{table_name}_temp"
        new_columns_str = ', '.join(new_columns)
        self.cursor.execute(f"CREATE TABLE {temp_table_name} ({new_columns_str})")

        old_columns_str = ', '.join([col[1] for col in columns if col[1] != field_name])
        self.cursor.execute(f"INSERT INTO {temp_table_name} ({old_columns_str}) SELECT {old_columns_str} FROM {table_name}")

        self.cursor.execute(f"DROP TABLE {table_name}")
        self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")
        self.connection.commit()

    def delete_table(self, table_name):
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.connection.commit()

    def delete_record(self, table_name, rowid):
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (rowid,))
        self.connection.commit()

    def get_table_names(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in self.cursor.fetchall()]

    def get_table_data(self, table_name):
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"SELECT rowid, * FROM {table_name}")
        rows = self.cursor.fetchall()
        headers = ['rowid'] + [description[0] for description in self.cursor.description[1:]]
        return rows, headers

    def get_database_size(self):
        return os.path.getsize(self.db_name)

    def insert_record(self, table_name, fields, values):
        if not table_name.isidentifier() or not all(f.isidentifier() for f in fields):
            raise ValueError("Invalid table name or field names")

        placeholders = ', '.join(['?'] * len(values))
        field_names = ', '.join(fields)
        sql = f"INSERT INTO {table_name} ({field_names}) VALUES ({placeholders})"
        self.cursor.execute(sql, values)
        self.connection.commit()

    def update_record(self, table_name, fields, values, rowid):
        if not table_name.isidentifier() or not all(f.isidentifier() for f in fields):
            raise ValueError("Invalid table name or field names")

        set_clause = ', '.join([f"{field} = ?" for field in fields])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?"
        self.cursor.execute(sql, values + [rowid])
        self.connection.commit()


class AddFieldDialog(QtWidgets.QDialog):

    # Initialization and Setup
    # ------------------------
    def __init__(self, tables, parent=None):
        super().__init__(parent)

        # Store the arguments
        self.tables = tables

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        # Attributes
        # ----------
        self.relation_table = None
        self.relation_field = None

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setWindowTitle("Add Field")

        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)

        # Create Widgets
        # --------------
        self.field_name_label = QtWidgets.QLabel("Field Name:")
        self.field_name_input = QtWidgets.QLineEdit()

        self.field_type_label = QtWidgets.QLabel("Field Type:")
        self.field_type_dropdown = QtWidgets.QComboBox()
        self.field_type_dropdown.addItems(["INTEGER", "REAL", "TEXT", "BLOB", "NULL", "DATETIME"])

        self.not_null_checkbox = QtWidgets.QCheckBox("NOT NULL")
        self.primary_key_checkbox = QtWidgets.QCheckBox("PRIMARY KEY")
        self.auto_increment_checkbox = QtWidgets.QCheckBox("AUTOINCREMENT")

        self.foreign_key_checkbox = QtWidgets.QCheckBox("Foreign Key")

        self.add_button = QtWidgets.QPushButton("Add")

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.field_name_label)
        layout.addWidget(self.field_name_input)
        layout.addWidget(self.field_type_label)
        layout.addWidget(self.field_type_dropdown)
        layout.addWidget(self.not_null_checkbox)
        layout.addWidget(self.primary_key_checkbox)
        layout.addWidget(self.auto_increment_checkbox)
        layout.addWidget(self.foreign_key_checkbox)
        layout.addWidget(self.add_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.foreign_key_checkbox.stateChanged.connect(self.show_relation_dialog)
        self.add_button.clicked.connect(self.accept)

    # Public Methods
    # --------------
    def show_relation_dialog(self, state):
        if state == QtCore.Qt.Checked:
            dialog = AddRelationDialog(self.tables, self.parent())
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                self.relation_table, self.relation_field = dialog.get_relation_data()
            else:
                self.foreign_key_checkbox.setChecked(False)

    def get_field_data(self):
        field_name = self.field_name_input.text()
        field_type = self.field_type_dropdown.currentText()
        not_null = "NOT NULL" if self.not_null_checkbox.isChecked() else ""
        primary_key = "PRIMARY KEY" if self.primary_key_checkbox.isChecked() else ""
        auto_increment = "AUTOINCREMENT" if self.auto_increment_checkbox.isChecked() else ""

        if primary_key and auto_increment:
            field_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

        field_definition = f"{field_type} {not_null} {primary_key} {auto_increment}".strip()

        foreign_key = None
        if self.foreign_key_checkbox.isChecked() and self.relation_table and self.relation_field:
            foreign_key = f"{self.relation_table}({self.relation_field})"

        return field_name, field_definition, foreign_key

class AddTableDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Table")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.table_name_label = QtWidgets.QLabel("Table Name:")
        self.table_name_input = QtWidgets.QLineEdit()
        
        self.fields = []
        self.fields_layout = QtWidgets.QVBoxLayout()

        self.add_field_button = QtWidgets.QPushButton("Add Field")
        self.add_field_button.clicked.connect(self.add_field)

        self.create_table_button = QtWidgets.QPushButton("Create Table")
        self.create_table_button.clicked.connect(self.accept)

        self.layout.addWidget(self.table_name_label)
        self.layout.addWidget(self.table_name_input)
        self.layout.addLayout(self.fields_layout)
        self.layout.addWidget(self.add_field_button)
        self.layout.addWidget(self.create_table_button)

        self.setLayout(self.layout)

    def add_field(self):
        dialog = AddFieldDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            field_name, field_definition, _ = dialog.get_field_data()
            if field_name and field_definition:
                self.fields.append((field_name, field_definition))
                field_label = QtWidgets.QLabel(f"{field_name} {field_definition}")
                self.fields_layout.addWidget(field_label)

    def get_table_data(self):
        table_name = self.table_name_input.text()
        return table_name, self.fields

class AddRelationDialog(QtWidgets.QDialog):
    def __init__(self, tables, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Relation")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.tables = tables

        self.table_label = QtWidgets.QLabel("Reference Table:")
        self.table_dropdown = QtWidgets.QComboBox()
        self.table_dropdown.addItems(tables)
        self.table_dropdown.currentIndexChanged.connect(self.update_fields)

        self.field_label = QtWidgets.QLabel("Reference Field:")
        self.field_dropdown = QtWidgets.QComboBox()

        self.add_button = QtWidgets.QPushButton("Add Relation")
        self.add_button.clicked.connect(self.accept)

        self.layout.addWidget(self.table_label)
        self.layout.addWidget(self.table_dropdown)
        self.layout.addWidget(self.field_label)
        self.layout.addWidget(self.field_dropdown)
        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

        self.update_fields()

    def update_fields(self):
        selected_table = self.table_dropdown.currentText()
        if selected_table:
            fields = self.parent().db_manager.get_table_info(selected_table)
            self.field_dropdown.clear()
            self.field_dropdown.addItems([field[1] for field in fields])

    def get_relation_data(self):
        return self.table_dropdown.currentText(), self.field_dropdown.currentText()

class AddEditRecordDialog(QtWidgets.QDialog):
    def __init__(self, fields, types, record=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Record")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.fields = fields
        self.inputs = []
        self.auto_increment_fields = []

        for field, field_type in zip(fields, types):
            label = QtWidgets.QLabel(field)
            input_widget = self.create_input_widget(field_type)
            self.layout.addWidget(label)
            self.layout.addWidget(input_widget)
            self.inputs.append(input_widget)
            if "INTEGER PRIMARY KEY" in field_type:
                input_widget.setDisabled(True)
                self.auto_increment_fields.append(field)

        if record:
            for i, value in enumerate(record):
                self.set_input_value(self.inputs[i], value)

        self.submit_button = QtWidgets.QPushButton("Submit")
        self.submit_button.clicked.connect(self.accept)
        self.layout.addWidget(self.submit_button)

    def create_input_widget(self, field_type):
        if "INTEGER" in field_type and "PRIMARY KEY" not in field_type:
            widget = QtWidgets.QSpinBox()
            widget.setRange(-2147483648, 2147483647)  # Set the range for typical 32-bit integers
            widget.setSpecialValueText("")  # Allow clearing the value
            return widget
        elif "REAL" in field_type:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setSpecialValueText("")  # Allow clearing the value
            return widget
        elif "TEXT" in field_type:
            return QtWidgets.QLineEdit()
        elif "BLOB" in field_type:
            return self.create_blob_widget()
        elif "DATETIME" in field_type:
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
        if isinstance(input_widget, QtWidgets.QSpinBox) or isinstance(input_widget, QtWidgets.QDoubleSpinBox):
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
        return [self.get_input_value(input_field) for input_field in self.inputs]

    def get_input_value(self, input_widget):
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

        # Create tree data widget
        self.tree_data_widget = GroupableTreeWidget()
        self.tree_data_widget.setHeaderLabels([])  # Header labels will be set dynamically
        self.tree_data_widget.itemDoubleClicked.connect(self.edit_record)

        # Create layout for main area
        self.main_layout = QtWidgets.QVBoxLayout()
        self.actions_layout = QtWidgets.QHBoxLayout()
        self.actions_layout.addWidget(QtWidgets.QLabel("Actions:"))
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        self.actions_layout.addWidget(self.refresh_button)
        self.add_record_button = QtWidgets.QPushButton("Add Record")
        self.add_record_button.clicked.connect(self.show_add_record_dialog)
        self.add_table_button = QtWidgets.QPushButton("Add Table")
        self.add_table_button.clicked.connect(self.show_add_table_dialog)
        
        self.delete_table_button = QtWidgets.QPushButton("Delete Table")
        self.delete_table_button.clicked.connect(self.delete_table)
        self.delete_record_button = QtWidgets.QPushButton("Delete Record")
        self.delete_record_button.clicked.connect(self.delete_record)
        self.actions_layout.addWidget(self.add_record_button)

        self.actions_layout.addWidget(self.delete_record_button)
        self.actions_layout.addWidget(QtWidgets.QLabel("Filter:"))
        self.filter_input = QtWidgets.QLineEdit()
        self.actions_layout.addWidget(self.filter_input)
        self.main_layout.addLayout(self.actions_layout)
        self.main_layout.addWidget(QtWidgets.QLabel("Table Data"))
        self.main_layout.addWidget(self.tree_data_widget)

        self.central_widget.setLayout(self.main_layout)

        # Create dock widget for left layout
        self.dock_widget = QtWidgets.QDockWidget("SQLite Database Info", self)
        self.dock_widget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock_widget)

        # Create left layout
        self.left_widget = QtWidgets.QWidget()
        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_widget.setLayout(self.left_layout)

        self.db_name_label = QtWidgets.QLabel("Database Name:")
        self.db_name_display = QtWidgets.QLabel("")
        self.db_path_label = QtWidgets.QLabel("Database Path:")
        self.db_path_display = QtWidgets.QLabel("")
        self.db_size_label = QtWidgets.QLabel("Size:")
        self.db_size_display = QtWidgets.QLabel("")

        self.open_db_button = QtWidgets.QPushButton("Open Database")
        self.open_db_button.clicked.connect(self.open_database)

        self.tables_list = QtWidgets.QListWidget()
        self.tables_list.currentItemChanged.connect(self.load_table_info)

        self.columns_list = QtWidgets.QListWidget()

        self.add_field_button = QtWidgets.QPushButton("Add Field")
        self.add_field_button.clicked.connect(self.show_add_field_dialog)
        self.delete_field_button = QtWidgets.QPushButton("Delete Field")
        self.delete_field_button.clicked.connect(self.delete_field)

        # Add widgets to left layout
        self.left_layout.addWidget(self.open_db_button)
        self.left_layout.addWidget(self.db_name_label)
        self.left_layout.addWidget(self.db_name_display)
        self.left_layout.addWidget(self.db_path_label)
        self.left_layout.addWidget(self.db_path_display)
        self.left_layout.addWidget(self.db_size_label)
        self.left_layout.addWidget(self.db_size_display)
        
        sub_layout = QtWidgets.QHBoxLayout()
        self.left_layout.addLayout(sub_layout)
        sub_layout.addWidget(QtWidgets.QLabel("Tables"))
        sub_layout.addWidget(self.add_table_button)
        sub_layout.addWidget(self.delete_table_button)

        self.left_layout.addWidget(self.tables_list)
        sub_layout = QtWidgets.QHBoxLayout()
        self.left_layout.addLayout(sub_layout)
        sub_layout.addWidget(QtWidgets.QLabel("Columns"))
        
        sub_layout.addWidget(self.add_field_button)
        sub_layout.addWidget(self.delete_field_button)

        self.left_layout.addWidget(self.columns_list)

        # Set the left widget as the dock widget's content
        self.dock_widget.setWidget(self.left_widget)

        self.db_manager = None
        self.current_table = None

    def open_database(self):
        db_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Database", "", "SQLite Database Files (*.db *.sqlite)")
        if db_name:
            self.db_manager = DatabaseManager(db_name)
            self.db_name_display.setText(os.path.basename(db_name))
            self.db_path_display.setText(db_name)
            self.db_size_display.setText(f"{self.db_manager.get_database_size()} bytes")
            self.load_table_names()

    def load_table_names(self):
        if self.db_manager:
            tables = self.db_manager.get_table_names()
            self.tables_list.clear()
            self.tables_list.addItems(tables)

    def load_table_info(self, current_item):
        if current_item:
            table_name = current_item.text()
            self.current_table = table_name
            columns = self.db_manager.get_table_info(table_name)
            foreign_keys = self.db_manager.get_foreign_keys(table_name)
            self.columns_list.clear()
            column_names = []
            column_types = []
            for column in columns:
                column_names.append(column[1])
                column_types.append(column[2])
                column_definition = f"{column[1]} {column[2]} {column[3] and 'NOT NULL' or ''} {column[5] and 'PRIMARY KEY' or ''}".strip()
                for fk in foreign_keys:
                    if fk[3] == column[1]:
                        column_definition += f" (FK to {fk[2]}({fk[4]}))"
                self.columns_list.addItem(column_definition)
            self.column_names = column_names
            self.column_types = column_types
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
            dialog = AddFieldDialog(self.db_manager.get_table_names(), self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                field_name, field_definition, foreign_key = dialog.get_field_data()
                if field_name and field_definition:
                    self.db_manager.add_column(self.current_table, field_name, field_definition, foreign_key)
                    QtWidgets.QMessageBox.information(self, "Success", f"Field '{field_name}' added successfully.")
                    self.load_table_info(self.tables_list.currentItem())
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please enter valid field data.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def show_add_record_dialog(self):
        if self.current_table:
            dialog = AddEditRecordDialog(self.column_names, self.column_types, parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                values = dialog.get_record_data()
                values_filtered = [v for v, t in zip(values, self.column_types) if "PRIMARY KEY" not in t]
                column_names_filtered = [c for c, t in zip(self.column_names, self.column_types) if "PRIMARY KEY" not in t]
                if all(values_filtered):
                    self.db_manager.insert_record(self.current_table, column_names_filtered, values_filtered)
                    QtWidgets.QMessageBox.information(self, "Success", "Record added successfully.")
                    self.load_table_data()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please fill in all fields.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a table first.")

    def show_add_table_dialog(self):
        dialog = AddTableDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            table_name, fields = dialog.get_table_data()
            if table_name and fields:
                fields_dict = dict(fields)
                self.db_manager.create_table(table_name, fields_dict)
                QtWidgets.QMessageBox.information(self, "Success", f"Table '{table_name}' created successfully.")
                self.load_table_names()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "Please enter a valid table name and fields.")

    def edit_record(self, item, column):
        if self.current_table:
            row_data = [item.text(col) for col in range(len(self.column_names))]
            dialog = AddEditRecordDialog(self.column_names, self.column_types, row_data, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_values = dialog.get_record_data()
                if all(new_values):
                    rowid = int(item.text(0))  # Assuming the first column is the rowid
                    self.db_manager.update_record(self.current_table, self.column_names, new_values, rowid)
                    QtWidgets.QMessageBox.information(self, "Success", "Record updated successfully.")
                    self.load_table_data()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "Please fill in all fields.")
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
                QtWidgets.QMessageBox.information(self, "Success", "Table deleted successfully.")
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
                    QtWidgets.QMessageBox.information(self, "Success", "Field deleted successfully.")
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
                    QtWidgets.QMessageBox.information(self, "Success", "Record deleted successfully.")
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
