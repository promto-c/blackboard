from typing import Dict, Any, List, Tuple, Optional, Union, Generator, Iterable, Set
from enum import Enum


class SortOrder(Enum):
    ASC = "ASC"
    DESC = "DESC"

    def __str__(self) -> str:
        """Convert enum to a string (supports .upper() for query generation)."""
        return self.value


class FilterOperation(Enum):
    # Display name, SQL operator, number of values
    GTE = ("Greater Than or Equal", ">= ?", 1)      
    LTE = ("Less Than or Equal", "<= ?", 1)
    GT = ("Greater Than", "> ?", 1)
    LT = ("Less Than", "< ?", 1)
    BEFORE = ("Before", "> ?", 1)
    AFTER = ("After", "< ?", 1)
    EQ = ("Equals", "= ?", 1)
    NEQ = ("Not Equals", "!= ?", 1)
    CONTAINS = ("Contains", "LIKE '%' || ? || '%'", 1)   # Special LIKE operator for string matching
    NOT_CONTAINS = ("Does Not Contain", "NOT LIKE '%' || ? || '%'", 1)
    STARTS_WITH = ("Starts With", "LIKE ? || '%'", 1)  # Start with pattern matching
    ENDS_WITH = ("Ends With", "LIKE '%' || ?", 1)      # End with pattern matching
    IS_NULL = ("Is Null", "IS NULL", 0)  # Checks for NULL values
    IS_NOT_NULL = ("Is Not Null", "IS NOT NULL", 0)  # Checks for NOT NULL values
    IN = ("In", "IN", -1)  # Special case for IN query, variable number of arguments
    NOT_IN = ("Not In", "NOT IN", -1)  # Special case for NOT IN query, variable number of arguments
    BETWEEN = ("Between", "BETWEEN ? AND ?", 2)  # Special case for BETWEEN operator, requires two values
    NOT_BETWEEN = ("Not Between", "NOT BETWEEN ? AND ?", 2)  # Special case for NOT BETWEEN operator, requires two values

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
        return self._num_values != 0

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


class FieldType(Enum):
    """Enum representing user-friendly column types and their associated filter widgets.
    """
    TEXT = 'Text'
    NUMERIC = 'Numeric'
    DATE = 'Date'
    DATETIME = 'Date & Time'
    BOOLEAN = 'True/False'
    ENUM = 'Single Select'
    LIST = 'Multiple Select'
    UUID = 'UUID'
    NULL = 'Null'

    @property
    def display_name(self):
        """Return the user-friendly display type of the column.
        """
        return self.value

    @property
    def supported_operations(self) -> List[FilterOperation]:
        return FieldTypeMapping.TO_SUPPORTED_OPERATORS.get(self, [])

    def __str__(self):
        """Return a string representation of the FieldType enum.
        """
        return self.name

    @staticmethod
    def from_sql(sql_type: str) -> 'FieldType':
        """Map SQL column type to the corresponding FieldType enum.

        Args:
            sql_type (str): The SQL type of the column.

        Returns:
            FieldType: The corresponding FieldType enum instance.
        """
        sql_type = sql_type.upper()

        # Map common SQL types to FieldType enum
        if any(keyword in sql_type for keyword in ['CHAR', 'VARCHAR', 'TEXT', 'CLOB']):
            return FieldType.TEXT
        # Combine integer and floating point SQL types into NUMERIC.
        elif any(keyword in sql_type for keyword in [
            'INT', 'INTEGER', 'TINYINT', 'SMALLINT', 'BIGINT', 'SERIAL',
            'REAL', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC', 'MONEY'
        ]):
            return FieldType.NUMERIC
        elif 'DATETIME' in sql_type or 'TIMESTAMP' in sql_type:
            return FieldType.DATETIME  # Support DATETIME types
        elif 'DATE' in sql_type:
            return FieldType.DATE
        elif any(keyword in sql_type for keyword in ['BOOLEAN', 'BOOL']):
            return FieldType.BOOLEAN
        elif 'ENUM' in sql_type:  # Assumption: custom enum or select types include 'ENUM' keyword
            return FieldType.ENUM
        elif 'LIST' in sql_type or 'ARRAY' in sql_type:  # Use 'LIST' for PostgreSQL array types
            return FieldType.LIST

        # PostgreSQL-Specific Types and others
        elif 'UUID' in sql_type:
            return FieldType.UUID
        elif 'JSON' in sql_type or 'JSONB' in sql_type:
            return FieldType.TEXT
        elif 'TSVECTOR' in sql_type or 'TSQUERY' in sql_type:
            return FieldType.TEXT
        elif 'HSTORE' in sql_type:
            return FieldType.TEXT
        elif any(keyword in sql_type for keyword in ['CIDR', 'INET', 'MACADDR']):
            return FieldType.TEXT
        elif 'BIT' in sql_type:
            return FieldType.NUMERIC
        elif 'INTERVAL' in sql_type:
            return FieldType.TEXT
        elif 'BYTEA' in sql_type:
            return FieldType.TEXT

        else:
            raise ValueError(f"Unsupported SQL type: {sql_type}")


