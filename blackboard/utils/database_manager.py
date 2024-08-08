# Type Checking Imports
# ---------------------
from typing import Generator, List, Tuple, Union, Optional, Dict

# Standard Library Imports
# ------------------------
import sqlite3
from dataclasses import dataclass
import os
import logging


# Class Definitions
# -----------------
@dataclass
class ForeignKey:
    """Represents a foreign key constraint in a database table.
    """
    table: str          # The referenced table name
    from_field: str     # The field in the current table
    to_field: str       # The field in the referenced table
    on_update: str      # The action on update (e.g., "CASCADE", "RESTRICT")
    on_delete: str      # The action on delete (e.g., "CASCADE", "RESTRICT")

    def get_foreign_key_definition(self) -> str:
        """Generate the SQL definition string for this foreign key.
        """
        return (f"FOREIGN KEY({self.from_field}) REFERENCES {self.table}({self.to_field}) "
                f"ON UPDATE {self.on_update} ON DELETE {self.on_delete}")

@dataclass
class FieldInfo:
    cid: int
    name: str
    type: str
    notnull: int
    dflt_value: str
    pk: int
    unique: bool = False
    fk: Optional[ForeignKey] = None

    def get_field_definition(self) -> str:
        """Generate the SQL definition string for this field."""
        definition = f"{self.name} {self.type}"
        if self.is_not_null:
            definition += " NOT NULL"
        if self.is_primary_key:
            definition += " PRIMARY KEY"
        if self.is_unique:
            definition += " UNIQUE"
        # if self.is_foreign_key:
        #     definition += f", {self.fk.get_foreign_key_definition()}"
        return definition

    @property
    def is_not_null(self) -> bool:
        return self.notnull == 1

    @property
    def is_primary_key(self) -> bool:
        return self.pk == 1

    @property
    def is_foreign_key(self) -> bool:
        return self.fk is not None

    @property
    def is_unique(self) -> bool:
        return self.unique

