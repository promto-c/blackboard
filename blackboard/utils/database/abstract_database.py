
# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, Generator, List, Tuple, Union, Optional, Dict, Any
if TYPE_CHECKING:
    from blackboard.utils.database.schema import FieldInfo, ForeignKey
    from blackboard.enums.view_enum import GroupOperator, SortOrder

# Standard Library Imports
# ------------------------
from abc import ABC, abstractmethod
import json

# Local Imports
# -------------
from blackboard.utils.database.sql_query_builder import SQLQueryBuilder


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

    def execute_raw(self, query: str, parameters: Optional[List[Any]] = None) -> int:
        """Execute a raw SQL query that modifies data (INSERT, UPDATE, DELETE)."""
        cursor = self._connection.cursor()
        try:
            cursor.execute(query, parameters)
            self._connection.commit()
            return cursor.rowcount
        finally:
            cursor.close()

    def query_raw(self, query: str, parameters: Optional[List[Any]] = None, as_dict: bool = True, is_single_field_query: bool = False):
        """Execute a raw SQL query and yield results as dictionaries or tuples.

        Args:
            query (str): The SQL query to execute.
            parameters (Optional[List[Any]]): A list of parameters to bind to the query.
                If None, the query is executed without parameters.
            as_dict (bool): If True, each row is returned as a dictionary mapping column names
                to values. If False, each row is returned as a tuple.

        Yields:
            Union[Dict[str, Any], Tuple[Any, ...]]: Each row from the query result.
        """
        cursor = self._connection.cursor()
        if parameters:
            cursor.execute(query, parameters)
        else:
            cursor.execute(query)

        try:
            if as_dict:
                yield from map(dict, cursor)
            elif is_single_field_query:
                yield from map(lambda x: x[0], cursor)
            else:
                yield from map(tuple, cursor)
        finally:
            cursor.close()

    def query_raw_one(self, query: str, parameters: Optional[List[Any]] = None, as_dict: bool = True) -> Optional[Union[Dict[str, Any], Tuple[Any, ...]]]:
        """Execute a raw SQL query and return the first result as a dictionary or tuple.

        Args:
            query (str): The SQL query to execute.
            parameters (Optional[List[Any]]): A list of parameters to bind to the query.
                If None, the query is executed without parameters.
            as_dict (bool): If True, the row is returned as a dictionary mapping column names
                to values. If False, the row is returned as a tuple.

        Returns:
            Optional[Union[Dict[str, Any], Tuple[Any, ...]]]: The first row from the query result
                or None if no row is found.
        """
        return next(self.query_raw(query, parameters, as_dict), None) 

    def query(self, model_name: str, fields: Optional[List[str]] = None, 
              conditions: Optional[Dict[Union['GroupOperator', str], Any]] = None,
              relationships: Dict[str, str] = None, order_by: Optional[Dict[str, 'SortOrder']] = None, 
              limit: Optional[int] = None, as_dict: bool = True,
              ) -> Generator[Tuple[Any, ...] | Dict[str, Any], None, None]:
        """Retrieve data from a specified table as a generator.

        Args:
            fields (Optional[List[str]]): Specific fields to retrieve. Defaults to all fields.
            conditions (Optional[Dict[Union[GroupOperator, str], Any]]): SQL WHERE clause conditions.
            relationships (Optional[Dict[str, str]]): Relationship mappings.
            order_by (Optional[Dict[str, SortOrder]]): Fields and sort order.
            limit (Optional[int]): Maximum number of rows to retrieve.
            as_dict (bool): If True, yield rows as dictionaries; if False, as tuples.

        Yields:
            Tuple[Any, ...] | Dict[str, Any]: Each row from the query result.
        """
        is_single_field_query = isinstance(fields, str)
        if is_single_field_query:
            fields = [fields]

        # Merge provided relationships with default relationships.
        if relationships:
            relationships = self.get_relationships(model_name) | relationships
        else:
            relationships = self.get_relationships(model_name)

        query, parameters, grouped_field_aliases = SQLQueryBuilder.build_query(
            model=model_name,
            fields=fields,
            conditions=conditions,
            relationships=relationships,
            order_by=order_by,
            limit=limit,
        )

        # No grouped (JSON) fields present: yield raw results.
        if not grouped_field_aliases:
            yield from self.query_raw(query, parameters, as_dict, is_single_field_query)
        # Grouped fields are present.
        elif as_dict:
            yield from (
                {
                    field: json.loads(value) if field in grouped_field_aliases else value
                    for field, value in row.items()
                }
                for row in self.query_raw(query, parameters, as_dict=True)
            )
        else:
            yield from (
                tuple(
                    json.loads(value) if field in grouped_field_aliases else value
                    for field, value in row.items()
                )
                for row in self.query_raw(query, parameters, as_dict=True)
            )

    def query_one(
        self,
        model_name: str,
        fields: Optional[List[str]] = None,
        conditions: Optional[Dict[Union['GroupOperator', str], Any]] = None,
        relationships: Optional[Dict[str, str]] = None,
        order_by: Optional[Dict[str, 'SortOrder']] = None,
        as_dict: bool = True,
    ) -> Optional[Union[Dict[str, Any], Tuple[Any, ...]]]:
        """Retrieve a single row from a specified table.

        This method internally calls `query` with a limit of 1 and returns the first
        row from the result generator. If no rows are found, it returns None.

        Args:
            model_name (str): Name of the model/table to query.
            fields (Optional[List[str]]): Specific fields to retrieve. Defaults to all fields.
            conditions (Optional[Dict[Union[GroupOperator, str], Any]]): SQL WHERE clause conditions.
            relationships (Optional[Dict[str, str]]): Relationship mappings.
            order_by (Optional[Dict[str, 'SortOrder']]): Fields and sort order.
            as_dict (bool): If True, the row is returned as a dictionary; if False, as a tuple.

        Returns:
            Optional[Union[Dict[str, Any], Tuple[Any, ...]]]: The first row from the query result
                or None if no row is found.
        """
        # Force limit to 1 when retrieving a single row.
        result_generator = self.query(
            model_name=model_name,
            fields=fields,
            conditions=conditions,
            relationships=relationships,
            order_by=order_by,
            limit=1,
            as_dict=as_dict,
        )
        return next(result_generator, None)

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

    def get_foreign_keys(self, model_name: str) -> Generator['ForeignKey', None, None]:
        """Retrieve foreign key constraints for the specified table.

        Args:
            model_name (str): The name of the table from which to retrieve foreign keys.

        Yields:
            ForeignKey: Each foreign key constraint as a `ForeignKey` instance.
        
        Raises:
            ValueError: If the table name is not a valid Python identifier.
        """
        if not model_name or not model_name.isidentifier():
            raise ValueError("Invalid model name")

        # Convert each row (sqlite3.Row) to a dictionary, then create a ForeignKey instance.
        yield from (
            ForeignKey.from_dict(row, local_table=model_name)
            for row in self.query_raw(...)
        )

    def get_foreign_key(self, model_name: str, field_name: str) -> Optional['ForeignKey']:
        """Retrieve the foreign key constraint for the specified field in a given table.

        Args:
            model_name (str): The name of the table.
            field_name (str): The field name in the table that acts as the foreign key.

        Returns:
            Optional[ForeignKey]: The `ForeignKey` instance if found; otherwise, None.
        """
        # Return the foreign key with a matching local field.
        for fk in self.get_foreign_keys(model_name):
            if fk.local_field != field_name:
                continue
            return fk
        return

    def get_relationships(self, model_name: str) -> Dict[str, str]:
        related_table = set()
        relationships = {}

        def construct_relationships(model_name: str):
            if model_name in related_table:
                return
            related_table.add(model_name)

            for foreign_key in self.get_foreign_keys(model_name):
                relationships[f'{foreign_key.local_table}.{foreign_key.local_field}'] = f'{foreign_key.related_table}.{foreign_key.related_field}'
                if foreign_key.related_table in related_table:
                    continue
                construct_relationships(foreign_key.related_table)

        construct_relationships(model_name)

        return relationships


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

    def query(self, fields: Optional[List[str]] = None, 
              conditions: Optional[Dict[Union['GroupOperator', str], Any]] = None,
              relationships: Dict[str, str] = None, order_by: Optional[Dict[str, 'SortOrder']] = None, 
              limit: Optional[int] = None, as_dict: bool = True,
              ) -> Generator[Tuple[Any, ...] | Dict[str, Any], None, None]:
        """Retrieve data from a specified table as a generator.

        Args:
            fields (Optional[List[str]]): Specific fields to retrieve. Defaults to all fields.
            conditions (Optional[Dict[Union[GroupOperator, str], Any]]): SQL WHERE clause conditions.
            relationships (Optional[Dict[str, str]]): Relationship mappings.
            order_by (Optional[Dict[str, SortOrder]]): Fields and sort order.
            limit (Optional[int]): Maximum number of rows to retrieve.
            as_dict (bool): If True, yield rows as dictionaries; if False, as tuples.

        Yields:
            Tuple[Any, ...] | Dict[str, Any]: Each row from the query result.
        """
        yield from self._database.query(
            model_name=self._name, fields=fields, conditions=conditions, relationships=relationships,
            order_by=order_by, limit=limit, as_dict=as_dict
        )

    def query_one(self, fields=None, conditions=None, relationships=None, values=None, order_by=None, as_dict=True):
        return next(self.query(fields=fields, conditions=conditions, relationships=relationships, values=values, order_by=order_by, as_dict=as_dict), None)

    def resolve_model_chain(self, relation_chain: str, relationships: Dict[str, str] = None) -> str:
        relationships = relationships or {}
        return self._database.resolve_model_chain(self._name, relation_chain, self.get_relationships() | relationships)

    @property
    def name(self) -> str:
        return self._name

    @property
    def field_names(self) -> List[str]:
        return self.get_field_names()

    def get_foreign_keys(self) -> Generator['ForeignKey', None, None]:
        """Retrieve foreign key constraints for the specified table.

        Returns:
            List[ForeignKey]: A list of `ForeignKey` instances representing the foreign keys.
        """
        yield from self._database.get_foreign_keys(self.name)

    def get_foreign_key(self, field_name: str) -> Optional['ForeignKey']:
        """Retrieve the foreign key constraint for a specific field in the specified table.

        Args:
            field_name (str): The name of the field to check for a foreign key constraint.

        Returns:
            Optional[ForeignKey]: A `ForeignKey` instance representing the foreign key constraint,
                or `None` if the field is not a foreign key.
        """
        return self._database.get_foreign_key(self._name, field_name)

    def get_relationships(self) -> Dict[str, str]:
        return self._database.get_relationships(self.name)

    def get_field_type(self, field_name: str) -> str:
        """Retrieve the data type of a specific field in a specified table.

        Args:
            table_name (str): The name of the table.
            field_name (str): The name of the field.

        Returns:
            str: The data type of the field.
        """
        return self._database.get_field_type(self.name, field_name)

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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