class FieldTypeMapping:

    TO_SUPPORTED_OPERATORS = {
        FieldType.TEXT: [
            FilterOperation.CONTAINS,
            FilterOperation.NOT_CONTAINS,
            FilterOperation.STARTS_WITH,
            FilterOperation.ENDS_WITH,
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ],
        FieldType.NUMERIC: [
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.GT,
            FilterOperation.LT,
            FilterOperation.GTE,
            FilterOperation.LTE,
            FilterOperation.BETWEEN,
            FilterOperation.NOT_BETWEEN,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ],
        FieldType.DATE: [
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.BEFORE,
            FilterOperation.AFTER,
            FilterOperation.BETWEEN,
            FilterOperation.NOT_BETWEEN,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ],
        FieldType.DATETIME: [
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.BEFORE,
            FilterOperation.AFTER,
            FilterOperation.BETWEEN,
            FilterOperation.NOT_BETWEEN,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ],
        FieldType.BOOLEAN: [
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ],
        FieldType.ENUM: [
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.IN,
            FilterOperation.NOT_IN,
            FilterOperation.CONTAINS,
            FilterOperation.NOT_CONTAINS,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ],
        FieldType.LIST: [
            FilterOperation.EQ,              # Exact list equality
            FilterOperation.NEQ,             # Exact list inequality
            # FilterOperation.CONTAINS_ANY,    # The list contains at least one element of a provided set
            # FilterOperation.NOT_CONTAINS_ANY,
            # FilterOperation.CONTAINS_ALL,    # The list contains all elements of a provided set
            # FilterOperation.NOT_CONTAINS_ALL,
            FilterOperation.IN,              # At least one element in the list is in a given set
            FilterOperation.NOT_IN,          # None of the elements in the list are in a given set
            FilterOperation.IS_NULL,         # The list is null
            FilterOperation.IS_NOT_NULL,     # The list is not null
        ],
        FieldType.UUID: [
            FilterOperation.EQ,
            FilterOperation.NEQ,
            FilterOperation.IS_NULL,
            FilterOperation.IS_NOT_NULL,
        ]
    }