class DatabaseManager:

    FIELD_TYPES = ["INTEGER", "REAL", "TEXT", "BLOB", "NULL", "DATETIME", "ENUM"]
    PRIMARY_KEY_TYPES = ["INTEGER", "TEXT"]

    def __init__(self, db_name: str):
        """Initialize a DatabaseManager instance to interact with a SQLite database.

        Args:
            db_name (str): The name of the SQLite database file.

        Raises:
            sqlite3.Error: If there is an error connecting to the database.
        """
        self.db_name = db_name
        self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def _create_meta_display_field_table(self):
        """Create the meta table to store display field information.
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS _meta_display_field (
                table_name TEXT,
                field_name TEXT,
                display_foreign_field_name TEXT,
                display_format TEXT,
                PRIMARY KEY (table_name, field_name)
            );
        ''')
        self.connection.commit()

    def _create_meta_enum_field_table(self):
        """Create the meta table to store enum field information."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS _meta_enum_field (
                table_name TEXT,
                field_name TEXT,
                enum_table_name TEXT,
                description TEXT,
                PRIMARY KEY (table_name, field_name)
            );
        ''')
        self.connection.commit()

    def add_enum_metadata(self, table_name: str, field_name: str, enum_table_name: str, description: str = ""):
        self._create_meta_enum_field_table()
        self.cursor.execute('''
            INSERT INTO _meta_enum_field (table_name, field_name, enum_table_name, description)
            VALUES (?, ?, ?, ?);
        ''', (table_name, field_name, enum_table_name, description))
        self.connection.commit()

    def get_existing_enum_tables(self) -> List[str]:
        """Get a list of existing enum tables.

        Returns:
            List[str]: A list of table names that match the 'enum_%' pattern.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'enum_%'")
        return [row[0] for row in self.cursor.fetchall()]

    def get_enum_table_name(self, table_name: str, field_name: str) -> Optional[str]:
        """Retrieve the name of the enum table associated with a given field.
        """
        try:
            self.cursor.execute('''
                SELECT enum_table_name FROM _meta_enum_field
                WHERE table_name = ? AND field_name = ?;
            ''', (table_name, field_name))
        except sqlite3.OperationalError:
            pass

        if not (results := self.cursor.fetchone()):
            return

        return results[0]

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

    def create_enum_table(self, table_name: str, values: List[str]):
        """Create a table to store enum values.

        Args:
            enum_name (str): The name of the enum.
            values (List[str]): The values of the enum.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid enum name")

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

    def get_unique_fields(self, table_name: str) -> List[str]:
        """Retrieve the names of fields with unique constraints in a specified table.

        Args:
            table_name (str): The name of the table to retrieve unique fields from.

        Returns:
            List[str]: A set of field names that have unique constraints.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Retrieve the list of indexes for the table
        self.cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = self.cursor.fetchall()

        unique_fields = []

        # Iterate over the indexes and find those that are unique
        for index in indexes:
            index_name = index[1]
            if index[2]:  # If the index is unique
                self.cursor.execute(f"PRAGMA index_info({index_name})")
                index_fields = self.cursor.fetchall()
                for field in index_fields:
                    unique_fields.append(field[2])  # Add the field name to the set

        return unique_fields

    def get_table_info(self, table_name: str) -> Dict[str, FieldInfo]:
        """Retrieve information about the fields of a specified table, including whether they have UNIQUE constraints.

        Args:
            table_name (str): The name of the table to retrieve information from.

        Returns:
            List[FieldInfo]: A list of FieldInfo dataclass instances, each representing a field in the table.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Retrieve field information
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        fields = self.cursor.fetchall()

        # Get unique fields using the new method
        unique_fields = self.get_unique_fields(table_name)

        name_to_field_info = {field[1]: FieldInfo(*field, unique=(field[1] in unique_fields)) for field in fields}
        
        foreign_keys = self.get_foreign_keys(table_name)
        for foreign_key in foreign_keys:
            name_to_field_info[foreign_key.from_field].fk = foreign_key

        return name_to_field_info

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
        fields = self.cursor.fetchall()
        return [field[1] for field in fields]

    def get_foreign_keys(self, table_name: str) -> List[ForeignKey]:
        """Retrieve the foreign keys of a specified table.

        Args:
            table_name (str): The name of the table to retrieve foreign keys from.

        Returns:
            List[ForeignKey]: A list of ForeignKey data class instances, each representing a foreign key in the table.
                Each ForeignKey instance contains the following attributes:
                    - table: The name of the referenced table.
                    - from_field: The field in the current table.
                    - to_field: The field in the referenced table.
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
                from_field=fk[3],
                to_field=fk[4],
                on_update=fk[5],
                on_delete=fk[6]
            )
            for fk in foreign_keys
        ]

    def add_field(self, table_name: str, field_name: str, field_definition: str, foreign_key: Optional[str] = None, enum_values: Optional[List[str]] = None, enum_table_name: Optional[str] = None):
        """Add a new field to an existing table, optionally with a foreign key or enum constraint.

        Args:
            table_name (str): The name of the table to add the field to.
            field_name (str): The name of the new field.
            field_definition (str): The data type of the new field.
            foreign_key (Optional[str]): A foreign key constraint in the form of "referenced_table(referenced_field)".
            enum_values (Optional[List[str]]): A list of enum values if the field is of enum type.
            enum_table_name (Optional[str]): The name of an existing enum table if the field is an enum.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # Handle enum values or existing enum table
        if enum_values or enum_table_name:
            if not enum_table_name:
                enum_table_name = f"enum_{field_name}"
                self.create_enum_table(enum_table_name, enum_values)

            field_definition = "TEXT"
            foreign_key = f"{enum_table_name}(id)"
            self.add_enum_metadata(table_name, field_name, enum_table_name)

        # Fetch existing fields and foreign keys
        fields = self.get_table_info(table_name)
        foreign_keys = self.get_foreign_keys(table_name)

        # Create a new table schema with the new field
        new_fields = [field.get_field_definition() for field in fields.values()]

        # Add the new field definition
        new_fields.append(f"{field_name} {field_definition}")

        # Include existing foreign keys
        new_fields.extend(fk.get_foreign_key_definition() for fk in foreign_keys)

        # Add the new foreign key constraint if provided
        if foreign_key:
            new_fields.append(f"FOREIGN KEY({field_name}) REFERENCES {foreign_key}")

        new_fields_str = ', '.join(new_fields)

        temp_table_name = f"{table_name}_temp"
        self.cursor.execute(f"CREATE TABLE {temp_table_name} ({new_fields_str})")

        # Copy data from the old table to the new table
        old_fields_str = ', '.join(fields.keys())
        self.cursor.execute(f"INSERT INTO {temp_table_name} ({old_fields_str}) SELECT {old_fields_str} FROM {table_name}")

        # Drop the old table and rename the new table
        self.cursor.execute(f"DROP TABLE {table_name}")
        self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")

        self.connection.commit()

    def delete_field(self, table_name: str, field_name: str):
        """Delete a field from a table by recreating the table without that field.

        Args:
            table_name (str): The name of the table to delete the field from.
            field_name (str): The name of the field to delete.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # Retrieve the table information
        fields = self.get_table_info(table_name)

        # Disable foreign key constraints temporarily
        self.cursor.execute("PRAGMA foreign_keys=off;")
        try:
            # Filter out the field to be deleted
            new_fields = [field for field in fields.values() if field.name != field_name]
            field_names_str = ', '.join([field.name for field in new_fields])

            # Retrieve and filter foreign key constraints
            field_definitions = [field.get_field_definition() for field in new_fields]
            foreign_keys = self.get_foreign_keys(table_name)
            field_definitions.extend([fk.get_foreign_key_definition() for fk in foreign_keys if fk.from_field != field_name])
            field_definitions_str = ', '.join(field_definitions)

            # Create a temporary table with the new schema
            temp_table_name = f"{table_name}_temp"
            self.cursor.execute(f"CREATE TABLE {temp_table_name} ({field_definitions_str})")
            self.cursor.execute(f"INSERT INTO {temp_table_name} ({field_names_str}) SELECT {field_names_str} FROM {table_name}")
            # Replace the old table with the new one
            self.cursor.execute(f"DROP TABLE {table_name}")
            self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")

            # Remove the display field metadata
            self.remove_display_field(table_name, field_name)

            # Commit the transaction
            self.connection.commit()

        except sqlite3.Error as e:
            logging.error(f"Error deleting field '{field_name}' from table '{table_name}': {e}")
            self.connection.rollback()
            raise

        finally:
            # Re-enable foreign key constraints
            self.cursor.execute("PRAGMA foreign_keys=on;")

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

    def delete_record(self, table_name: str, pk_value: Union[int, str, float], pk_field: str = 'rowid'):
        """Delete a specific record from a table by primary key.

        Args:
            table_name (str): The name of the table to delete the record from.
            pk_field (str): The name of the primary key field.
            pk_value (Union[int, str, float]): The value of the primary key for the record to delete.

        Raises:
            ValueError: If the table name or pk_field is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not pk_field.isidentifier():
            raise ValueError("Invalid table name or primary key field")

        query = f"DELETE FROM {table_name} WHERE {pk_field} = ?"
        self.cursor.execute(query, (pk_value,))
        self.connection.commit()

    def delete_records(self, table_name: str, pk_values: List[Union[int, str, float]], pk_field: str = 'rowid'):
        """Delete multiple records from a table by a list of primary key values.

        Args:
            table_name (str): The name of the table to delete records from.
            pk_field (str): The name of the primary key field.
            pk_values (List[Union[int, str, float]]): A list of primary key values for the records to delete.

        Raises:
            ValueError: If the table name or pk_field is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not pk_field.isidentifier():
            raise ValueError("Invalid table name or primary key field")

        if not pk_values:
            return  # No values to delete

        placeholders = ', '.join('?' * len(pk_values))
        query = f"DELETE FROM {table_name} WHERE {pk_field} IN ({placeholders})"
        
        self.cursor.execute(query, pk_values)
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

    def get_view_names(self) -> List[str]:
        """Retrieve the names of all views in the database.

        Returns:
            List[str]: A list of view names present in the database.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        return [row[0] for row in self.cursor.fetchall()]

    def query_table_data(self, table_name: str, fields: Optional[List[str]] = None, where_clause: Optional[str] = None, as_dict: bool = False,
                        ) -> Union[Generator[Tuple, None, None], Generator[Dict[str, Union[int, str, float, None]], None, None]]:
        """Retrieve data from a specified table as a generator.

        Args:
            table_name (str): The name of the table to query data from.
            fields (Optional[List[str]]): Specific fields to retrieve. Defaults to all fields.
            where_clause (Optional[str]): Optional SQL WHERE clause to filter results.
            as_dict (bool): If True, yield rows as dictionaries.

        Yields:
            Union[Generator[Tuple, None, None], Generator[Dict[str, Union[int, str, float, None]], None, None]]:
            Yields each row, either as a tuple of field values or a dictionary.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        fields = fields or self.get_field_names(table_name)

        # Ensure all fields are valid identifiers
        if not all(field.isidentifier() for field in fields):
            raise ValueError("Invalid field name")

        fields_str = ', '.join(fields)

        query = f"SELECT {fields_str} FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        self.cursor.execute(query)

        if as_dict:
            yield from (dict(zip(fields, row)) for row in self.cursor)
        else:
            yield from self.cursor

    def fetch_related_value(self, related_table_name: str, target_field_name: str,
                            reference_field_name: str, foreign_key_value: Union[int, str, float],
                           ) -> Optional[Union[int, str, float]]:
        """Retrieve a value from a related table based on a foreign key.

        Args:
            related_table_name (str): The name of the related table to fetch the value from.
            target_field_name (str): The specific field in the related table to retrieve.
            reference_field_name (str): The field in the related table that corresponds to the foreign key.
            foreign_key_value (Union[int, str, float]): The foreign key value from the source table.

        Returns:
            Optional[Union[int, str, float]]: The value from the specified field in the related table, or None if no match is found.

        Raises:
            ValueError: If any of the table or field names are not valid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not all(map(str.isidentifier, [related_table_name, target_field_name, reference_field_name])):
            raise ValueError("Invalid table name or field names")

        # Use the fetch_one method to retrieve the related row
        query = f"SELECT {target_field_name} FROM {related_table_name} WHERE {reference_field_name} = ?"
        self.cursor.execute(query, (foreign_key_value,))

        if not (results := self.cursor.fetchone()):
            return

        return results[0]

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

    def update_record(self, table_name: str, fields: List[str], values: List, pk_value: Union[int, str, float], pk_field: str = 'rowid'):
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
        if (not table_name.isidentifier() or 
            not all(f.isidentifier() for f in fields) or
            not pk_field.isidentifier()
           ):
            raise ValueError("Invalid table name or field names")

        set_clause = ', '.join([f"{field} = ?" for field in fields])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {pk_field} = ?"
        self.cursor.execute(sql, values + [pk_value])
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
        fields = self.cursor.fetchall()
        for field in fields:
            if field[1] == field_name:
                return field[2]  # Return the data type

        raise ValueError(f"Field '{field_name}' not found in table '{table_name}'")

    def get_primary_keys(self, table_name: str) -> List[str]:
        """Retrieve the primary keys of a specified table.
        
        Args:
            table_name (str): The name of the table to retrieve primary keys from.

        Returns:
            List[str]: A list of primary key field names. If it's a composite key, multiple fields are returned.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        self.cursor.execute(f"PRAGMA table_info({table_name})")
        fields = self.cursor.fetchall()

        # Filter fields to include only those that are part of the primary key
        primary_keys = [field[1] for field in fields if field[5] == 1]  # field[5] indicates the primary key part
        return primary_keys

    # TODO: Test
    def create_junction_table(self, junction_table_name: str, table1: str, field1: str, table2: str, field2: str):
        """Create a junction table for many-to-many relationships.

        Args:
            junction_table_name (str): The name of the junction table.
            table1 (str): The name of the first table.
            field1 (str): The name of the field in the first table.
            table2 (str): The name of the second table.
            field2 (str): The name of the field in the second table.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not junction_table_name.isidentifier():
            raise ValueError("Invalid junction table name")

        # Define the junction table schema
        junction_fields = {
            f"{table1}_id": "INTEGER NOT NULL",
            f"{table2}_id": "INTEGER NOT NULL",
            "PRIMARY KEY": f"({table1}_id, {table2}_id)"
        }

        # Create the junction table
        self.create_table(junction_table_name, junction_fields)

        # Add foreign key constraints to the junction table
        self.add_field(
            junction_table_name,
            f"{table1}_id",
            "INTEGER",
            foreign_key=f"{table1}(rowid)"
        )

        self.add_field(
            junction_table_name,
            f"{table2}_id",
            "INTEGER",
            foreign_key=f"{table2}(rowid)"
        )

    def add_display_field(self, table_name: str, field_name: str, display_field_name: str, display_format: str = None):
        """Add a display field entry to the meta table.
        """
        self._create_meta_display_field_table()
        self.cursor.execute('''
            INSERT OR REPLACE INTO _meta_display_field (table_name, field_name, display_foreign_field_name, display_format)
            VALUES (?, ?, ?, ?);
        ''', (table_name, field_name, display_field_name, display_format))
        self.connection.commit()

    def get_display_field(self, table_name: str, field_name: str) -> Optional[Tuple[str, str]]:
        """Retrieve the display field name and format for a specific field.
        """
        try:
            self.cursor.execute('''
                SELECT display_foreign_field_name, display_format
                FROM _meta_display_field
                WHERE table_name = ? AND field_name = ?;
            ''', (table_name, field_name))
        except sqlite3.OperationalError:
            pass

        if not (results := self.cursor.fetchone()):
            return

        return results[0]

    def remove_display_field(self, table_name: str, field_name: str):
        """Remove a display field entry from the meta table.
        """
        try:
            self.cursor.execute('''
                DELETE FROM _meta_display_field
                WHERE table_name = ? AND field_name = ?;
            ''', (table_name, field_name))
            self.connection.commit()
        except sqlite3.OperationalError:
            pass

    # NOTE: Tmp
    def create_view_with_display_field(
        self, 
        view_name: str, 
        main_table: str, 
        field_name: str, 
        reference_table: str, 
        key_field: str, 
        display_field: str
    ):
        """
        Create a view that includes the display field from the reference table.

        Args:
            view_name (str): The name of the view to be created.
            main_table (str): The name of the main table.
            field_name (str): The field name in the main table that references the key field in the reference table.
            reference_table (str): The name of the reference table.
            key_field (str): The key field in the reference table.
            display_field (str): The display field in the reference table.
        """
        # Construct the SQL to create the view
        create_view_sql = f"""
        CREATE VIEW IF NOT EXISTS {view_name} AS
        SELECT 
            {main_table}.*,
            {reference_table}.{display_field} AS {field_name}_{display_field}
        FROM 
            {main_table}
        JOIN 
            {reference_table}
        ON 
            {main_table}.{field_name} = {reference_table}.{key_field};
        """

        # Execute the SQL command to create the view
        self.cursor.execute(create_view_sql)
        self.connection.commit()
