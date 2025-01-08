from typing import Dict, Any, List, Tuple, Optional, Union, Generator, Iterable
from enum import Enum


class SortOrder(Enum):
    ASC = "ASC"
    DESC = "DESC"

    def __str__(self) -> str:
        """Convert enum to a string (supports .upper() for query generation)."""
        return self.value


class FilterOperation(Enum):
    # Display name, SQL operator, number of values
    GTE = ("gte", ">= ?", 1)      
    LTE = ("lte", "<= ?", 1)
    GT = ("gt", "> ?", 1)
    LT = ("lt", "< ?", 1)
    EQ = ("eq", "= ?", 1)
    NEQ = ("neq", "!= ?", 1)
    CONTAINS = ("contains", "LIKE '%' || ? || '%'", 1)   # Special LIKE operator for string matching
    STARTS_WITH = ("starts_with", "LIKE ? || '%'", 1)  # Start with pattern matching
    ENDS_WITH = ("ends_with", "LIKE '%' || ?", 1)      # End with pattern matching
    IS_NULL = ("is_null", "IS NULL", 0)  # Checks for NULL values
    IS_NOT_NULL = ("is_not_null", "IS NOT NULL", 0)  # Checks for NOT NULL values
    IN = ("in", "IN", -1)  # Special case for IN query, variable number of arguments
    NOT_IN = ("not_in", "NOT IN", -1)  # Special case for NOT IN query, variable number of arguments
    BETWEEN = ("between", "BETWEEN ? AND ?", 2)  # Special case for BETWEEN operator, requires two values
    NOT_BETWEEN = ("not_between", "NOT BETWEEN ? AND ?", 2)  # Special case for NOT BETWEEN operator, requires two values

    # Initialization and Setup
    # ------------------------
    def __init__(self, display_name: str, sql_operator: str, num_values: int):
        """Initialize the enum with its display name, SQL operator, and number of values.
        """
        self._display_name = display_name
        self._sql_operator = sql_operator
        self._num_values = num_values

    @property
    def display_name(self) -> str:
        """Return the display name of the filter operation.
        """
        return self._display_name

    @property
    def sql_operator(self) -> str:
        """Return the SQL operator for the filter operation.
        """
        return self._sql_operator

    @property
    def num_values(self) -> Optional[int]:
        """Return the number of values required for the filter operation.
        """
        return self._num_values

    def requires_value(self) -> bool:
        """Determine if the filter condition requires input values.

        Returns:
            bool: True if values are required, False otherwise.
        """
        return self._num_values > 0

    def is_multi_value(self) -> bool:
        """Return True if the operation supports multiple values."""
        return self._num_values == -1

    @classmethod
    def from_string(cls, name: str) -> 'FilterOperation':
        return cls[name.upper()]

    def __str__(self):
        """Return the string representation of the filter operation.
        """
        return self._display_name


# Enum for logical operators (AND, OR) used for grouping
class GroupOperator(Enum):
    AND = ("and", "AND")
    OR = ("or", "OR")

    def __init__(self, display_name: str, sql_operator: str):
        self._display_name = display_name
        self._sql_operator = sql_operator

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def sql_operator(self) -> str:
        return self._sql_operator

    @classmethod
    def is_valid(cls, key: str) -> bool:
        try:
            cls[key.upper()]  # Try to access the enum by the string value
            return True
        except KeyError:
            return False

    def __str__(self):
        return self._display_name


