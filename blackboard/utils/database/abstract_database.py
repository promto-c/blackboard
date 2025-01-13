
# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, Generator, List, Tuple, Union, Optional, Dict, Any
if TYPE_CHECKING:
    from .schema import FieldInfo
# Standard Library Imports
# ------------------------
from abc import ABC, abstractmethod


# Class Definitions
# -----------------
class AbstractDatabase(ABC):

    @abstractmethod
    def create_table(self, table_name: str, fields: Dict[str, str]) -> 'AbstractModel':
        """Create a table in the database."""
        pass

    @abstractmethod
    def delete_table(self, table_name: str):
        """Delete a table from the database."""
        pass

    @abstractmethod
    def is_table_exists(self, table_name: str):
        pass

    @abstractmethod
    def get_table_names(self) -> List[str]:
        """Retrieve the names of all tables in the database.

        Returns:
            List[str]: A list of table names present in the database.
        """
        pass

    @abstractmethod
    def get_view_names(self) -> List[str]:
        """Retrieve the names of all views in the database.

        Returns:
            List[str]: A list of view names present in the database.
        """
        pass

    @abstractmethod
    def get_field_type(self, table_name: str, field_name: str) -> str:
        """Retrieve the data type of a specific field in a specified table.

        Args:
            table_name (str): The name of the table.
            field_name (str): The name of the field.

        Returns:
            str: The data type of the field.
        """
        pass

    @abstractmethod
    def get_model(self, table_name: str) -> 'AbstractModel':
        """Get a model instance for the specified table.

        Args:
            table_name (str): The name of the table.

        Returns:
            AbstractModel: An instance of AbstractModel representing the table.
        """
        return AbstractModel(self, table_name)

    @abstractmethod
    def close(self):
        """Close the database connection."""
        pass

class AbstractModel(ABC):
    """Abstract base class for all models that interact with a database.
    Defines the core methods that any concrete model should implement.
    """

    def __init__(self, db_manager: 'AbstractDatabase', table_name: str):
        """Initialize the model with a reference to the database manager and table name.

        Args:
            db_manager (AbstractDatabaseManager): The database manager instance.
            table_name (str): The name of the table associated with the model.
        """
        self._db_manager = db_manager
        self._table_name = table_name

    def get_field_type(self, field_name: str):
        return self._db_manager.get_field_type(self._table_name, field_name)

    @property
    def name(self) -> str:
        return self._table_name

    @property
    def field_names(self) -> List[str]:
        return self.get_field_names()

    @abstractmethod
    def add_field(self, field_name: str, field_definition: str, foreign_key: Optional[str] = None, enum_values: Optional[List[str]] = None, enum_table_name: Optional[str] = None):
        """Add a new field to an existing table, optionally with a foreign key or enum constraint."""
        pass

    @abstractmethod
    def delete_field(self, field_name: str):
        """Delete a field from a table."""
        pass

    @abstractmethod
    def get_fields(self) -> Dict[str, 'FieldInfo']:
        """Retrieve all fields in the table."""
        pass

    @abstractmethod
    def get_field(self, field_name: str) -> 'FieldInfo':
        """Retrieve a specific field's details."""
        pass

    @abstractmethod
    def get_field_names(self, include_fk: bool = True, include_m2m: bool = False, exclude_regular: bool = False) -> List[str]:
        """Retrieve a list of field names, with options to filter foreign keys or many-to-many fields."""
        pass

    @abstractmethod
    def get_primary_keys(self) -> List[str]:
        """Retrieve a list of primary keys for the table."""
        pass

    @abstractmethod
    def insert_record(self, data_dict: Dict[str, Union[int, str, float, None]], handle_m2m: bool = False) -> int:
        """Insert a new record into the database and return its ID."""
        pass

    @abstractmethod
    def update_record(self, data_dict: Dict[str, Union[int, str, float, None]], pk_value: Union[int, str, float], pk_field: str = 'rowid', handle_m2m: bool = False):
        """Update an existing record in the database."""
        pass

    @abstractmethod
    def delete_record(self, pk_values: Union[Dict[str, Union[int, str, float]], Union[int, str, float]], pk_field: Optional[str] = None):
        """Delete a record from the database."""
        pass

    @abstractmethod
    def get_unique_fields(self) -> List[str]:
        """Get a list of unique fields in the table."""
        pass

    @abstractmethod
    def query(self, fields: Optional[List[str]] = None, where_clause: Optional[str] = None, parameters: Optional[List] = None,
              as_dict: bool = False, handle_m2m: bool = False,
              ) -> Union[Generator[Tuple, None, None], Generator[Dict[str, Any], None, None]]:
        """Perform a query on the table."""
        pass
