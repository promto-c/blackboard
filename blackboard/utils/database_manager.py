# Type Checking Imports
# ---------------------
from typing import Generator, List, Tuple, Union, Optional, Dict, Any

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
class ManyToManyField:
    """Represents a many-to-many relationship field."""
    from_table: str                         # The name of the originating table
    track_field_name: str                   # The field name in the originating table
    junction_table: str                     # The name of the junction table

@dataclass
class FieldInfo:
    cid: int = -1
    name: str = ''
    type: str = 'NULL'
    notnull: int = 0
    dflt_value: Optional[str] = None
    pk: int = 0
    unique: bool = False
    fk: Optional[ForeignKey] = None
    m2m: Optional[ManyToManyField] = None

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
        return bool(self.notnull)

    @property
    def is_primary_key(self) -> bool:
        return bool(self.pk)

    @property
    def is_foreign_key(self) -> bool:
        return self.fk is not None

    @property
    def is_unique(self) -> bool:
        return self.unique

    @property
    def is_many_to_many(self) -> bool:
        """Check if the field is part of a many-to-many relationship.
        """
        return self.m2m is not None

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
        """Create the meta table to store enum field information.
        """
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

    def _create_meta_many_to_many_table(self):
        """Create the meta table to store many-to-many relationship information, including display field names.
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS _meta_many_to_many (
                from_table TEXT NOT NULL,
                track_field_name TEXT NOT NULL,
                junction_table TEXT NOT NULL,
                PRIMARY KEY (from_table, track_field_name)
            );
        ''')
        self.connection.commit()

    def is_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the current database.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name=?
        ''', (table_name,))

        exists = cursor.fetchone() is not None
        cursor.close()
        
        return exists

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
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()

        unique_fields = []

        # Iterate over the indexes and find those that are unique
        for index in indexes:
            index_name = index[1]
            if index[2]:  # If the index is unique
                cursor.execute(f"PRAGMA index_info({index_name})")
                index_fields = cursor.fetchall()
                for field in index_fields:
                    unique_fields.append(field[2])  # Add the field name to the set
        cursor.close()

        return unique_fields

    def get_fields(self, table_name: str, include_many_to_many: bool = False) -> Dict[str, 'FieldInfo']:
        """Retrieve all fields of the specified table, including unique constraints and many-to-many relationships.

        Args:
            table_name (str): The name of the table to retrieve fields from.
            include_many_to_many (bool): Whether to include many-to-many relationship fields. Defaults to False.

        Returns:
            Dict[str, FieldInfo]: A dictionary where keys are field names and values are FieldInfo dataclass instances, 
                representing the fields in the table and their properties.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Retrieve field information
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        fields = cursor.fetchall()
        cursor.close()

        # Get unique fields using the new method
        unique_fields = self.get_unique_fields(table_name)

        # Create a dictionary mapping field names to FieldInfo objects
        name_to_field_info = {field[1]: FieldInfo(*field, unique=(field[1] in unique_fields)) for field in fields}

        # Add foreign key information to the FieldInfo objects
        foreign_keys = self.get_foreign_keys(table_name)
        for foreign_key in foreign_keys:
            name_to_field_info[foreign_key.from_field].fk = foreign_key

        # Include many-to-many fields if requested
        if include_many_to_many:
            many_to_many_fields = self.get_many_to_many_fields(table_name)
            for field_name, m2m_field in many_to_many_fields.items():
                # Add the many-to-many field with a reference to the junction table
                name_to_field_info[field_name] = FieldInfo(
                    name=field_name,
                    type='MANY_TO_MANY',  # Use a custom type for many-to-many fields
                    m2m=m2m_field  # Store the many-to-many relationship info
                )

        return name_to_field_info

    def get_field(self, table_name: str, field_name: str) -> FieldInfo:
        """Get information for a specific field (column) in a table.

        Args:
            table_name (str): The name of the table.
            field_name (str): The name of the field to get information for.

        Returns:
            FieldInfo: The FieldInfo instance representing the field's information.
        """
        fields = self.get_fields(table_name, include_many_to_many=True)
        return fields.get(field_name)

    def get_possible_values(self, table_name: str, display_field: Optional[str] = None) -> List[str]:
        """Get possible values from a related table using a display field.

        Args:
            table_name (str): The name of the related table.
            display_field (Optional[str]): The field to display. Defaults to the primary key.

        Returns:
            List[str]: A list of possible values from the specified display field.
        """
        # Determine the display field: use the provided display field or default to the primary key
        display_field = display_field or self.get_primary_keys(table_name)[0]

        # Ensure the display field exists in the table
        if display_field not in self.get_field_names(table_name):
            raise ValueError(f"Field '{display_field}' does not exist in table '{table_name}'")

        # Execute query to get the unique values for the display field
        self.cursor.execute(f"SELECT DISTINCT {display_field} FROM {table_name} ORDER BY {display_field}")
        return [row[0] for row in self.cursor.fetchall()]

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

    def get_foreign_keys(self, table_name: str) -> List['ForeignKey']:
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

        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = cursor.fetchall()
        cursor.close()

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

    def get_many_to_many_fields(self, table_name: str) -> Dict[str, 'ManyToManyField']:
        """Retrieve many-to-many relationships for a specified table.

        Args:
            table_name (str): The name of the table to retrieve many-to-many relationships for.

        Returns:
            Dict[str, ManyToManyField]: A dictionary where keys are `track_field_name` and values are ManyToManyField 
                dataclass instances representing the relationships.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Return an empty dictionary if the _meta_many_to_many table does not exist
        if not self.is_table_exists('_meta_many_to_many'):
            return {}

        # Proceed with fetching the many-to-many relationships
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT track_field_name, junction_table
            FROM _meta_many_to_many
            WHERE from_table = ?
        ''', (table_name,))
        
        records = cursor.fetchall()
        cursor.close()

        # Create a dictionary with track_field_name as keys and ManyToManyField instances as values
        return {
            record[0]: ManyToManyField(
                from_table=table_name,
                track_field_name=record[0],
                junction_table=record[1],
            )
            for record in records
        }

    def get_many_to_many_field_names(self, table_name: str) -> List[str]:
        """Retrieve the track field names of all many-to-many relationships for the current table.

        Args:
            table_name (str): The name of the table for which to retrieve many-to-many field names.

        Returns:
            List[str]: A list of track field names representing many-to-many relationships in the current table.
        """
        return list(self.get_many_to_many_fields(table_name).keys())

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
        fields = self.get_fields(table_name)
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
        fields = self.get_fields(table_name)

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
            self._remove_display_field(table_name, field_name)

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

    def delete_record(self, table_name: str, pk_values: Union[Dict[str, Any], Any], pk_field: Optional[str] = None):
        """Delete a specific record from a table by primary key, including related data in many-to-many junction tables.

        Args:
            table_name (str): The name of the table to delete the record from.
            pk_values (Union[Dict[str, Any], Any]): The primary key value(s) for the record to delete.
                Can be a single value or a dictionary of field-value pairs for composite keys.
            pk_field (Optional[str]): The name of the primary key field, required only for single-key deletions.

        Raises:
            ValueError: If the table name or primary key field is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Determine if the deletion is for a single key or composite keys
        if isinstance(pk_values, dict):
            # Composite key handling
            if not all(isinstance(k, str) and k.isidentifier() for k in pk_values.keys()):
                raise ValueError("Invalid primary key fields")

            # Create a dynamic WHERE clause for composite keys
            where_clause = " AND ".join(f"{field} = ?" for field in pk_values.keys())
            where_values = list(pk_values.values())

        elif pk_field and pk_field.isidentifier():
            # Single key handling
            if not pk_field.isidentifier():
                raise ValueError("Invalid primary key field")

            where_clause = f"{pk_field} = ?"
            where_values = [pk_values]
        else:
            raise ValueError("Primary key field is required for single-key deletions")

        # TODO: Handle composite pks
        # First, delete related data in the many-to-many junction tables
        m2m_fields = self.get_many_to_many_fields(table_name)
        for m2m_field in m2m_fields.values():
            junction_table = m2m_field.junction_table
            fks = self.get_foreign_keys(junction_table)

            for fk in fks:
                if fk.table == table_name:
                    from_table_fk = fk
                    break

            # Delete related entries in the junction table
            self.cursor.execute(f'''
                DELETE FROM {junction_table}
                WHERE {from_table_fk.from_field} = ?
            ''', (list(pk_values.values())[0],))

        # Then, delete the main record from the table
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        self.cursor.execute(query, where_values)
        self.connection.commit()

    # TODO: Handle composite pks
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

    def get_many_to_many_data(self, table_name: str, track_field: str, from_values: Optional[List[Union[int, str, float]]] = None,
                              display_field: str = '', display_field_label: str = '') -> List[Dict[str, Union[int, str, float]]]:
        """Retrieve the display field data related to specific records in a many-to-many relationship.

        Args:
            table_name (str): The name of the table from which the relationship starts.
            track_field (str): The field name that tracks the many-to-many relationship.
            from_values (Optional[List[Union[int, str, float]]]): A list of values in the from_table to match. If None, retrieve for all.
            display_field (str): The name of the display field in the related table to retrieve.

        Returns:
            List[Dict[str, Union[int, str, float]]]: A list of dictionaries, each containing the 'id' from the original table and the corresponding list of related tags or other display fields.
        """
        cursor = self.connection.cursor()
        # Retrieve the junction table associated with the many-to-many field
        cursor.execute('''
            SELECT junction_table
            FROM _meta_many_to_many
            WHERE from_table = ? AND track_field_name = ?
        ''', (table_name, track_field))

        junction_table = cursor.fetchone()[0]

        # Identify foreign key relationships in the junction table
        fks = self.get_foreign_keys(junction_table)
        for fk in fks:
            if fk.table == table_name:
                from_table_fk = fk
                key_type = self.get_field_type(table_name, from_table_fk.to_field)
            else:
                to_table_fk = fk

        # Determine the display field and its type
        display_field = display_field or to_table_fk.to_field
        display_field_type = self.get_field_type(to_table_fk.table, display_field)

        # Retrieve all values if not specified
        if from_values is None:
            cursor.execute(f'''
                SELECT DISTINCT {from_table_fk.from_field}
                FROM {junction_table}
            ''')
            from_values = [row[0] for row in cursor.fetchall()]

        # Prepare the SQL query
        placeholders = ', '.join('?' for _ in from_values)
        query = f'''
            SELECT CAST({junction_table}.{from_table_fk.from_field} AS {key_type}) AS {from_table_fk.to_field},
                GROUP_CONCAT({to_table_fk.table}.{display_field}) AS {track_field}
            FROM {junction_table}
            JOIN {to_table_fk.table} ON {junction_table}.{to_table_fk.from_field} = {to_table_fk.table}.{to_table_fk.to_field}
            WHERE {junction_table}.{from_table_fk.from_field} IN ({placeholders})
            GROUP BY {junction_table}.{from_table_fk.from_field}
        '''

        cursor.execute(query, from_values)
        results = cursor.fetchall()
        cursor.close()

        # Convert each result row into a dictionary, converting display fields back to their original type
        def convert_value(value: str, value_type: str) -> Union[int, str, float]:
            if value_type == 'INTEGER':
                return int(value)
            elif value_type == 'REAL':
                return float(value)
            else:
                return value

        display_field_label = display_field_label or track_field
        # Return data with proper formatting
        return [
            {
                from_table_fk.to_field: row[0],
                display_field_label: [convert_value(val, display_field_type) for val in row[1].split(',')]
            }
            for row in results
        ]

    def query_table_data(self, table_name: str, fields: Optional[List[str]] = None, where_clause: Optional[str] = None,
                         as_dict: bool = False, handle_m2m: bool = False
                        ) -> Union[Generator[Tuple, None, None], Generator[Dict[str, Union[int, str, float, None]], None, None]]:
        """Retrieve data from a specified table as a generator.

        Args:
            table_name (str): The name of the table to query data from.
            fields (Optional[List[str]]): Specific fields to retrieve. Defaults to all fields.
            where_clause (Optional[str]): Optional SQL WHERE clause to filter results.
            as_dict (bool): If True, yield rows as dictionaries.
            handle_m2m (bool): Whether to retrieve many-to-many related data as well.

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

        many_to_many_field_names = self.get_many_to_many_field_names(table_name) if handle_m2m else []
        fields = [field for field in fields if field not in many_to_many_field_names]
        fields_str = ', '.join(fields)

        query = f"SELECT {fields_str} FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        cursor = self.connection.cursor()
        try:
            cursor.execute(query)

            if handle_m2m:
                for row in cursor:
                    row_dict = dict(zip(fields, row))
                    for m2m_field in many_to_many_field_names:
                        m2m_data = self.get_many_to_many_data(table_name, m2m_field, [row_dict[self.get_primary_keys(table_name)[0]]])
                        if not m2m_data:
                            continue
                        row_dict[m2m_field] = m2m_data[0].get(m2m_field, [])

                    if as_dict:
                        yield row_dict
                    else:
                        yield tuple(row_dict.values())

            else:
                if as_dict:
                    yield from (dict(zip(fields, row)) for row in cursor)
                else:
                    yield from cursor

        finally:
            cursor.close()

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

    def insert_record(self, table_name: str, data_dict: Dict[str, Union[int, str, float, None]],
                      handle_m2m: bool = False) -> int:
        """Insert a new record into a table.

        Args:
            table_name (str): The name of the table to insert the record into.
            data_dict (Dict[str, Union[int, str, float, None]]): A dictionary mapping field names to their values.
            handle_m2m (bool): Whether to handle many-to-many relationships. Defaults to False.

        Returns:
            int: The rowid of the newly inserted record.

        Raises:
            ValueError: If the table name or field names are not valid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not table_name.isidentifier() or not all(f.isidentifier() for f in data_dict.keys()):
            raise ValueError("Invalid table name or field names")

        # Separate M2M data from the main data if handling M2M relationships
        m2m_data = {}
        if handle_m2m:
            for track_field_name in self.get_many_to_many_field_names(table_name):
                if track_field_name not in data_dict:
                    continue
                m2m_data[track_field_name] = data_dict.pop(track_field_name)

        # Insert the main record
        field_names = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?'] * len(data_dict))
        sql = f"INSERT INTO {table_name} ({field_names}) VALUES ({placeholders})"
        self.cursor.execute(sql, list(data_dict.values()))
        self.connection.commit()

        # Get the primary key of the newly inserted record
        rowid = self.cursor.lastrowid

        # Insert M2M data into the junction table(s) if handling M2M relationships
        if handle_m2m:
            for track_field_name, selected_values in m2m_data.items():
                self.update_junction_table(table_name, track_field_name, rowid, selected_values, is_rowid=True)

        return rowid

    # TODO: Handle composite pks
    def update_record(self, table_name: str, data_dict: Dict[str, Union[int, str, float, None]], 
                      pk_value: Union[int, str, float], pk_field: str = 'rowid', handle_m2m: bool = False):
        """Update an existing record in a table by primary key.

        Args:
            table_name (str): The name of the table containing the record to update.
            data_dict (Dict[str, Union[int, str, float, None]]): A dictionary mapping field names to their new values.
            pk_value (Union[int, str, float]): The primary key value of the record to update.
            pk_field (str): The name of the primary key field. Defaults to 'rowid'.
            handle_m2m (bool): Whether to handle many-to-many relationships. Defaults to False.

        Raises:
            ValueError: If the table name or field names are not valid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if (not table_name.isidentifier() or 
            not all(f.isidentifier() for f in data_dict.keys()) or
            not pk_field.isidentifier()
        ):
            raise ValueError("Invalid table name or field names")

        # Separate M2M data from the main data if handling M2M relationships
        m2m_data = {}
        if handle_m2m:
            for track_field_name in self.get_many_to_many_field_names(table_name):
                if track_field_name not in data_dict:
                    continue
                m2m_data[track_field_name] = data_dict.pop(track_field_name)

        if data_dict:
            # Update the main record
            set_clause = ', '.join([f"{field} = ?" for field in data_dict.keys()])
            sql = f"UPDATE {table_name} SET {set_clause} WHERE {pk_field} = ?"
            self.cursor.execute(sql, list(data_dict.values()) + [pk_value])
            self.connection.commit()

        # Update M2M data in the junction table(s) if handling M2M relationships
        if handle_m2m:
            for track_field_name, selected_values in m2m_data.items():
                self.update_junction_table(table_name, track_field_name, pk_value, selected_values)

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

        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        fields = cursor.fetchall()
        cursor.close()

        # Filter fields to include only those that are part of the primary key
        primary_keys = [field[1] for field in fields if field[5]]  # field[5] indicates the primary key part
        return primary_keys

    def create_junction_table(self, from_table: str, to_table: str, from_field: str = 'id', to_field: str = 'id',
                            junction_table_name: Optional[str] = None, track_field_name: str = None, track_field_vice_versa_name: str = None,
                            from_display_field: Optional[str] = None, to_display_field: Optional[str] = None,
                            track_vice_versa: bool = False):
        """Create a junction table to represent a many-to-many relationship between two tables.

        Args:
            from_table (str): The name of the first table involved in the relationship.
            to_table (str): The name of the second table involved in the relationship.
            from_field (str): The field in the first table that is referenced by the foreign key (default is 'id').
            to_field (str): The field in the second table that is referenced by the foreign key (default is 'id').
            junction_table_name (Optional[str]): The name of the junction table to be created. Defaults to '{from_table}_{to_table}' in alphabetical order.
            from_display_field (Optional[str]): The field from the "from" table to be used for display purposes.
            to_display_field (Optional[str]): The field from the "to" table to be used for display purposes.
            track_vice_versa (bool): Whether to track the relationship in both directions.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        # Assign the default junction table name if not provided
        junction_table_name = junction_table_name or f"{'_'.join(sorted([from_table, to_table]))}"
        track_field_name = track_field_name or f"{to_table}_{to_field}s"
        track_field_vice_versa_name = track_field_vice_versa_name or f"{from_table}_{from_field}s"

        # Set keys
        from_table_key = f"{from_table}_{from_field}"
        to_table_key = f"{to_table}_{to_field}"

        # Construct the SQL for creating the junction table
        sql = f"""
            CREATE TABLE IF NOT EXISTS {junction_table_name} (
                {from_table_key} TEXT NOT NULL,
                {to_table_key} TEXT NOT NULL,
                PRIMARY KEY ({from_table_key}, {to_table_key}),
                FOREIGN KEY ({from_table_key}) REFERENCES {from_table}({from_field}) ON DELETE CASCADE,
                FOREIGN KEY ({to_table_key}) REFERENCES {to_table}({to_field}) ON DELETE CASCADE
            );
        """

        # Execute the SQL command
        self.cursor.execute(sql)
        self.connection.commit()

        self._create_meta_many_to_many_table()

        # Track the many-to-many relationship in the metadata table
        self.cursor.execute('''
            INSERT OR REPLACE INTO _meta_many_to_many (
                from_table, track_field_name, junction_table
            ) VALUES (?, ?, ?);
        ''', (from_table, track_field_name, junction_table_name))

        # Add display field metadata for the "to" table
        if to_display_field:
            self.add_display_field(junction_table_name, to_table_key, to_display_field)
            self.add_display_field(from_table, track_field_name, to_display_field)

        # Optionally track the relationship in the reverse direction
        if track_vice_versa:
            self.cursor.execute('''
                INSERT OR REPLACE INTO _meta_many_to_many (
                    from_table, track_field_name, junction_table
                ) VALUES (?, ?, ?);
            ''', (to_table, track_field_vice_versa_name, junction_table_name))

            # Add display field metadata for the "from" table
            if from_display_field:
                self.add_display_field(junction_table_name, from_table_key, from_display_field)
                self.add_display_field(to_table, track_field_vice_versa_name, from_display_field)

        self.connection.commit()

    def update_junction_table(self, from_table: str, track_field_name: str, from_value: Union[int, str, float], 
                            selected_values: List[Union[int, str, float]], is_rowid: bool = False):
        """Update the junction table for a many-to-many relationship.

        Args:
            from_table (str): The name of the table from which the relationship starts.
            track_field_name (str): The field name that tracks the many-to-many relationship.
            from_value (Union[int, str, float]): The value in the from_table to match, either a rowid or an existing key.
            selected_values (List[Union[int, str, float]]): The list of values to insert into the junction table.
            is_rowid (bool): Indicates if `from_value` is a rowid that needs to be translated into the corresponding foreign key value.
        """
        self.cursor.execute('''
            SELECT junction_table
            FROM _meta_many_to_many
            WHERE from_table = ? AND track_field_name = ?
        ''', (from_table, track_field_name))
        
        junction_table = self.cursor.fetchone()[0]
        fks = self.get_foreign_keys(junction_table)
        for fk in fks:
            if fk.table == from_table:
                from_table_fk = fk
            else:
                to_table_fk = fk

        if is_rowid:
            # Translate the rowid into the corresponding foreign key value
            self.cursor.execute(f'''
                SELECT {from_table_fk.to_field}
                FROM {from_table}
                WHERE rowid = ?
            ''', (from_value,))
            from_value = self.cursor.fetchone()[0]

        # Clear existing junction table entries for this record
        self.cursor.execute(f'''
            DELETE FROM {junction_table}
            WHERE {from_table_fk.from_field} = ?
        ''', (from_value,))

        # Insert new entries into the junction table
        for value in selected_values:
            self.cursor.execute(f'''
                INSERT INTO {junction_table} ({from_table_fk.from_field}, {to_table_fk.from_field})
                VALUES (?, ?)
            ''', (from_value, value))
        
        self.connection.commit()

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

    def _remove_display_field(self, table_name: str, field_name: str):
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
