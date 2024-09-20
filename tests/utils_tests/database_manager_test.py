import pytest
from pathlib import Path
from typing import Generator
from blackboard.utils.database import DatabaseManager

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

    model = db_manager.get_model(table_name)

    table_info = list(model.get_fields().values())
    assert len(table_info) == 2
    assert table_info[0].name == "id"
    assert table_info[0].type == "INTEGER"
    assert table_info[1].name == "name"
    assert table_info[1].type == "TEXT"

def test_create_enum_table(db_manager: DatabaseManager):
    enum_values = ["Pending", "Completed", "Failed"]
    db_manager.create_enum_table("enum_status", enum_values)
    
    stored_values = db_manager.get_enum_values("enum_status")
    assert set(stored_values) == set(enum_values)

def test_add_field(db_manager: DatabaseManager):
    test_model = db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY"})
    test_model.add_field("age", "INTEGER")

    fields = test_model.get_field_names()
    assert "age" in fields

def test_insert_and_retrieve_record(db_manager: DatabaseManager):
    test_model = db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    test_model.insert_record({"name": "Test Name"})

    rows = list(test_model.query())
    assert len(rows) == 1
    assert rows[0][1] == "Test Name"

def test_update_record(db_manager: DatabaseManager):
    # Create a test table and insert a record
    test_model = db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    test_model.insert_record({"name": "Old Name"})

    # Retrieve the inserted record to get the rowid
    rows = list(test_model.query(fields=["rowid", "name"]))
    rowid = rows[0][0]

    # Update the record with a new name
    test_model.update_record({"name": "New Name"}, pk_value=rowid)

    # Query the updated record and verify the update
    updated_rows = list(test_model.query(fields=["name"]))
    assert updated_rows[0][0] == "New Name"

def test_delete_field(db_manager: DatabaseManager):
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT", "age": "INTEGER"})
    model = db_manager.get_model('test_table')
    model.delete_field("age")

    fields = model.get_field_names()
    assert "age" not in fields

def test_delete_table(db_manager: DatabaseManager):
    db_manager.create_table("test_table", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
    db_manager.delete_table("test_table")

    tables = db_manager.get_table_names()
    assert "test_table" not in tables

# def test_create_and_query_many_to_many(db_manager: DatabaseManager):
#     # Create two related models (tables) and a junction table for many-to-many relationship
#     authors_model = db_manager.create_table("authors", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
#     books_model = db_manager.create_table("books", {"id": "INTEGER PRIMARY KEY", "title": "TEXT"})

#     authors_model.add
#     # Create a many-to-many junction table
#     authors_books_model = db_manager.create_junction_table(
#         from_table="authors",
#         to_table="books",
#         from_field="id",
#         to_field="id"
#     )

#     # Insert data into both tables and create many-to-many relationships
#     author_id = authors_model.insert_record({"name": "Author 1"})
#     book_id = books_model.insert_record({"title": "Book 1"})

#     ...
