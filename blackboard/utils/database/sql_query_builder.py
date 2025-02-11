# Type Checking Imports
# ---------------------
from typing import Dict, Any, List, Tuple, Optional, Union, Generator, Iterable, Set

# Standard Library Imports
# ------------------------
from dataclasses import dataclass, field

# Local Imports
# -------------
from blackboard.enums.view_enum import GroupOperator, SortOrder, FilterOperation


# Class Definitions
# -----------------
# NOTE: WIP
@dataclass
class QueryContext:
    """A class that holds the context for a built query, including its components such as fields, conditions, and relationships."""
    model: str
    query: str
    values: List[Any]
    relationships: Dict[str, str] = field(default_factory=dict)
    field_to_alias: Dict[str, str] = field(default_factory=dict)
    alias_to_field: Dict[str, str] = field(default_factory=dict)
    grouped_field_aliases: List[str] = field(default_factory=list)

    def add_field_alias_pairs(self, pairs: List[Tuple[str, str]]) -> None:
        """Add field-alias pairs and maintain a reversible mapping.

        This method updates both `field_aliases` (field → alias) and 
        `alias_to_field` (alias → field) mappings.

        Args:
            pairs (List[Tuple[str, str]]): A list of tuples where the first value is 
                                           the field name and the second is the alias.

        Example:
            >>> result = QueryResult(query="SELECT id FROM tasks", values=[])
            >>> result.add_field_alias_pairs([("tasks.id", "task_id"), ("tasks.name", "task_name")])
            >>> print(result.field_aliases)
            {'tasks.id': 'task_id', 'tasks.name': 'task_name'}
            >>> print(result.alias_to_field)
            {'task_id': 'tasks.id', 'task_name': 'tasks.name'}
        """
        for field, alias in pairs:
            # Ensure no duplicate alias is assigned to different fields
            if alias in self.alias_to_field and self.alias_to_field[alias] != field:
                raise ValueError(f"Alias '{alias}' is already mapped to '{self.alias_to_field[alias]}'.")

            # Store mappings
            self.field_to_alias[field] = alias
            self.alias_to_field[alias] = field


