# Type Checking Imports
# ---------------------
from typing import Generator, List, Tuple, Union, Optional, Dict, Any

# Standard Library Imports
# ------------------------
from dataclasses import dataclass


# Class Definitions
# -----------------
@dataclass
class ForeignKey:
    """Represents a foreign key constraint in a database table.
    """
    constraint_id: int           # Foreign key constraint ID
    sequence: int                # Sequence number within the foreign key
    local_table: str             # The local table name (the table containing the foreign key)
    local_field: str             # The field in the local table (foreign key column)
    referenced_table: str        # The referenced table name
    referenced_field: str        # The field in the referenced table (primary key column)
    on_update: str               # Action on update (e.g., "CASCADE", "RESTRICT", "SET NULL")
    on_delete: str               # Action on delete (e.g., "CASCADE", "RESTRICT", "SET NULL")
    match: str                   # The match type (e.g., "NONE", "PARTIAL", "FULL")

    def get_field_definition(self) -> str:
        """Generate the SQL definition string for this foreign key.
        """
        definition = (f"FOREIGN KEY({self.local_field}) REFERENCES {self.referenced_table}({self.referenced_field}) "
                      f"ON UPDATE {self.on_update} ON DELETE {self.on_delete}")
        if self.match and self.match != 'NONE':
            definition += f" MATCH {self.match}"
        return definition

@dataclass
class ManyToManyField:
    """Represents a many-to-many relationship field.
    """
    track_field_name: str                   # The field name used for display purposes
    local_table: str                        # The originating table name
    remote_table: str                       # The related table name
    junction_table: str                     # The name of the junction table
    local_fk: ForeignKey                    # ForeignKeyInfo for the local table
    remote_fk: ForeignKey                   # ForeignKeyInfo for the remote table

@dataclass
class FieldInfo:
    cid: int = -1
    name: str = ''
    type: str = 'NULL'
    notnull: int = 0
    dflt_value: Optional[str] = None
    pk: int = 0
    is_unique: bool = False
    fk: Optional[ForeignKey] = None
    m2m: Optional[ManyToManyField] = None

    def get_field_definition(self) -> str:
        """Generate the SQL definition string for this field.
        """
        definition = f"{self.name} {self.type}"
        if self.is_not_null:
            definition += " NOT NULL"
        if self.is_primary_key:
            definition += " PRIMARY KEY"
        if self.is_unique:
            definition += " UNIQUE"
        # if self.is_foreign_key:
        #     definition += f", {self.fk.get_field_definition()}"
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
    def is_many_to_many(self) -> bool:
        """Check if the field is part of a many-to-many relationship.
        """
        return self.m2m is not None
