import pytest
from pathlib import Path
from typing import Generator
from blackboard.utils.database_manager import DatabaseManager

@pytest.fixture(scope="function")
def db_manager(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """Fixture to create a temporary database manager instance for testing."""
    db_path = tmp_path / "test_database.db"
    manager = DatabaseManager(str(db_path))
    yield manager
    manager.connection.close()

def test_create_table(db_manager: DatabaseManager):
    table_name = "test_table"
    fields = {"id": "INTEGER PRIMARY KEY", "name": "TEXT NOT NULL"}
    db_manager.create_table(table_name, fields)

    table_info = list(db_manager.get_table_info(table_name).values())
    assert len(table_info) == 2
    assert table_info[0].name == "id"
    assert table_info[1].name == "name"

def test_add_enum_metadata(db_manager: DatabaseManager):
    db_manager.add_enum_metadata("test_table", "status", "enum_status")

    db_manager.cursor.execute("SELECT * FROM _meta_enum_field WHERE table_name='test_table'")
    result = db_manager.cursor.fetchone()

    assert result is not None
    assert result[0] == "test_table"
    assert result[1] == "status"
    assert result[2] == "enum_status"

def test_create_enum_table(db_manager: DatabaseManager):
    enum_values = ["Pending", "Completed", "Failed"]
    db_manager.create_enum_table("enum_status", enum_values)
    
    stored_values = db_manager.get_enum_values("enum_status")
    assert set(stored_values) == set(enum_values)

def test_add_field(db_manager: DatabaseManager):
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY"})
    db_manager.add_field("test_table", "age", "INTEGER")

    fields = db_manager.get_field_names("test_table")
    assert "age" in fields

def test_insert_and_retrieve_record(db_manager: DatabaseManager):
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    db_manager.insert_record("test_table", {"name": "Test Name"})

    rows = list(db_manager.query_table_data("test_table"))
    assert len(rows) == 1
    assert rows[0][1] == "Test Name"

def test_update_record(db_manager: DatabaseManager):
    # Create a test table and insert a record
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    db_manager.insert_record("test_table", {"name": "Old Name"})

    # Retrieve the inserted record to get the rowid
    rows = list(db_manager.query_table_data("test_table", fields=["rowid", "name"]))
    rowid = rows[0][0]

    # Update the record with a new name
    db_manager.update_record("test_table", {"name": "New Name"}, pk_value=rowid)

    # Query the updated record and verify the update
    updated_rows = list(db_manager.query_table_data("test_table", fields=["name"]))
    assert updated_rows[0][0] == "New Name"

def test_delete_field(db_manager: DatabaseManager):
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT", "age": "INTEGER"})
    db_manager.delete_field("test_table", "age")

    fields = db_manager.get_field_names("test_table")
    assert "age" not in fields

def test_delete_table(db_manager: DatabaseManager):
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    db_manager.delete_table("test_table")

    tables = db_manager.get_table_names()
    assert "test_table" not in tables
