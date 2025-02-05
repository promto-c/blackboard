
# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, Generator, List, Tuple, Union, Optional, Dict, Any
if TYPE_CHECKING:
    from blackboard.enums.view_enum import SortOrder

# Standard Library Imports
# ------------------------
import logging
import sqlite3

# Local Imports
# -------------
from .abstract_database import AbstractDatabase, AbstractModel
from .schema import FieldInfo, ManyToManyField, ForeignKey
from .sql_query_builder import SQLQueryBuilder


# Class Definitions
# -----------------
class SQLiteDatabase(AbstractDatabase):

    # Initialization and Setup
    # ------------------------
    def __init__(self, db_name: str, read_only: bool = False):
        """Initialize the AbstractDatabase with a database name.

        Args:
            db_name (str): The name of the database file or connection string.
        """
        self._db_name = db_name
        if read_only:
            self._connection = sqlite3.connect(f'file:///{self._db_name}?mode=ro' ,uri=True, check_same_thread=False)
        else:
            self._connection = sqlite3.connect(self._db_name, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._cursor = self._connection.cursor()

    # Public Methods
    # --------------
    def create_junction_table(self, from_table: str, to_table: str, from_field: str = 'id', to_field: str = 'id',
                              junction_table_name: Optional[str] = None, track_field_name: str = None, track_field_vice_versa_name: str = None,
                              from_display_field: Optional[str] = None, to_display_field: Optional[str] = None,
                              track_vice_versa: bool = False) -> 'AbstractModel':
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
        self._cursor.execute(sql)
        self._connection.commit()

        self._create_meta_many_to_many_table()

        # Track the many-to-many relationship in the metadata table
        self._cursor.execute('''
            INSERT OR REPLACE INTO _meta_many_to_many (
                from_table, track_field_name, junction_table
            ) VALUES (?, ?, ?);
        ''', (from_table, track_field_name, junction_table_name))

        # Add display field metadata for the "to" table
        if to_display_field:
            junction_model = self.get_model(junction_table_name)
            junction_model.add_display_field(to_table_key, to_display_field)

            from_model = self.get_model(from_table)
            from_model.add_display_field(track_field_name, to_display_field)

        # Optionally track the relationship in the reverse direction
        if track_vice_versa:
            self._cursor.execute('''
                INSERT OR REPLACE INTO _meta_many_to_many (
                    from_table, track_field_name, junction_table
                ) VALUES (?, ?, ?);
            ''', (to_table, track_field_vice_versa_name, junction_table_name))

            # Add display field metadata for the "from" table
            if from_display_field:
                junction_model = self.get_model(junction_table_name)
                junction_model.add_display_field(from_table_key, from_display_field)

                to_model = self.get_model(to_table)
                to_model.add_display_field(track_field_vice_versa_name, from_display_field)

        self._connection.commit()

        return self.get_model(junction_table_name)

    # Private Methods
    # ---------------
    def _create_meta_many_to_many_table(self):
        """Create the meta table to store many-to-many relationship information.
        """
        fields = {
            'from_table': 'TEXT NOT NULL',
            'track_field_name': 'TEXT NOT NULL',
            'junction_table': 'TEXT NOT NULL',
            'PRIMARY KEY': '(from_table, track_field_name)'
        }
        self.create_table('_meta_many_to_many', fields)

    # Class Properties
    # ----------------
    @property
    def connection(self):
        """Get the current database connection.
        """
        return self._connection

    @property
    def cursor(self):
        return self._cursor

    # Overridden Methods
    # ------------------
    def is_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the current database.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        cursor = self._connection.cursor()
        cursor.execute('''
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name=?
        ''', (table_name,))

        return cursor.fetchone() is not None

    def create_table(self, table_name: str, fields: Dict[str, str]) -> 'AbstractModel':
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
        self._cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({fields_str})")
        self._connection.commit()

        return self.get_model(table_name)

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

        self._cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self._connection.commit()

    def get_table_names(self) -> List[str]:
        """Retrieve the names of all tables in the database.

        Returns:
            List[str]: A list of table names present in the database.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in self._cursor.fetchall()]

    def get_view_names(self) -> List[str]:
        """Retrieve the names of all views in the database.

        Returns:
            List[str]: A list of view names present in the database.

        Raises:
            sqlite3.Error: If there is an error executing the SQL command.
        """
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        return [row[0] for row in self._cursor.fetchall()]

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

        self._cursor.execute(
            f"SELECT type FROM pragma_table_info(?) WHERE name = ?",
            (table_name, field_name)
        )

        row = self._cursor.fetchone()
        return row[0]

    def get_model(self, table_name: str):
        return SQLiteModel(self, table_name)

    def close(self):
        """Close the database cursor and connection.

        This method ensures that both the cursor and the connection to the SQLite database
        are properly closed. It is idempotent, meaning that calling it multiple times
        will have no adverse effects.

        Raises:
            sqlite3.Error: If an error occurs while closing the cursor or connection.
        """
        try:
            if self._cursor:
                self._cursor.close()
                self._cursor = None
                print("Cursor closed successfully.")
        except sqlite3.Error as e:
            print(f"Error closing cursor: {e}")
            raise

        try:
            if self._connection:
                self._connection.close()
                self._connection = None
                print("Connection closed successfully.")
        except sqlite3.Error as e:
            print(f"Error closing connection: {e}")
            raise

class SQLiteModel(AbstractModel):
    def __init__(self, database: SQLiteDatabase, table_name: str):
        self._database = database
        self._table_name = table_name

        self._connection = self._database.connection
        self._cursor = self._connection.cursor()

    def get_unique_fields(self) -> List[str]:
        """Retrieve the names of fields with unique constraints in a specified table.

        Returns:
            List[str]: A set of field names that have unique constraints.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not self._table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Retrieve the list of indexes for the table
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA index_list({self._table_name})")
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

    def get_fields(self, include_many_to_many: bool = False) -> Dict[str, 'FieldInfo']:
        """Retrieve all fields of the specified table, including unique constraints and many-to-many relationships.

        Args:
            include_many_to_many (bool): Whether to include many-to-many relationship fields. Defaults to False.

        Returns:
            Dict[str, FieldInfo]: A dictionary where keys are field names and values are FieldInfo dataclass instances, 
                representing the fields in the table and their properties.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not self._table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Retrieve field information
        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA table_info({self._table_name})")
        fields = cursor.fetchall()
        cursor.close()

        # Get unique fields using the new method
        unique_fields = self.get_unique_fields()

        # Create a dictionary mapping field names to FieldInfo objects
        name_to_field_info = {field[1]: FieldInfo(*field, is_unique=(field[1] in unique_fields)) for field in fields}

        # Add foreign key information to the FieldInfo objects
        foreign_keys = self.get_foreign_keys()
        for foreign_key in foreign_keys:
            name_to_field_info[foreign_key.local_field].fk = foreign_key

        # Include many-to-many fields if requested
        if include_many_to_many:
            many_to_many_fields = self.get_many_to_many_fields()
            for field_name, m2m_field in many_to_many_fields.items():
                # Add the many-to-many field with a reference to the junction table
                name_to_field_info[field_name] = FieldInfo(
                    name=field_name,
                    type='MANY_TO_MANY',  # Use a custom type for many-to-many fields
                    m2m=m2m_field  # Store the many-to-many relationship info
                )

        return name_to_field_info

    def get_field(self, field_name: str) -> FieldInfo:
        """Get information for a specific field (column) in a table.

        Args:
            field_name (str): The name of the field to get information for.

        Returns:
            FieldInfo: The FieldInfo instance representing the field's information.

        Raises:
            ValueError: If the table or field name is invalid or the field does not exist.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not field_name.isidentifier():
            raise ValueError("Invalid table or field name")

        cursor = self._connection.cursor()

        # Try to retrieve field information for the specific field from the table's columns
        cursor.execute(
            f"SELECT * FROM pragma_table_info(?) WHERE name = ?",
            (self._table_name, field_name)
        )
        row = cursor.fetchone()

        if row is not None:
            # Field exists in the table columns
            column_id, name, data_type, not_null, default_value, primary_key = row

            # Check if the field is unique
            unique_fields = self.get_unique_fields()
            is_unique = field_name in unique_fields

            # Initialize FieldInfo
            field_info = FieldInfo(
                cid=column_id,
                name=name,
                type=data_type,
                notnull=bool(not_null),
                dflt_value=default_value,
                pk=bool(primary_key),
                is_unique=is_unique
            )

            # Retrieve foreign key information for the field
            foreign_key = self.get_foreign_key(field_name)
            if foreign_key:
                field_info.fk = foreign_key
        else:
            # Field is not in the table's columns; check if it's a many-to-many relationship
            try:
                m2m_field = self.get_many_to_many_field(field_name)
                # Initialize FieldInfo with m2m field
                field_info = FieldInfo(
                    name=field_name,
                    m2m=m2m_field
                )
            except ValueError:
                # Field is neither a column nor a many-to-many relationship
                cursor.close()
                raise ValueError(f"Field '{field_name}' does not exist in table '{self._table_name}'")

        cursor.close()
        return field_info

    def get_field_names(self, include_fk: bool = True, include_m2m: bool = False,
                        exclude_regular: bool = False) -> List[str]:
        """Retrieve the names of the fields (columns) in a specified table, with options to include or exclude foreign keys (FK) and many-to-many (M2M) fields.

        Args:
            include_fk (bool): Whether to include foreign key fields. Default is True.
            include_m2m (bool): Whether to include many-to-many fields. Default is False.
            exclude_regular (bool): Whether to exclude regular (non-FK, non-M2M) fields. Default is False.

        Returns:
            List[str]: A list of field names in the specified table.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not self._table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Retrieve all fields
        fields_info = self.get_fields()
        
        # Get many-to-many fields if needed
        m2m_fields = self.get_many_to_many_fields() if include_m2m else {}

        # Filter fields based on options
        field_names = []
        for field_name, field_info in fields_info.items():
            is_fk = field_info.is_foreign_key
            is_m2m = field_name in m2m_fields

            # Include/exclude based on provided options
            if exclude_regular and not is_fk and not is_m2m:
                continue
            if (include_fk and is_fk) or (include_m2m and is_m2m) or (not is_fk and not is_m2m):
                field_names.append(field_name)

        # Add M2M fields if included
        if include_m2m:
            field_names.extend(m2m_fields.keys())

        return field_names

    def get_field_type(self, field_name: str) -> str:
        """Retrieve the data type of a specific field in a specified table.

        Args:
            table_name (str): The name of the table.
            field_name (str): The name of the field.

        Returns:
            str: The data type of the field.
        """
        return self._database.get_field_type(self._table_name, field_name)

    def get_foreign_keys(self, table_name: str = None) -> List['ForeignKey']:
        """Retrieve foreign key constraints for the specified table.

        Args:
            table_name (str): The name of the table to retrieve foreign keys from.

        Returns:
            List[ForeignKey]: A list of `ForeignKey` instances representing the foreign keys.

        Raises:
            ValueError: If the table name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        table_name = table_name or self._table_name
        if not table_name.isidentifier():
            raise ValueError("Invalid table name")

        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
        foreign_keys = []
        for row in cursor.fetchall():
            constraint_id, sequence, referenced_table, local_field, referenced_field, on_update, on_delete, match = row
            fk_info = ForeignKey(
                constraint_id=constraint_id,
                sequence=sequence,
                local_table=table_name,
                local_field=local_field,
                referenced_table=referenced_table,
                referenced_field=referenced_field,
                on_update=on_update,
                on_delete=on_delete,
                match=match,
            )
            foreign_keys.append(fk_info)
        cursor.close()

        return foreign_keys

    def get_foreign_key(self, field_name: str) -> Optional['ForeignKey']:
        """Retrieve the foreign key constraint for a specific field in the specified table.

        Args:
            field_name (str): The name of the field to check for a foreign key constraint.

        Returns:
            Optional[ForeignKey]: A `ForeignKey` instance representing the foreign key constraint,
                or `None` if the field is not a foreign key.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not self._table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA foreign_key_list('{self._table_name}')")
        foreign_key = None
        for row in cursor.fetchall():
            constraint_id, sequence, referenced_table, local_field, referenced_field, on_update, on_delete, match = row
            if local_field == field_name:
                foreign_key = ForeignKey(
                    constraint_id=constraint_id,
                    sequence=sequence,
                    local_table=self._table_name,
                    local_field=local_field,
                    referenced_table=referenced_table,
                    referenced_field=referenced_field,
                    on_update=on_update,
                    on_delete=on_delete,
                    match=match,
                )
                break  # Assuming one foreign key per field
        cursor.close()

        return foreign_key

    def get_relationships(self) -> Dict[str, str]:
        related_table = set()
        relationships = {}

        def construct_relationships(table_name: str):
            related_table.add(table_name)
            foreign_keys = self.get_foreign_keys(table_name)

            for foreign_key in foreign_keys:
                relationships[f'{foreign_key.local_table}.{foreign_key.local_field}'] = f'{foreign_key.referenced_table}.{foreign_key.referenced_field}'
                if foreign_key.referenced_table in related_table:
                    continue
                construct_relationships(foreign_key.referenced_table)

        construct_relationships(self._table_name)
        return relationships

    def get_many_to_many_fields(self) -> Dict[str, 'ManyToManyField']:
        """Retrieve all many-to-many relationships for a specified table.

        Returns:
            Dict[str, ManyToManyField]: A dictionary where keys are `track_field_name` and values are ManyToManyField 
                instances representing the relationships.
        """
        if not self._table_name.isidentifier():
            raise ValueError("Invalid table name")

        # Return an empty dictionary if the _meta_many_to_many table does not exist
        if not self._database.is_table_exists('_meta_many_to_many'):
            return {}

        # Fetch all many-to-many relationships for the table
        cursor = self._connection.cursor()
        cursor.execute('''
            SELECT track_field_name, junction_table
            FROM _meta_many_to_many
            WHERE from_table = ?
        ''', (self._table_name,))
        
        records = cursor.fetchall()
        cursor.close()

        many_to_many_relationships = {}

        for record in records:
            track_field_name, junction_table = record

            # Retrieve foreign keys from the junction table
            foreign_keys = self.get_foreign_keys(junction_table)
            local_fk = None
            remote_fk = None

            for fk in foreign_keys:
                if fk.referenced_table == self._table_name:
                    local_fk = fk
                else:
                    remote_fk = fk

            if not local_fk or not remote_fk:
                raise ValueError(f"Foreign keys referencing '{self._table_name}' and '{remote_fk.referenced_table}' not found in '{junction_table}'.")

            # Create the ManyToManyField instance
            many_to_many_field = ManyToManyField(
                track_field_name=track_field_name,
                local_table=self._table_name,
                remote_table=remote_fk.referenced_table,
                junction_table=junction_table,
                local_fk=local_fk,
                remote_fk=remote_fk
            )

            # Use track_field_name as the key in the dictionary
            many_to_many_relationships[track_field_name] = many_to_many_field

        return many_to_many_relationships

    def get_many_to_many_field(self, field_name: str) -> 'ManyToManyField':
        """Retrieve a specific many-to-many relationship for a specified table and field.

        Args:
            table_name (str): The name of the table to retrieve the many-to-many relationship for.
            field_name (str): The name of the field representing the many-to-many relationship.

        Returns:
            ManyToManyField: An instance representing the many-to-many relationship.

        Raises:
            ValueError: If the field does not represent a many-to-many relationship.
        """
        if not self._table_name.isidentifier() or not field_name.isidentifier():
            raise ValueError("Invalid field name")

        # Check if the _meta_many_to_many table exists
        if not self._database.is_table_exists('_meta_many_to_many'):
            return

        # Fetch the specific many-to-many relationship
        cursor = self._connection.cursor()
        cursor.execute('''
            SELECT track_field_name, junction_table
            FROM _meta_many_to_many
            WHERE from_table = ? AND track_field_name = ?
        ''', (self._table_name, field_name))

        record = cursor.fetchone()
        cursor.close()

        if not record:
            raise ValueError(f"No many-to-many relationship found for field '{field_name}' in table '{self._table_name}'.")

        track_field_name, junction_table = record

        # Retrieve foreign keys from the junction table
        foreign_keys = self.get_foreign_keys(junction_table)
        local_fk = None
        remote_fk = None

        for fk in foreign_keys:
            if fk.referenced_table == self._table_name:
                local_fk = fk  # Foreign key referencing the local table
            else:
                remote_fk = fk  # Foreign key referencing the remote table
                remote_table = remote_fk.referenced_table

        if not local_fk or not remote_fk:
            raise ValueError(f"Foreign keys referencing '{self._table_name}' and '{remote_table}' not found in '{junction_table}'.")

        # Create the ManyToManyField instance
        many_to_many_field = ManyToManyField(
            track_field_name=track_field_name,
            local_table=self._table_name,
            remote_table=remote_table,
            junction_table=junction_table,
            local_fk=local_fk,
            remote_fk=remote_fk
        )

        return many_to_many_field

    def get_many_to_many_field_names(self) -> List[str]:
        """Retrieve the track field names of all many-to-many relationships for the current table.

        Returns:
            List[str]: A list of track field names representing many-to-many relationships in the current table.
        """
        return list(self.get_many_to_many_fields().keys())

    def get_primary_keys(self) -> List[str]:
        """Retrieve the primary keys of a specified table.
        
        Args:
            table_name (str): The name of the table to retrieve primary keys from.

        Returns:
            List[str]: A list of primary key field names. If it's a composite key, multiple fields are returned.
        """
        if not self._table_name.isidentifier():
            raise ValueError("Invalid table name")

        cursor = self._connection.cursor()
        cursor.execute(f"PRAGMA table_info({self._table_name})")
        fields = cursor.fetchall()
        cursor.close()

        # Filter fields to include only those that are part of the primary key
        primary_keys = [field[1] for field in fields if field[5]]
        return primary_keys

    def get_many_to_many_data(self, track_field_name: str, from_values: Optional[List[Union[int, str, float]]] = None,
                              display_field: str = '', display_field_label: str = '') -> List[Dict[str, Union[int, str, float]]]:
        """Retrieve the display field data related to specific records in a many-to-many relationship.

        Args:
            table_name (str): The name of the table from which the relationship starts.
            track_field_name (str): The field name that tracks the many-to-many relationship.
            from_values (Optional[List[Union[int, str, float]]]): A list of values in the from_table to match. If None, retrieve for all.
            display_field (str): The name of the display field in the related table to retrieve.

        Returns:
            List[Dict[str, Union[int, str, float]]]: A list of dictionaries, each containing the 'id' from the original table and the corresponding list of related tags or other display fields.
        """
        cursor = self._connection.cursor()

        m2m = self.get_many_to_many_field(track_field_name)

        # Determine the display field and its type
        display_field = display_field or m2m.remote_fk.referenced_field
        display_field_type = self._database.get_field_type(m2m.remote_table, display_field)

        # Retrieve all values if not specified
        if from_values is None:
            cursor.execute(f'''
                SELECT DISTINCT {m2m.local_fk.local_field}
                FROM {m2m.junction_table}
            ''')
            from_values = [row[0] for row in cursor.fetchall()]

        key_type = self.get_field_type(m2m.local_fk.referenced_field)

        # Prepare the SQL query
        placeholders = ', '.join('?' for _ in from_values)
        query = f'''
            SELECT CAST({m2m.junction_table}.{m2m.local_fk.local_field} AS {key_type}) AS {m2m.local_fk.referenced_field},
                GROUP_CONCAT({m2m.remote_table}.{display_field}) AS {track_field_name}
            FROM {m2m.junction_table}
            JOIN {m2m.remote_table} ON {m2m.junction_table}.{m2m.remote_fk.local_field} = {m2m.remote_table}.{m2m.remote_fk.referenced_field}
            WHERE {m2m.junction_table}.{m2m.local_fk.local_field} IN ({placeholders})
            GROUP BY {m2m.junction_table}.{m2m.local_fk.local_field}
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

        display_field_label = display_field_label or track_field_name
        # Return data with proper formatting
        return [
            {
                m2m.local_fk.referenced_field: row[0],
                display_field_label: [convert_value(val, display_field_type) for val in row[1].split(',')]
            }
            for row in results
        ]

    def query(self, fields: Optional[List[str]] = None, conditions: Optional[str] = None,
              values: Optional[List[Any]] = None, as_dict: bool = False, handle_m2m: bool = False,
              order_by: Optional[Dict[str, 'SortOrder']] = None, relationships=None
              ) -> Union[Generator[Tuple, None, None], Generator[Dict[str, Union[int, str, float, None]], None, None]]:
        """Retrieve data from a specified table as a generator.

        Args:
            fields (Optional[List[str]]): Specific fields to retrieve. Defaults to all fields.
            conditions (Optional[str]): Optional SQL WHERE clause to filter results. Defaults to None.
            values (Optional[List[Any]]): Parameters to substitute into the SQL query, preventing SQL injection. Defaults to None.
            as_dict (bool): If True, yield rows as dictionaries. Defaults to False.
            handle_m2m (bool): Whether to retrieve many-to-many related data as well. Defaults to False.
            order_by (Optional[List[Tuple[str, str]]]): A list of tuples specifying fields and sort direction ("ASC" or "DESC"). Defaults to None.

        Yields:
            Union[Tuple[Any, ...], Dict[str, Any]]: Each row from the query result.
                - If `as_dict` is False (default), yields a tuple of field values.
                - If `as_dict` is True, yields a dictionary mapping field names to their values.

        Raises:
            ValueError: If the table name, field names, or order_by fields are invalid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        fields = fields or self.field_names
        if relationships:
            relationships = self.get_relationships() | relationships
        else:
            relationships = self.get_relationships()

        many_to_many_field_names = self.get_many_to_many_field_names() if handle_m2m else []
        fields = [field for field in fields if field not in many_to_many_field_names]

        query, values, grouped_field_aliases = SQLQueryBuilder.build_query(
            model=self._table_name,
            fields=fields,
            conditions=conditions,
            relationships=relationships,
            order_by=order_by,
            values=values
        )

        cursor = self._connection.cursor()
        try:
            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)

            if handle_m2m:
                for row in cursor:
                    row_dict = dict(row)
                    for m2m_field in many_to_many_field_names:
                        m2m_data = self.get_many_to_many_data(m2m_field, [row_dict[self.get_primary_keys()[0]]])
                        if not m2m_data:
                            continue
                        row_dict[m2m_field] = m2m_data[0].get(m2m_field, [])

                    if as_dict:
                        yield row_dict
                    else:
                        yield tuple(row_dict.values())

            else:
                if as_dict:
                    yield from map(dict, cursor)
                else:
                    yield from map(tuple, cursor)

        finally:
            cursor.close()

    def query_one(self, fields=None, conditions=None, relationships=None, values=None, order_by=None, as_dict=True):
        return next(self.query(fields=fields, conditions=conditions, relationships=relationships, values=values, order_by=order_by, as_dict=as_dict), None)

    def add_field(self, field_name: str, field_definition: str, foreign_key: Optional[str] = None, enum_values: Optional[List[str]] = None, enum_table_name: Optional[str] = None):
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
        if not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # Handle enum values or existing enum table
        if enum_values or enum_table_name:
            if not enum_table_name:
                enum_table_name = f"enum_{field_name}"
                self.create_enum_table(enum_table_name, enum_values)

            field_definition = "TEXT"
            foreign_key = f"{enum_table_name}(id)"
            self._add_enum_metadata(field_name, enum_table_name)

        # Fetch existing fields and foreign keys
        fields = self.get_fields()
        foreign_keys = self.get_foreign_keys()

        # Create a new table schema with the new field
        new_fields = [field.get_field_definition() for field in fields.values()]

        # Add the new field definition
        new_fields.append(f"{field_name} {field_definition}")

        # Include existing foreign keys
        new_fields.extend(fk.get_field_definition() for fk in foreign_keys)

        # Add the new foreign key constraint if provided
        if foreign_key:
            new_fields.append(f"FOREIGN KEY({field_name}) REFERENCES {foreign_key}")

        new_fields_str = ', '.join(new_fields)

        temp_table_name = f"{self._table_name}_temp"
        self._cursor.execute(f"CREATE TABLE {temp_table_name} ({new_fields_str})")

        # Copy data from the old table to the new table
        old_fields_str = ', '.join(fields.keys())
        self._cursor.execute(f"INSERT INTO {temp_table_name} ({old_fields_str}) SELECT {old_fields_str} FROM {self._table_name}")

        # Drop the old table and rename the new table
        self._cursor.execute(f"DROP TABLE {self._table_name}")
        self._cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {self._table_name}")

        self._connection.commit()

    def delete_field(self, field_name: str):
        """Delete a field from a table by recreating the table without that field.

        Args:
            table_name (str): The name of the table to delete the field from.
            field_name (str): The name of the field to delete.

        Raises:
            ValueError: If the table name or field name is not a valid Python identifier.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not field_name.isidentifier():
            raise ValueError("Invalid table name or field name")

        # Retrieve the table information
        fields = self.get_fields(self._table_name)

        # Disable foreign key constraints temporarily
        self._cursor.execute("PRAGMA foreign_keys=off;")
        try:
            # Filter out the field to be deleted
            new_fields = [field for field in fields.values() if field.name != field_name]
            field_names_str = ', '.join([field.name for field in new_fields])

            # Retrieve and filter foreign key constraints
            field_definitions = [field.get_field_definition() for field in new_fields]
            foreign_keys = self.get_foreign_keys()
            field_definitions.extend([fk.get_field_definition() for fk in foreign_keys if fk.from_field != field_name])
            field_definitions_str = ', '.join(field_definitions)

            # Create a temporary table with the new schema
            temp_table_name = f"{self._table_name}_temp"
            self._cursor.execute(f"CREATE TABLE {temp_table_name} ({field_definitions_str})")
            self._cursor.execute(f"INSERT INTO {temp_table_name} ({field_names_str}) SELECT {field_names_str} FROM {self._table_name}")
            # Replace the old table with the new one
            self._cursor.execute(f"DROP TABLE {self._table_name}")
            self._cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {self._table_name}")

            # Remove the display field metadata
            self._remove_display_field(field_name)

            # Commit the transaction
            self._connection.commit()

        except sqlite3.Error as e:
            logging.error(f"Error deleting field '{field_name}' from table '{self._table_name}': {e}")
            self._connection.rollback()
            raise

        finally:
            # Re-enable foreign key constraints
            self._cursor.execute("PRAGMA foreign_keys=on;")

    def insert_record(self, data_dict: Dict[str, Union[int, str, float, None]],
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
        if not all(f.isidentifier() for f in data_dict.keys()):
            raise ValueError("Invalid table name or field names")

        # Separate M2M data from the main data if handling M2M relationships
        m2m_data = {}
        if handle_m2m:
            for track_field_name in self.get_many_to_many_field_names():
                if track_field_name not in data_dict:
                    continue
                m2m_data[track_field_name] = data_dict.pop(track_field_name)

        # Insert the main record
        field_names = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?'] * len(data_dict))
        sql = f"INSERT INTO {self._table_name} ({field_names}) VALUES ({placeholders})"
        self._cursor.execute(sql, list(data_dict.values()))
        self._connection.commit()

        # Get the primary key of the newly inserted record
        rowid = self._cursor.lastrowid

        # Insert M2M data into the junction table(s) if handling M2M relationships
        if handle_m2m:
            for track_field_name, selected_values in m2m_data.items():
                self._update_junction_table(track_field_name, rowid, selected_values, is_rowid=True)

        return rowid
    
    def delete_record(self, pk_values: Union[Dict[str, Any], Any], pk_field: Optional[str] = None):
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
        m2m_fields = self.get_many_to_many_fields()
        for m2m_field in m2m_fields.values():
            junction_table = m2m_field.junction_table

            # Delete related entries in the junction table
            self._cursor.execute(f'''
                DELETE FROM {junction_table}
                WHERE {m2m_field.local_fk.local_field} = ?
            ''', (list(pk_values.values())[0],))

        # Then, delete the main record from the table
        query = f"DELETE FROM {self._table_name} WHERE {where_clause}"
        self._cursor.execute(query, where_values)
        self._connection.commit()

    # TODO: Handle composite pks
    def update_record(self, data_dict: Dict[str, Union[int, str, float, None]], 
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
        if (not all(f.isidentifier() for f in data_dict.keys()) or
            not pk_field.isidentifier()
        ):
            raise ValueError("Invalid table name or field names")

        # Separate M2M data from the main data if handling M2M relationships
        m2m_data = {}
        if handle_m2m:
            for track_field_name in self.get_many_to_many_field_names():
                if track_field_name not in data_dict:
                    continue
                m2m_data[track_field_name] = data_dict.pop(track_field_name)

        if data_dict:
            # Update the main record
            set_clause = ', '.join([f"{field} = ?" for field in data_dict.keys()])
            sql = f"UPDATE {self._table_name} SET {set_clause} WHERE {pk_field} = ?"
            self._cursor.execute(sql, list(data_dict.values()) + [pk_value])
            self._connection.commit()

        # Update M2M data in the junction table(s) if handling M2M relationships
        if handle_m2m:
            for track_field_name, selected_values in m2m_data.items():
                self._update_junction_table(track_field_name, pk_value, selected_values)

    def fetch_one(self, field_name: str, reference_field_name: str, reference_value: Union[int, str, float]) -> Optional[Union[int, str, float]]:
        """Retrieve a value from a related table based on a foreign key.

        Args:
            field_name (str): The specific field in the related table to retrieve.
            reference_field_name (str): The field in the related table that corresponds to the foreign key.
            reference_value (Union[int, str, float]): The foreign key value from the source table.

        Returns:
            Optional[Union[int, str, float]]: The value from the specified field in the related table, or None if no match is found.

        Raises:
            ValueError: If any of the table or field names are not valid Python identifiers.
            sqlite3.Error: If there is an error executing the SQL command.
        """
        if not all(map(str.isidentifier, [field_name, reference_field_name])):
            raise ValueError("Invalid table name or field names")

        # Use the fetch_one method to retrieve the related row
        query = f"SELECT {field_name} FROM {self._table_name} WHERE {reference_field_name} = ? LIMIT 1"
        self._cursor.execute(query, (reference_value,))

        if not (results := self._cursor.fetchone()):
            return

        return results[0]

    def get_possible_values(self, field: Optional[str] = None) -> List[str]:
        """Get possible values from a related table using a display field.

        Args:
            table_name (str): The name of the related table.
            field (Optional[str]): The field to display. Defaults to the primary key.

        Returns:
            List[str]: A list of possible values from the specified display field.
        """
        # Determine the display field: use the provided display field or default to the primary key
        field = field or self.get_primary_keys()[0]

        # Ensure the display field exists in the table
        if field not in self.get_field_names():
            raise ValueError(f"Field '{field}' does not exist in table '{self._table_name}'")

        # Execute query to get the unique values for the display field
        self._cursor.execute(f"SELECT DISTINCT {field} FROM {self._table_name} ORDER BY {field}")
        return [row[0] for row in self._cursor.fetchall()]

    def add_display_field(self, field_name: str, display_field_name: str, display_format: str = None):
        """Add a display field entry to the meta table.
        """
        self._create_meta_display_field_table()
        self._cursor.execute('''
            INSERT OR REPLACE INTO _meta_display_field (table_name, field_name, display_foreign_field_name, display_format)
            VALUES (?, ?, ?, ?);
        ''', (self._table_name, field_name, display_field_name, display_format))
        self._connection.commit()

    def get_display_field(self, field_name: str) -> Optional[Tuple[str, str]]:
        """Retrieve the display field name and format for a specific field.
        """
        try:
            self._cursor.execute('''
                SELECT display_foreign_field_name, display_format
                FROM _meta_display_field
                WHERE table_name = ? AND field_name = ?;
            ''', (self._table_name, field_name))
        except sqlite3.OperationalError:
            pass

        if not (results := self._cursor.fetchone()):
            return

        return results[0]

    # Private Methods
    # ---------------
    def _create_meta_enum_field_table(self):
        """Create the meta table to store enum field information.
        """
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS _meta_enum_field (
                table_name TEXT,
                field_name TEXT,
                enum_table_name TEXT,
                description TEXT,
                PRIMARY KEY (table_name, field_name)
            );
        ''')
        self._connection.commit()

    def _update_junction_table(self, track_field_name: str, from_value: Union[int, str, float], 
                            selected_values: List[Union[int, str, float]], is_rowid: bool = False):
        """Update the junction table for a many-to-many relationship.

        Args:
            track_field_name (str): The field name that tracks the many-to-many relationship.
            from_value (Union[int, str, float]): The value in the from_table to match, either a rowid or an existing key.
            selected_values (List[Union[int, str, float]]): The list of values to insert into the junction table.
            is_rowid (bool): Indicates if `from_value` is a rowid that needs to be translated into the corresponding foreign key value.
        """
        m2m = self.get_many_to_many_field(track_field_name)

        if is_rowid:
            # Translate the rowid into the corresponding foreign key value
            self._cursor.execute(f'''
                SELECT {m2m.local_fk.referenced_field}
                FROM {self._table_name}
                WHERE rowid = ?
            ''', (from_value,))
            from_value = self._cursor.fetchone()[0]

        # Clear existing junction table entries for this record
        self._cursor.execute(f'''
            DELETE FROM {m2m.junction_table}
            WHERE {m2m.local_fk.local_field} = ?
        ''', (from_value,))

        # Insert new entries into the junction table
        for value in selected_values:
            self._cursor.execute(f'''
                INSERT INTO {m2m.junction_table} ({m2m.local_fk.local_field}, {m2m.remote_fk.local_field})
                VALUES (?, ?)
            ''', (from_value, value))
        
        self._connection.commit()

    def _add_enum_metadata(self, table_name: str, field_name: str, enum_table_name: str, description: str = ""):
        self._create_meta_enum_field_table()
        self._cursor.execute('''
            INSERT INTO _meta_enum_field (table_name, field_name, enum_table_name, description)
            VALUES (?, ?, ?, ?);
        ''', (table_name, field_name, enum_table_name, description))
        self._connection.commit()

    def _remove_display_field(self, field_name: str):
        """Remove a display field entry from the meta table.
        """
        try:
            self._cursor.execute('''
                DELETE FROM _meta_display_field
                WHERE table_name = ? AND field_name = ?;
            ''', (self._table_name, field_name))
            self._connection.commit()
        except sqlite3.OperationalError:
            pass

    def _create_meta_display_field_table(self):
        """Create the meta table to store display field information.
        """
        fields = {
            'table_name': 'TEXT',
            'field_name': 'TEXT',
            'display_foreign_field_name': 'TEXT',
            'display_format': 'TEXT',
            'PRIMARY KEY': '(table_name, field_name)'
        }
        self._database.create_table('_meta_display_field', fields)


class Entity:

    def __init__(self, database: SQLiteDatabase, table_name: str, entity_id: Any):
        self._database = database
        self._table_name = table_name
        self._id = entity_id

        self._model = self._database.get_model(self._table_name)
        self._cursor = self._database.cursor
    
    @property
    def database(self):
        return self._database
    
    @property
    def model(self):
        return self._model
    
    @property
    def table_name(self):
        return self._table_name
    
    @property
    def id(self):
        return self._id
    
    def get_field_names(self) -> List[str]:
        return self._model.get_field_names()
    
    def get(self, fields: List[str] | str = None, as_dict: bool = True):
        return self._model.query_one(
            fields=fields,
            conditions={'rowids': self._id},
            as_dict=as_dict
        )
    
    def __getitem__(self, fields):
        return self.get(fields, as_dict=False)