class SQLQueryBuilder:

    CHAIN_SEPARATOR = '.'

    # Utility Methods
    # ---------------
    @staticmethod
    def resolve_model(base_model: str, relation_chain: str, relationships: Dict[str, str], sep: str = CHAIN_SEPARATOR) -> str:
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
        unique_hierarchies = set()

        # Iterate over the flattened fields and process the hierarchical tokens.
        for field in SQLQueryBuilder._extract_key_value_pairs(fields, keys_only=True):
            tokens = field.split(separator)

            # Generate all prefix levels
            for i in range(len(tokens) - prune_leaves):
                prefix = separator.join(tokens[:i+1])
                unique_hierarchies.add(prefix)

        # Return a lexicographically sorted list
        return sorted(unique_hierarchies)

    @staticmethod
    def build_select_clause(fields: List[str | Dict[str, str]] | Dict[str, str] = None, relationships = None, base_model = None) -> str:
        """Build the SELECT part of the query.

        Arguments:
            fields: A list containing field names as strings or dictionaries mapping a field to an alias,
                or a dictionary mapping multiple fields to aliases.

        Returns:
            str: The SELECT clause in SQL format.

        Examples:
            >>> SQLQueryBuilder.build_select_clause(["shot.sequence.project.name", "shot.name", "name", "status"])
            "'shot.sequence.project'.name AS 'shot.sequence.project.name',\\n\\t'shot'.name AS 'shot.name',\\n\\t_.name AS 'name',\\n\\t_.status AS 'status'"

            >>> SQLQueryBuilder.build_select_clause({"shot.sequence.project.name": "project_name", "shot.name": "shot_name"})
            "'shot.sequence.project'.name AS 'project_name',\\n\\t'shot'.name AS 'shot_name'"

            >>> SQLQueryBuilder.build_select_clause(["shot.sequence.project.name", {"shot.name": "my_shot_name"}, "status"])
            "'shot.sequence.project'.name AS 'shot.sequence.project.name',\\n\\t'shot'.name AS 'my_shot_name',\\n\\t_.status AS 'status'"
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
            return "*", grouped_field_aliases

        # Handle both list of tuples (field, alias)
        select_parts = [
            _build(field, alias)
            for field, alias in SQLQueryBuilder._extract_key_value_pairs(fields)
        ]
        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        return ",\n\t".join(select_parts), grouped_field_aliases

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
            return None, None

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

        # 3) Return them as a single multi-line string
        return '\n'.join(join_clauses), ', '.join(group_by_fields)

    @staticmethod
    def build_where_clause(conditions: Dict[Union[GroupOperator, str], Any], 
                           group_operator: Union[GroupOperator, str] = GroupOperator.AND,
                           ) -> Tuple[str, Set[str], List[Any]]:
        """Build the WHERE clause of the query.

        Examples:
            >>> SQLQueryBuilder.build_where_clause({"name": "John"})
            ('_.name = ?', ['John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "age": {"gte": 18},
            ...     "name": {"contains": "John"}
            ... })
            ("_.age >= ? AND _.name LIKE '%' || ? || '%'", [18, 'John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "status": {"in": ["active", "pending", "suspended"]}
            ... })
            ('_.status IN (?, ?, ?)', ['active', 'pending', 'suspended'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "status": {"not_in": ["inactive", "deleted"]}
            ... })
            ('_.status NOT IN (?, ?)', ['inactive', 'deleted'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "age": {"lt": 25},
            ...     "name": {"contains": "John"}
            ... })
            ("_.age < ? AND _.name LIKE '%' || ? || '%'", [25, 'John'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "id": 123
            ... })
            ('_.id = ?', [123])

            >>> SQLQueryBuilder.build_where_clause({
            ...    "OR": {
            ...        "shot.sequence.project.name": {"contains": "Forest"},
            ...        "shot.status": {"eq": "Completed"},
            ...        "assigned_to.role": {"eq": "Artist"}
            ...    }
            ... })
            ("('shot.sequence.project'.name LIKE '%' || ? || '%' OR 'shot'.status = ? OR 'assigned_to'.role = ?)", ['Forest', 'Completed', 'Artist'])

            >>> SQLQueryBuilder.build_where_clause({
            ...     "OR": {
            ...         "age": {"lt": 18},
            ...         "AND": {
            ...             "status": {"eq": "inactive"},
            ...             "id": {"gte": 100}
            ...         }
            ...     }
            ... })
            ('(_.age < ? OR (_.status = ? AND _.id >= ?))', [18, 'inactive', 100])
        """
        where_clauses = []
        values = []
        fields = set()

        if not conditions:
            return None, None, None

        for key, value in SQLQueryBuilder._extract_key_value_pairs(conditions):
            # Handle key as `GroupOperator`
            if isinstance(key, GroupOperator) or GroupOperator.is_valid(key):
                sub_where_clause, sub_fields, sub_values = SQLQueryBuilder.build_where_clause(value, group_operator=key)
                where_clauses.append(f"({sub_where_clause})")
                fields.update(sub_fields)
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

            fields.add(key)
            where_clause = f"{SQLQueryBuilder._build_inner_alias(key)} {sql_operator}"
            where_clauses.append(where_clause)

            # Handle special case for IN and NOT IN
            if operator.is_multi_value() or operator.num_values > 1:
                values.extend(value)
            elif operator.requires_value():
                values.append(value)

        where_clauses_str = SQLQueryBuilder._join_where_clauses(where_clauses, group_operator)

        return where_clauses_str, fields, values

    @staticmethod
    def build_order_by_clause(order_by: Dict[str, SortOrder]) -> str:
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
            return

        # Ensure that the input for order_by values are `SortOrder` or strings
        return ", ".join(
            [
                f"{SQLQueryBuilder._build_inner_alias(field)} {str(direction).upper()}"
                for field, direction in order_by.items()
            ]
        )

    @staticmethod
    def build_query(model: str, fields = None, conditions = None, relationships = None, order_by: Optional[Dict[str, SortOrder]] = None, limit: int = None):
        """Constructs a SQL query dynamically based on the given parameters.

        This method builds a `SELECT` query by handling fields, conditions, relationships, 
        ordering, and limit constraints. It also processes indirect relational fields, such as 
        one-to-many relationships.

        Args:
            model (str): The base model (table) from which to query data.
            fields (Optional[List[str]]): A list of fields to retrieve in the `SELECT` clause.
            conditions (Optional[Dict[str, Any]]): A dictionary of filter conditions for the `WHERE` clause.
            relationships (Optional[Dict[str, str]]): A dictionary defining relationships between models.
            order_by (Optional[Dict[str, SortOrder]]): A dictionary specifying sorting order for fields.
            limit (Optional[int]): The maximum number of records to retrieve.

        Returns:
            Tuple[str, List[Any], Dict[str, str]]: A tuple containing:
                - The SQL query string.
                - A list of values for parameterized queries (to prevent SQL injection).
                - A dictionary mapping grouped field aliases.

        Examples:
            >>> SQLQueryBuilder.build_query(
            ...     model="Tasks",
            ...     fields=["id", "name", "status"],
            ...     conditions={"status": "active"},
            ...     relationships={"Tasks.assigned_to": "Users.id"},
            ...     order_by={"created_at": "DESC"},
            ...     limit=10
            ... )
            (
                "SELECT\\n\\tid, name, status\\nFROM\\n\\t'Tasks' AS _\\nWHERE\\n\\tstatus = ?\\nORDER BY\\n\\tcreated_at DESC\\nLIMIT\\n\\t10",
                ['active'],
                {}
            )

            >>> SQLQueryBuilder.build_query(
            ...     model="Users",
            ...     fields=["id", "email"],
            ...     conditions={"role": "admin"},
            ...     limit=5
            ... )
            (
                "SELECT\\n\\tid, email\\nFROM\\n\\t'Users' AS _\\nWHERE\\n\\trole = ?\\nLIMIT\\n\\t5",
                ['admin'],
                {}
            )
        """
        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        select_clause, grouped_field_aliases = SQLQueryBuilder.build_select_clause(fields, relationships, base_model=model)
        where_clause, where_fields, values = SQLQueryBuilder.build_where_clause(conditions)
        fields = list(fields or []) + list(where_fields or [])
        join_clause, group_by_clause = SQLQueryBuilder.build_join_clause(fields, model, relationships)
        order_by_clause = SQLQueryBuilder.build_order_by_clause(order_by)

        query_clauses = [
            f"SELECT\n\t{select_clause}",
            f"FROM\n\t'{model}' AS _",
        ]
        if join_clause:
            query_clauses.append(join_clause)
        if where_clause:
            query_clauses.append(f'WHERE\n\t{where_clause}')
        if group_by_clause:
            query_clauses.append(f'GROUP BY\n\t{group_by_clause}')
        if order_by_clause:
            query_clauses.append(f'ORDER BY\n\t{order_by_clause}')
        if limit:
            query_clauses.append(f'LIMIT\n\t{limit}')

        # NOTE: Handle indirect relational fields, such as one-to-many relationships.
        return '\n'.join(query_clauses), values, grouped_field_aliases

    @staticmethod
    def _extract_key_value_pairs(data: str | Tuple[str, Any] | Dict[str, Any] | Iterable[Any], 
                                 keys_only: bool = False
                                 ) -> Generator[Tuple[str, Any] | str, None, None]:
        """Recursively extracts key-value pairs from various data structures.

        This method supports:
        - Strings (yields the string as both key and value)
        - Tuples of length 2 (yields them as-is)
        - Dictionaries (yields items as key-value pairs)
        - Iterables containing any of the above (recursively processes each element)
        - Optionally, only the keys from the data structures

        Args:
            data: The input data, which can be a string, tuple of two elements,
                  dictionary, or an iterable containing any of these.
            keys_only: If True, only keys will be yielded (ignoring values).

        Yields:
            Tuple[str, Any]: Tuples of (key, value) extracted from the input, or just (key) if keys_only is True.

        Examples:
            >>> list(SQLQueryBuilder._extract_key_value_pairs("status"))
            [('status', 'status')]

            >>> list(SQLQueryBuilder._extract_key_value_pairs(("priority", 1)))
            [('priority', 1)]

            >>> list(SQLQueryBuilder._extract_key_value_pairs({"name": "Alice", "age": 30}))
            [('name', 'Alice'), ('age', 30)]

            >>> list(SQLQueryBuilder._extract_key_value_pairs([("id", 42), {"role": "admin"}]))
            [('id', 42), ('role', 'admin')]

            >>> list(SQLQueryBuilder._extract_key_value_pairs([
            ...     "category",
            ...     ("level", "high"),
            ...     {"status": "active", "rank": 5}
            ... ], keys_only=True))
            ['category', 'level', 'status', 'rank']
        """
        # Handle the simple case where data is a string.
        if isinstance(data, str):
            yield keys_only and data or (data, data)

        # Check early if data is a tuple of length 2.
        elif isinstance(data, tuple) and len(data) == 2:
            yield keys_only and data[0] or data

        # Handle the case where data is a dict.
        elif isinstance(data, dict):
            yield from keys_only and data.keys() or data.items()

        # Otherwise, if it’s an iterable (but not a string), recursively process each element.
        elif isinstance(data, Iterable):
            for item in data:
                yield from SQLQueryBuilder._extract_key_value_pairs(item, keys_only)

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
