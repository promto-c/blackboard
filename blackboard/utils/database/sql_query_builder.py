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
        return self._num_values > 1 or self._num_values == -1

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
    def propagate_hierarchies(fields: List[str], separator: str = '.', prune_leaves: int = 0) -> List[str]:
        """Propagate and ensure all levels of hierarchy are referenced, with an option to prune levels from the leaves.

        Args:
            fields (list of str): List of hierarchical strings.
            separator (str): Separator used to split the hierarchy strings. Default is '.'.
            prune_leaves (int): Number of levels to prune from the end of each hierarchy. Default is 0.

        Returns:
            list of str: Unique propagated hierarchy references.

        Examples:
            >>> SQLQueryBuilder.propagate_hierarchies([
            ...     "shot.sequence.project.name", 
            ...     "shot.name", 
            ...     "name", 
            ...     "status", 
            ...     "user.name"
            ... ], prune_leaves=1)
            ['shot', 'shot.sequence', 'shot.sequence.project', 'user']

            >>> SQLQueryBuilder.propagate_hierarchies([
            ...     "department.team.lead.name",
            ...     "department.team.project.status",
            ...     "company.department.team.lead",
            ...     "company.department",
            ...     "team.member.task"
            ... ], prune_leaves=1)
            ['company', 'company.department', 'company.department.team', 'department', 'department.team', 'department.team.lead', 'department.team.project', 'team', 'team.member']

            >>> SQLQueryBuilder.propagate_hierarchies(["a.b.c.d", "a.b.c", "x.y.z"], prune_leaves=2)
            ['a', 'a.b', 'x']

            >>> SQLQueryBuilder.propagate_hierarchies(["level1/level2", "level1/level2/level3"], separator='/')
            ['level1', 'level1/level2', 'level1/level2/level3']

            >>> SQLQueryBuilder.propagate_hierarchies(["root.branch.leaf"], prune_leaves=3)
            []
        """
        prefixes = set()

        for field in fields:
            parts = field.split(separator)
            for i in range(len(parts) - prune_leaves):
                prefix = separator.join(parts[:i+1])
                prefixes.add(prefix)
        return sorted(prefixes)

    @staticmethod
    def build_select_clause(fields: Union[List[str], Dict[str, str]]):
        """Build the SELECT part of the query.

        Arguments:
            fields (Union[List[str], Dict[str, str]]): 
                List of field strings or a dictionary mapping field names to alias names.
            
        Returns:
            str: The SELECT clause in SQL format.

        Example:
            >>> SQLQueryBuilder.build_select_clause(["shot.sequence.project.name", "shot.name", "name", "status"])
            "SELECT\\n\\t'shot.sequence.project'.name AS 'shot.sequence.project.name',\\n\\t'shot'.name AS 'shot.name',\\n\\t_.name AS 'name',\\n\\t_.status AS 'status'"

            >>> SQLQueryBuilder.build_select_clause({"shot.sequence.project.name": "project_name", "shot.name": "shot_name"})
            "SELECT\\n\\t'shot.sequence.project'.name AS 'project_name',\\n\\t'shot'.name AS 'shot_name'"
        """
        # Convert input into a list of tuples: [(field, alias)]
        if isinstance(fields, list):
            # If it's a list, assume no alias is provided
            fields = [(field, field) for field in fields]
        elif isinstance(fields, dict):
            # If it's a dictionary, map the field to its alias
            fields = [(field, outer_alias) for field, outer_alias in fields.items()]

        # Handle both list of tuples (field, alias)
        select_parts = [
            f"{SQLQueryBuilder._build_inner_alias(field)} AS '{outer_alias}'" 
            for field, outer_alias in fields
        ]

        select_parts_str = ',\n\t'.join(select_parts)
        select_clause = f'SELECT\n\t{select_parts_str}'

        return select_clause

    @staticmethod
    def build_from_clause(current_model: str) -> str:
        """Build the FROM part of the query.

        Arguments:
            current_model (str): The main table (e.g., 'Tasks') for the query.

        Returns:
            str: The FROM clause in SQL format.

        Example:
            >>> SQLQueryBuilder.build_from_clause("Tasks")
            'FROM\\n\\tTasks AS _'
        """
        return f"FROM\n\t{current_model} AS _"

    @staticmethod
    def build_join_clause(fields: List[str], current_model: str, relationships: Dict[str, str]) -> str:
        """Build the JOIN part of the query.

        Arguments:
            relationships (Dict[str, str]): A dictionary of relationships between tables.

        Returns:
            str: The JOIN clause in SQL format.

        Example:
            >>> SQLQueryBuilder.build_join_clause(
            ...     fields=["shot.sequence.project.name", "shot.name", "name", "status"],
            ...     current_model="Tasks",
            ...     relationships={
            ...         "Tasks.shot": "Shots.id", 
            ...         "Shots.sequence": "Sequences.id",
            ...         "Sequences.project": "Projects.id",
            ...     }
            ... )
            "LEFT JOIN\\n\\tShots AS 'shot' ON _.shot = 'shot'.id\\nLEFT JOIN\\n\\tSequences AS 'shot.sequence' ON 'shot'.sequence = 'shot.sequence'.id\\nLEFT JOIN\\n\\tProjects AS 'shot.sequence.project' ON 'shot.sequence'.project = 'shot.sequence.project'.id"
        """
        relation_chains = SQLQueryBuilder.propagate_hierarchies(fields, prune_leaves=1)
        if not relation_chains:
            return ''

        join_clauses = []
        relation_chain_to_model = {}

        for relation_chain in relation_chains:
            if '.' not in relation_chain:
                reference_model = current_model
                reference_field = relation_chain
            else:
                reference_chain, reference_field = SQLQueryBuilder._parse_relationship(relation_chain)
                reference_model = relation_chain_to_model[reference_chain]

            reference_model_field = f'{reference_model}.{reference_field}'
            related_model_field = relationships[reference_model_field]
            related_model, related_field = SQLQueryBuilder._parse_relationship(related_model_field)

            relation_chain_to_model[relation_chain] = related_model

            related_model_alias = f"'{relation_chain}'"
            reference_field_alias = SQLQueryBuilder._build_inner_alias(relation_chain)
            join_clause = f"LEFT JOIN\n\t{related_model} AS {related_model_alias} ON {reference_field_alias} = {related_model_alias}.{related_field}"
            join_clauses.append(join_clause)

        return '\n'.join(join_clauses)

    @staticmethod
    def build_where_clause(conditions: Optional[Dict[Union[GroupOperator, str], Any]], 
                           group_operator: Union[GroupOperator, str] = GroupOperator.AND,
                           build_where_root: bool = True) -> Tuple[str, List[Any]]:
        """Build the WHERE clause of the query.

        Examples:
            >>> SQLQueryBuilder.build_where_clause({"name": "John"})
            ('WHERE\\n\\t_.name = ?', ['John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "age": {"gte": 18},
            ...     "name": {"contains": "John"}
            ... }, build_where_root=False)
            ("_.age >= ? AND _.name LIKE '%' || ? || '%'", [18, 'John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "status": {"in": ["active", "pending", "suspended"]}
            ... }, build_where_root=False)
            ('_.status IN (?, ?, ?)', ['active', 'pending', 'suspended'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "status": {"not_in": ["inactive", "deleted"]}
            ... }, build_where_root=False)
            ('_.status NOT IN (?, ?)', ['inactive', 'deleted'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "age": {"lt": 25},
            ...     "name": {"contains": "John"}
            ... }, build_where_root=False)
            ("_.age < ? AND _.name LIKE '%' || ? || '%'", [25, 'John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "id": 123
            ... }, build_where_root=False)
            ('_.id = ?', [123])

            >>> SQLQueryBuilder.build_where_clause({
            ...    "OR": {
            ...        "shot.sequence.project.name": {"contains": "Forest"},
            ...        "shot.status": {"eq": "Completed"},
            ...        "assigned_to.role": {"eq": "Artist"}
            ...    }
            ... })
            ("WHERE\\n\\t('shot.sequence.project'.name LIKE '%' || ? || '%' OR 'shot'.status = ? OR 'assigned_to'.role = ?)", ['Forest', 'Completed', 'Artist'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "OR": {
            ...         "age": {"lt": 18},
            ...         "AND": {
            ...             "status": {"eq": "inactive"},
            ...             "id": {"gte": 100}
            ...         }
            ...     }
            ... })
            ('WHERE\\n\\t(_.age < ? OR (_.status = ? AND _.id >= ?))', [18, 'inactive', 100])
        """
        if not conditions:
            return "", []

        where_clauses = []
        values = []

        for key, value in SQLQueryBuilder._extract_key_value_pairs(conditions):
            # Handle key as `GroupOperator`
            if isinstance(key, GroupOperator) or GroupOperator.is_valid(key):
                sub_where_clause, sub_values = SQLQueryBuilder.build_where_clause(
                    value, group_operator=key, build_where_root=False
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

            where_clause = f"{SQLQueryBuilder._build_inner_alias(key)} {sql_operator}"
            where_clauses.append(where_clause)

            # Handle special case for IN and NOT IN
            if operator.is_multi_value():
                values.extend(value)
            elif operator.requires_value():
                values.append(value)

        where_clauses_str = SQLQueryBuilder._join_where_clauses(where_clauses, group_operator)
        if build_where_root:
            where_clauses_str = f'WHERE\n\t{where_clauses_str}'

        return where_clauses_str, values

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
    def build_query(model: str, fields = None, conditions = None, relationships = None, order_by: Optional[Dict[str, SortOrder]] = None):
        query_clauses = [
            SQLQueryBuilder.build_select_clause(fields),
            SQLQueryBuilder.build_from_clause(model),
        ]

        join_clause = SQLQueryBuilder.build_join_clause(fields, model, relationships)
        where_clause, values = SQLQueryBuilder.build_where_clause(conditions)
        order_by_clause = SQLQueryBuilder.build_order_by_clause(order_by)

        if join_clause:
            query_clauses.append(join_clause)
        if where_clause:
            query_clauses.append(where_clause)
        if order_by_clause:
            query_clauses.append(order_by_clause)

        return '\n'.join(query_clauses), values

    @staticmethod
    def _extract_key_value_pairs(conditions: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Generator[Tuple[str, Any], None, None]:
        if isinstance(conditions, dict):  # Case where `where` is a dictionary
            yield from conditions.items()
        else:  # Case where `where` is a list of dictionaries
            for condition_dict in conditions:
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

    @staticmethod
    def _build_inner_alias(field: str) -> str:
        if '.' in field:
            relation_chain, relation_field = field.rsplit('.', 1)
            inner_alias = f"'{relation_chain}'.{relation_field}"
        else:
            inner_alias = f'_.{field}'

        return inner_alias


# Example usage
if __name__ == "__main__":
    import doctest
    doctest.testmod()

    # Example 1: Using List[str]
    current_model = 'Tasks'

    fields = [
        "shot.sequence.project.name",
        "shot.name",
        "name",
        "status",
        "parent_task.name",
        "start_date",
        "due_date",
        "assigned_to.email"
    ]

    conditions = {
        "OR": {
            "shot.sequence.project.name": {"contains": "Forest"},
            "shot.status": {"eq": "Completed"},
            "assigned_to.role": {"eq": "Artist"}
        }
    }

    relationships = {
        "Tasks.shot": "Shots.id",
        "Shots.sequence": "Sequences.id",
        "Sequences.project": "Projects.id",
        "Tasks.assigned_to": "Users.id",
        "Tasks.parent_task": "Tasks.id"
    }


    quary_clause, values = SQLQueryBuilder.build_query(model=current_model, fields=fields, conditions=conditions, relationships=relationships)
    print(quary_clause)
    print(values)