class SQLQueryBuilder:

    # Utility Methods
    # ---------------
    @staticmethod
    def build_select_clause(select: Optional[Union[str, List[str]]] = None) -> str:
        """Build the SELECT clause of the query.
        
        If `select` is a single string, treat it as a single field.
        If `select` is a list, join the elements as comma-separated fields.
        If `select` is None, select all fields (*).
        
        >>> SQLQueryBuilder.build_select_clause("name")
        'name'
        >>> SQLQueryBuilder.build_select_clause(["id", "name", "email"])
        'id, name, email'
        >>> SQLQueryBuilder.build_select_clause(None)
        '*'
        """
        if select is None:
            return "*"
        elif isinstance(select, str):
            return select
        elif isinstance(select, list):
            return ", ".join(select)
        else:
            raise ValueError("select must be a string or a list of strings")

    @staticmethod
    def build_where_clause(where: Optional[Dict[Union[GroupOperator, str], Any]], 
                           group_operator: Union[GroupOperator, str] = GroupOperator.AND,
                           relationships: Optional[Dict[str, str]] = None) -> Tuple[str, List[Any]]:
        """Build the WHERE clause of the query.

        Examples:
            >>> SQLQueryBuilder.build_where_clause({"name": "John"})
            ('name = ?', ['John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "age": {"gte": 18},
            ...     "name": {"contains": "John"}
            ... })
            ("age >= ? AND name LIKE '%' || ? || '%'", [18, 'John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "status": {"in": ["active", "pending", "suspended"]}
            ... })
            ('status IN (?, ?, ?)', ['active', 'pending', 'suspended'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "status": {"not_in": ["inactive", "deleted"]}
            ... })
            ('status NOT IN (?, ?)', ['inactive', 'deleted'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "age": {"lt": 25},
            ...     "name": {"contains": "John"}
            ... })
            ("age < ? AND name LIKE '%' || ? || '%'", [25, 'John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "id": 123
            ... })
            ('id = ?', [123])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "AND": {
            ...         "age": {"gte": 18},
            ...         "OR": [
            ...             {"status": "active"},
            ...             {"status": {"eq": "pending"}}
            ...         ]
            ...     }
            ... })
            ('(age >= ? AND (status = ? OR status = ?))', [18, 'active', 'pending'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "OR": {
            ...         "age": {"lt": 18},
            ...         "AND": {
            ...             "status": {"eq": "inactive"},
            ...             "id": {"gte": 100}
            ...         }
            ...     }
            ... })
            ('(age < ? OR (status = ? AND id >= ?))', [18, 'inactive', 100])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "OR": {
            ...         "author.name": {"contains": "John"},
            ...         "AND": {
            ...             "publisher.name": {"eq": "Penguin"},
            ...             "title": {"contains": "Classic"}
            ...         }
            ...     }
            ... }, relationships={
            ...     "author": "Authors.id",
            ...     "publisher": "Publishers.id"
            ... })
            ("(author IN (SELECT id FROM Authors WHERE name LIKE '%' || ? || '%') OR (publisher IN (SELECT id FROM Publishers WHERE name = ?) AND title LIKE '%' || ? || '%'))", ['John', 'Penguin', 'Classic'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "OR": {
            ...         "author.name": {"contains": "John"},
            ...         "author.publisher.country": {"eq": "USA"},
            ...         "author.publisher.name": {"eq": "Penguin"},
            ...         }
            ... }, relationships={
            ...     "author": "Authors.id",
            ...     "author.publisher": "Publishers.id"
            ... })
            ("(author IN (SELECT id FROM Authors WHERE name LIKE '%' || ? || '%') OR author IN (SELECT id FROM Authors WHERE publisher IN (SELECT id FROM Publishers WHERE country = ?)) OR author IN (SELECT id FROM Authors WHERE publisher IN (SELECT id FROM Publishers WHERE name = ?)))", ['John', 'USA', 'Penguin'])
        """
        if not where:
            return "", []

        where_clauses = []
        values = []

        for key, value in SQLQueryBuilder._extract_key_value_pairs(where):
            # Handle key as `GroupOperator`
            if isinstance(key, GroupOperator) or GroupOperator.is_valid(key):
                sub_where_clause, sub_values = SQLQueryBuilder.build_where_clause(
                    value, group_operator=key, relationships=relationships
                )
                where_clauses.append(f"({sub_where_clause})")
                values.extend(sub_values)
                continue

            # Handle 
            if not isinstance(value, dict):
                operator = FilterOperation.EQ
            else:
                # Extract the operator and value
                operator, value = next(iter(value.items()))

            if not isinstance(operator, FilterOperation):
                operator = FilterOperation.from_string(operator)

            if operator.is_multi_value():
                if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
                    raise ValueError(f"For '{operator}' operation, value should be an iterable (but not a string or bytes)")
                placeholders = ', '.join(['?'] * len(value))
                sql_operator = f"{operator.sql_operator} ({placeholders})"
            else:
                sql_operator = operator.sql_operator

            where_clause = SQLQueryBuilder._generate_where_clause(key, relationships, sql_operator)
            where_clauses.append(where_clause)

            # Handle special case for IN and NOT IN
            if operator.num_values > 1:
                values.extend(value)
            elif operator.requires_value():
                values.append(value)

        return SQLQueryBuilder._join_where_clauses(where_clauses, group_operator), values

    @staticmethod
    def _generate_where_clause(key: str, relationships, operator=None):
        if '.' not in key: # Related field (e.g., "publisher.name")
            return f"{key} {operator}"

        local_field, relation_field = SQLQueryBuilder._parse_relationship(key)
        related_table, related_field = SQLQueryBuilder._parse_relationship(relationships[local_field])
        operator = f"IN (SELECT {related_field} FROM {related_table} WHERE {relation_field} {operator})"
        where_clause = SQLQueryBuilder._generate_where_clause(local_field, relationships, operator)

        return where_clause

    @staticmethod
    def build_order_by_clause(order_by: Optional[Dict[str, SortOrder]]) -> str:
        """Build the ORDER BY clause of the query.
        
        >>> SQLQueryBuilder.build_order_by_clause({
        ...     "createdAt": SortOrder.DESC,
        ...     "name": SortOrder.ASC
        ... })
        'createdAt DESC, name ASC'
        
        >>> SQLQueryBuilder.build_order_by_clause({
        ...     "createdAt": "desc",
        ...     "name": "asc"
        ... })
        'createdAt DESC, name ASC'
        """
        if not order_by:
            return ""

        # Ensure that the input for order_by values are `SortOrder` or strings
        return ", ".join(
            [f"{field} {str(direction).upper()}" for field, direction in order_by.items()]
        )

    @staticmethod
    def _extract_key_value_pairs(where: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Generator[Tuple[str, Any], None, None]:
        if isinstance(where, dict):  # Case where `where` is a dictionary
            yield from where.items()
        else:  # Case where `where` is a list of dictionaries
            for condition_dict in where:
                yield next(iter(condition_dict.items()))

    @staticmethod
    def _parse_relationship(relationship: str):
        """Parse a simplified relationship string into components.
        """
        return relationship.rsplit('.', 1)
    
    @staticmethod
    def _join_where_clauses(where_clauses: List[str], group_operator: Union[GroupOperator, str]) -> str:
        if isinstance(group_operator, GroupOperator):
            group_operator_str = group_operator.sql_operator
        else:
            group_operator_str = group_operator.upper()

        return f" {group_operator_str} ".join(where_clauses)


# If you want to run doctests manually, you can include this code block:
if __name__ == "__main__":
    import doctest
    doctest.testmod()

    # Example usage for a condition with logical operators and multi-value support:
    where_clause, params = SQLQueryBuilder.build_where_clause({
        "age": {"gte": 18},
        "status": {"in": ["active", "pending", "suspended"]},
        "name": {"contains": "John"},
        GroupOperator.OR: {
                "role": {"eq": "admin"},
                "permission": {"in": ["read", "write"]}
            }
        }
    )
    print(where_clause)
    # age >= ? AND status IN (?, ?, ?) AND name LIKE '%' || ? || '%' AND (role = ? OR permission IN (?, ?))
    print(params)
    # [18, 'active', 'pending', 'suspended', 'John', 'admin', 'read', 'write'])

    filters = {
        "OR": {
            "author.name": {"contains": "John"},
            "AND": {
                "publisher.name": {"eq": "Penguin"},
                "title": {"contains": "Classic"}
            }
        }
    }
    relationships = {
        "author": "Authors.id",  # books.author -> Authors.id
        "publisher": "Publishers.id"  # books.publisher -> Publishers.id
    }

    where_clause, params = SQLQueryBuilder.build_where_clause(
        where=filters, relationships=relationships
    )
    print(where_clause)
    # (author IN (SELECT id FROM Authors WHERE name LIKE '%' || ? || '%') OR (publisher IN (SELECT id FROM Publishers WHERE name = ?) AND title LIKE '%' || ? || '%'))
    print(params)
    # [18, 'active', 'pending', 'suspended', 'John', 'admin', 'read', 'write'])

filters = {
    "OR": {
        "author.name": {"contains": "John"},
        "author.publisher.country": {"eq": "USA"},
        "author.publisher.name": {"eq": "Penguin"},
    }
}

key = "author.publisher.country"

relationships = {
    "author": "Authors.id",  # books.author -> Authors.id
    "author.publisher": "Publishers.id",  # authors.publisher -> Publishers.id
}
where_clause = SQLQueryBuilder._generate_where_clause(key, relationships, FilterOperation.BETWEEN.sql_operator)
print(where_clause)