# Enum for logical operators (AND, OR) used for grouping
class GroupOperator(Enum):
    AND = "and"
    OR = "or"

    @property
    def display_name(self) -> str:
        return self.value

    @property
    def sql_operator(self) -> str:
        return self.name

    @classmethod
    def is_valid(cls, key: str) -> bool:
        try:
            cls[key.upper()]  # Try to access the enum by the string value
            return True
        except KeyError:
            return False

    def __str__(self):
        return self.value


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
            List[str]: Unique propagated hierarchy references (sorted lexicographically).

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
        # Preprocess fields to flatten into a list of strings
        expanded_fields = []
        for field in fields:
            if isinstance(field, str):
                # If the field is a string, add it directly
                expanded_fields.append(field)
            elif isinstance(field, dict):
                # If the field is a dictionarie, extract keys and add them
                expanded_fields.extend(field.keys())
            else:
                # Skip invalid field types
                continue
        fields = expanded_fields

        unique_hierarchies = set()

        for field in fields:
            tokens = field.split(separator)

            # Generate all prefix levels
            for i in range(len(tokens) - prune_leaves):
                prefix = separator.join(tokens[:i+1])
                unique_hierarchies.add(prefix)

        # Return a lexicographically sorted list
        return sorted(unique_hierarchies)

    @staticmethod
    def build_select_clause(fields: Union[List[Union[str, Dict[str, str]]], Dict[str, str]] = None, relationships = None, base_model = None) -> str:
        """Build the SELECT part of the query.

        Arguments:
            fields: A list containing field names as strings or dictionaries mapping a field to an alias,
                or a dictionary mapping multiple fields to aliases.

        Returns:
            str: The SELECT clause in SQL format.

        Examples:
            >>> SQLQueryBuilder.build_select_clause(["shot.sequence.project.name", "shot.name", "name", "status"])
            "SELECT\\n\\t'shot.sequence.project'.name AS 'shot.sequence.project.name',\\n\\t'shot'.name AS 'shot.name',\\n\\t_.name AS 'name',\\n\\t_.status AS 'status'"

            >>> SQLQueryBuilder.build_select_clause({"shot.sequence.project.name": "project_name", "shot.name": "shot_name"})
            "SELECT\\n\\t'shot.sequence.project'.name AS 'project_name',\\n\\t'shot'.name AS 'shot_name'"

            >>> SQLQueryBuilder.build_select_clause(["shot.sequence.project.name", {"shot.name": "my_shot_name"}, "status"])
            "SELECT\\n\\t'shot.sequence.project'.name AS 'shot.sequence.project.name',\\n\\t'shot'.name AS 'my_shot_name',\\n\\t_.status AS 'status'"
        """
        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        grouped_field_aliases = set()

        def _is_one_to_many_field(field):
            if '.' not in field:
                return False
            parent_field, _ = SQLQueryBuilder._parse_relationship(field)
            relation_chain = f'{base_model}.{parent_field}'
            if relation_chain not in relationships:
                return False
            return relationships[relation_chain] in relationships

        def _build(field, alias):
            field_inner_alias = SQLQueryBuilder._build_inner_alias(field)
            if _is_one_to_many_field(field):
                field_inner_alias = f"JSON_GROUP_ARRAY({field_inner_alias})"
                grouped_field_aliases.add(alias)

            return f"{field_inner_alias} AS '{alias}'"

        # Convert input into a list of tuples: [(field, alias)]
        if not fields:
            return "SELECT *"
        elif isinstance(fields, dict):
            # Convert each dictionary item into tuples of (field, alias)
            fields = [(field, alias) for field, alias in fields.items()]
        elif isinstance(fields, Iterable) and not isinstance(fields, str):
            expanded_fields = []
            for f in fields:
                if isinstance(f, str):
                    expanded_fields.append((f, f))
                elif isinstance(f, dict):
                    for field, alias in f.items():
                        expanded_fields.append((field, alias))
                else:
                    raise TypeError("Unsupported field type in fields list.")
            fields = expanded_fields
        else:
            # Treat any other string input as a direct SELECT clause
            return f"SELECT\n\t{fields}"

        # Handle both list of tuples (field, alias)
        select_parts = [
            _build(field, alias)
            for field, alias in fields
        ]
        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        return "SELECT\n\t" + ",\n\t".join(select_parts), grouped_field_aliases

    @staticmethod
    def build_from_clause(current_model: str) -> str:
        """Build the FROM part of the query.

        Arguments:
            current_model (str): The main table (e.g., 'Tasks') for the query.

        Returns:
            str: The FROM clause in SQL format.

        Example:
            >>> SQLQueryBuilder.build_from_clause("Tasks")
            "FROM\\n\\t'Tasks' AS _"
        """
        return f"FROM\n\t'{current_model}' AS _"

    @staticmethod
    def build_join_clause(fields: List[str],
                          current_model: str,
                          relationships: Dict[str, str],
                          separator: str = '.') -> str:
        """Build the JOIN part of the query.

        Args:
            fields (List[str]): A list of hierarchical field strings, 
                e.g. ["shot.sequence.project.name", "shot.name", "status"].
            current_model (str): The base table/model for the current query, e.g. "Tasks".
            relationships (Dict[str, str]): A dictionary of relationships between tables,
                e.g. {"Tasks.shot": "Shots.id", "Shots.sequence": "Sequences.id"}.
            separator (str): Separator used for hierarchy splitting. Default is '.'.

        Returns:
            str: The JOIN clause in SQL format.

        Example:
            >>> SQLQueryBuilder.build_join_clause(
            ...     fields=["shot.sequence.project.name", "shot.name", "name", "status", "assets.name"],
            ...     current_model="Tasks",
            ...     relationships={
            ...         "Tasks.shot": "Shots.id",
            ...         "Shots.sequence": "Sequences.id",
            ...         "Sequences.project": "Projects.id",
            ...         "Tasks.assets": "Assets.task",
            ...         "Assets.task": "Tasks.id",
            ...     }
            ... )
            "LEFT JOIN\\n\\tShots AS 'shot' ON _.shot = 'shot'.id\\nLEFT JOIN\\n\\tSequences AS 'shot.sequence' \
ON 'shot'.sequence = 'shot.sequence'.id\\nLEFT JOIN\\n\\tProjects AS 'shot.sequence.project' \
ON 'shot.sequence'.project = 'shot.sequence.project'.id\\nLEFT JOIN\\n\\tAssets AS 'assets' ON _.id = 'assets'.task"
        """
        # 1) Gather all chain prefixes that need to be joined up to (but not including) the final leaf
        #    For example, "shot.sequence" is taken from "shot.sequence.project.name"
        #    We apply prune_leaves=1 so "project.name" => "project" is recognized, but not "name" alone.
        relation_chains = SQLQueryBuilder.propagate_hierarchies(fields, separator=separator, prune_leaves=1)
        if not relation_chains:
            return '', ''

        # Maps a chain prefix (e.g. "shot" or "shot.sequence") to the table name (e.g. "Shots", "Sequences")
        relation_chain_to_table: Dict[str, str] = {}
        group_by_fields: Set[str] = set()

        # 2) Build the JOIN statements for each relation_chain
        join_clauses = []
        for chain in relation_chains:
            # If there's no separator in this chain (single token), then it's directly from the base model.
            if separator not in chain:
                left_table = current_model
                left_column = chain
            else:
                # For something like "shot.sequence", parse the parent prefix (e.g. "shot") and the last token ("sequence")
                parent_chain, left_column = SQLQueryBuilder._parse_relationship(chain, separator=separator)
                # The left_table is determined by whatever we assigned "parent_chain" to be
                left_table = relation_chain_to_table[parent_chain]

            # `left_table_field` is something like "Tasks.shot" or "Shots.sequence"
            left_table_field = f'{left_table}.{left_column}'

            # `relationships` dict should map that to e.g. "Shots.id" => right_table_field
            # which we then parse into e.g. right_table="Shots", right_column="id"
            right_table_field = relationships[left_table_field]
            right_table, right_column = SQLQueryBuilder._parse_relationship(right_table_field, separator=separator)

            # On the left side, we might need to reference the base model or a previous alias
            right_table_alias = f"'{chain}'"
            right_column_alias = f'{right_table_alias}.{right_column}'

            # Build the LEFT JOIN snippet
            if right_table_field in relationships:
                # NOTE: Handle indirect relational fields, such as one-to-many relationships.
                a, _ = SQLQueryBuilder._parse_relationship(SQLQueryBuilder._build_inner_alias(chain), separator=separator)
                _, b = SQLQueryBuilder._parse_relationship(relationships[right_table_field], separator=separator)
                left_column_alias = f'{a}.{b}'
                group_by_fields.add(left_column_alias)
            else:
                left_column_alias = SQLQueryBuilder._build_inner_alias(chain)

            # Store the discovered right_table in relation_chain_to_table, so future children
            # of this chain know which table they come from.
            relation_chain_to_table[chain] = right_table

            # "LEFT JOIN Shots AS 'shot' ON _.shot = 'shot'.id"
            join_clause = (
                f"LEFT JOIN\n\t{right_table} AS {right_table_alias} "
                f"ON {left_column_alias} = {right_column_alias}"
            )
            join_clauses.append(join_clause)

        if group_by_fields:
            group_by_fields_str = ', '.join(group_by_fields)
            group_by_clause = f'GROUP BY\n\t{group_by_fields_str}'
        else:
            group_by_clause = None

        # 3) Return them as a single multi-line string
        return '\n'.join(join_clauses), group_by_clause

    @staticmethod
    def build_where_clause(conditions: Optional[Dict[Union[GroupOperator, str], Any]], 
                           group_operator: Union[GroupOperator, str] = GroupOperator.AND,
                           build_where_root: bool = True) -> Tuple[str, Set[str], List[Any]]:
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
        where_clauses = []
        values = []
        fields = set()

        if not conditions:
            return None, None, None

        if isinstance(conditions, str):
            return f'WHERE\n\t{conditions}', fields, values

        for key, value in SQLQueryBuilder._extract_key_value_pairs(conditions):
            # Handle key as `GroupOperator`
            if isinstance(key, GroupOperator) or GroupOperator.is_valid(key):
                sub_where_clause, sub_fields, sub_values = SQLQueryBuilder.build_where_clause(
                    value, group_operator=key, build_where_root=False
                )
                where_clauses.append(f"({sub_where_clause})")
                fields.update(sub_fields)
                values.extend(sub_values)
                continue

            # Handle 
            if not isinstance(value, dict):
                operator = FilterOperation.EQUALS
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

            fields.add(key)
            where_clause = f"{SQLQueryBuilder._build_inner_alias(key)} {sql_operator}"
            where_clauses.append(where_clause)

            # Handle special case for IN and NOT IN
            if operator.is_multi_value() or operator.num_values > 1:
                values.extend(value)
            elif operator.requires_value():
                values.append(value)

        where_clauses_str = SQLQueryBuilder._join_where_clauses(where_clauses, group_operator)
        if build_where_root:
            where_clauses_str = f'WHERE\n\t{where_clauses_str}'

        return where_clauses_str, fields, values

    @staticmethod
    def build_order_by_clause(order_by: Optional[Dict[str, SortOrder]]) -> str:
        """Build the ORDER BY clause of the query.
        
        >>> SQLQueryBuilder.build_order_by_clause({
        ...     "shot.name": SortOrder.DESC,
        ...     "name": SortOrder.ASC
        ... })
        "ORDER BY\\n\\t'shot'.name DESC, _.name ASC"
        
        >>> SQLQueryBuilder.build_order_by_clause({
        ...     "shot.name": "desc",
        ...     "name": "asc"
        ... })
        "ORDER BY\\n\\t'shot'.name DESC, _.name ASC"
        """
        if not order_by:
            return ""
        
        if isinstance(order_by, str):
            return f'ORDER BY\n\t{order_by}'

        # Ensure that the input for order_by values are `SortOrder` or strings
        order_by_clause = ", ".join(
            [f"{SQLQueryBuilder._build_inner_alias(field)} {str(direction).upper()}" for field, direction in order_by.items()]
        )

        return f"ORDER BY\n\t{order_by_clause}"

    @staticmethod
    def build_query(model: str, fields = None, conditions = None, relationships = None, order_by: Optional[Dict[str, SortOrder]] = None, limit: int = None, values = None):
        
        # Fill relationships
        if relationships:
            relationships = {
                f'{model}.{key}' if '.' not in key else key: value
                for key, value in relationships.items()
            }

        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        select_clause, grouped_field_aliases = SQLQueryBuilder.build_select_clause(fields, relationships, base_model=model)

        query_clauses = [
            select_clause,
            SQLQueryBuilder.build_from_clause(model),
        ]

        where_clause, where_fields, extracted_values = SQLQueryBuilder.build_where_clause(conditions)
        if where_fields:
            if fields:
                fields = list(where_fields) + list(fields)
            else:
                fields = list(where_fields)
        join_clause, group_by_clause = SQLQueryBuilder.build_join_clause(fields, model, relationships)
        
        values = values or extracted_values
        order_by_clause = SQLQueryBuilder.build_order_by_clause(order_by)

        if join_clause:
            query_clauses.append(join_clause)
        if where_clause:
            query_clauses.append(where_clause)
        if group_by_clause:
            query_clauses.append(group_by_clause)
        if order_by_clause:
            query_clauses.append(order_by_clause)
        if limit:
            query_clauses.append(f'LIMIT\n\t{limit}')

        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        return '\n'.join(query_clauses), values, grouped_field_aliases

    @staticmethod
    def _extract_key_value_pairs(conditions: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Generator[Tuple[str, Any], None, None]:
        if isinstance(conditions, dict):  # Case where `where` is a dictionary
            yield from conditions.items()
        else:  # Case where `where` is a list of dictionaries
            for condition_dict in conditions:
                yield next(iter(condition_dict.items()))

    @staticmethod
    def _parse_relationship(relationship: str, separator: str = '.'):
        """Parse a simplified relationship string into components.
        """
        return relationship.rsplit(separator, 1)

    @staticmethod
    def _join_where_clauses(where_clauses: List[str], group_operator: Union[GroupOperator, str]) -> str:
        if isinstance(group_operator, GroupOperator):
            group_operator_str = group_operator.sql_operator
        else:
            group_operator_str = group_operator.upper()

        return f" {group_operator_str} ".join(where_clauses)

    @staticmethod
    def _build_inner_alias(field: str, base_alias: str = '_', separator: str = '.') -> str:
        if separator in field:
            # e.g. "shot.sequence" => "'shot'.sequence"
            relation_chain, relation_field = SQLQueryBuilder._parse_relationship(field, separator=separator)
            inner_alias = f"'{relation_chain}'.{relation_field}"
        else:
            # e.g. "shot" => '_.shot'
            inner_alias = f'{base_alias}.{field}'

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
        "assigned_to.email",
        "assets.name",      # Indirect relational field
        "child_tasks.name", # Indirect relational field
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
        "Tasks.parent_task": "Tasks.id",
        # TODO: Update to support reference fields for one-to-many relationships
        "Tasks.child_tasks": "Tasks.parent_task",   # Indirect relational field
        "Tasks.assets": "Assets.task",  # Indirect relational field
        "Assets.task": "Tasks.id",
    }

    order_by = {
        "shot.name": "desc",
        "name": "asc"
    }

    quary_clause, values, grouped_field_aliases = SQLQueryBuilder.build_query(
        model=current_model,
        fields=fields,
        conditions=conditions,
        relationships=relationships,
        order_by=order_by,
        limit=5
    )
    print(quary_clause)
    print(values)
    # NOTE: Example outputs
    # SELECT
    #         'shot.sequence.project'.name AS 'shot.sequence.project.name',
    #         'shot'.name AS 'shot.name',
    #         _.name AS 'name',
    #         _.status AS 'status',
    #         'parent_task'.name AS 'parent_task.name',
    #         _.start_date AS 'start_date',
    #         _.due_date AS 'due_date',
    #         'assigned_to'.email AS 'assigned_to.email',
    #         JSON_GROUP_ARRAY('assets'.name) AS 'assets.name'
    # FROM
    #         'Tasks' AS _
    # LEFT JOIN
    #         Users AS 'assigned_to' ON _.assigned_to = 'assigned_to'.id
    # LEFT JOIN
    #         Tasks AS 'parent_task' ON _.parent_task = 'parent_task'.id
    # LEFT JOIN
    #         Shots AS 'shot' ON _.shot = 'shot'.id
    # LEFT JOIN
    #         Sequences AS 'shot.sequence' ON 'shot'.sequence = 'shot.sequence'.id
    # LEFT JOIN
    #         Projects AS 'shot.sequence.project' ON 'shot.sequence'.project = 'shot.sequence.project'.id
    # LEFT JOIN
    #         Assets AS 'assets' ON _.id = 'assets'.task GROUP BY _.id
    # WHERE
    #         ('shot.sequence.project'.name LIKE '%' || ? || '%' OR 'shot'.status = ? OR 'assigned_to'.role = ?)
    # ORDER BY
    #         'shot'.name DESC, _.name ASC
    # LIMIT
    #         5
    # ['Forest', 'Completed', 'Artist']
