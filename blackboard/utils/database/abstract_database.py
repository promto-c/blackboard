
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

    CHAIN_SEPARATOR = '.'

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

    @staticmethod
    def resolve_model_chain(base_model: str, relation_chain: str, relationships: Dict[str, str], sep: str = CHAIN_SEPARATOR) -> str:
        """Resolve a chain of relationships to determine the final model.

        Starting from a base model, this method iteratively follows the relationship chain defined by
        the `relation_chain` string. At each step, it uses the `relationships` dictionary to map the current
        model and field (formatted as "Model{sep}field") to a new model. If the chain is invalid or incomplete,
        the function returns None.

        Args:
            base_model (str): The initial model from which to start the resolution.
            relation_chain (str): A separator-delimited string representing the chain of relationships (e.g., "name.account").
            relationships (Dict[str, str]): A dictionary mapping "Model{sep}field" to "RelatedModel{sep}related_field".
            sep (str, optional): The separator used in both the relationship chain and the dictionary keys.
                 Defaults to CHAIN_SEPARATOR.

        Returns:
            str: The final model reached after resolving the relationship chain. Returns None if the chain cannot be fully resolved.

        Examples:
            >>> relationships = {
            ...     'User.name': 'Profile.id',
            ...     'Profile.account': 'Account.id'
            ... }
            >>> AbstractDatabase.resolve_model_chain('User', 'name.account', relationships, sep='.')
            'Account'
            >>> AbstractDatabase.resolve_model_chain('User', 'name', relationships, sep='.')
            'Profile'
        """
        for field in relation_chain.split(sep):
            if (left_model_field := f'{base_model}{sep}{field}') not in relationships:
                return
            base_model, _right_field = relationships[left_model_field].split(sep)

        return base_model


class AbstractModel(ABC):
    """Abstract base class for all models that interact with a database.
    Defines the core methods that any concrete model should implement.
    """

    def __init__(self, database: 'AbstractDatabase', model_name: str):
        """Initialize the model with a reference to the database manager and table name.

        Args:
            database (AbstractDatabaseManager): The database manager instance.
            model_name (str): The name of the table associated with the model.
        """
        self._database = database
        self._name = model_name

    def get_field_type(self, field_chain: str):
        return self._database.get_field_type(self._name, field_chain)

    def resolve_model_chain(self, relation_chain: str, relationships: Dict[str, str] = None) -> str:
        relationships = relationships or {}
        return self._database.resolve_model_chain(self._name, relation_chain, self.get_relationships() | relationships)

    @property
    def name(self) -> str:
        return self._name

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
    def query(self, fields: Optional[List[str]] = None, conditions: Optional[str] = None, values: Optional[List] = None,
              as_dict: bool = False, handle_m2m: bool = False,
              ) -> Union[Generator[Tuple, None, None], Generator[Dict[str, Any], None, None]]:
        """Perform a query on the table."""
        pass

    @abstractmethod
    def get_relationships(self) -> Dict[str, str]:
        """Get a dictionary of relationships"""
        pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
