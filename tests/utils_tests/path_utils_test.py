import os
import pytest
from blackboard.utils.path_utils import PathUtil  # Adjust the import according to your module setup


# Define a fixture for a sample directory structure
@pytest.fixture(scope="module")
def create_test_directory(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("test_dir")
    (base_dir / "dir1").mkdir()
    (base_dir / "dir1" / "subdir1").mkdir()
    (base_dir / "dir1" / "subdir2").mkdir()
    (base_dir / "dir2").mkdir()
    (base_dir / ".hidden").mkdir()
    (base_dir / "excluded_dir").mkdir()
    return base_dir

def test_return_absolute_paths(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2"), os.path.join(root, "excluded_dir")}
    result = set(PathUtil.traverse_directories_at_level(root, level=1))
    assert result == expected

def test_return_relative_paths(create_test_directory):
    root = str(create_test_directory)
    expected = {"dir1", "dir2", "excluded_dir"}
    result = set(PathUtil.traverse_directories_at_level(root, level=1, is_return_relative=True))
    assert result == expected

def test_skip_hidden(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2"), os.path.join(root, "excluded_dir")}
    result = set(PathUtil.traverse_directories_at_level(root, level=1, is_skip_hidden=True))
    assert result == expected
    assert os.path.join(root, ".hidden") not in result

def test_not_skip_hidden(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2"), os.path.join(root, ".hidden"), os.path.join(root, "excluded_dir")}
    assert set(PathUtil.traverse_directories_at_level(root, level=1, is_skip_hidden=False)) == expected

def test_excluded_folders(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2")}
    result = set(PathUtil.traverse_directories_at_level(root, level=1, excluded_folders=["excluded_dir"]))
    assert result == expected
    assert os.path.join(root, "excluded_dir") not in result

# Run the tests
if __name__ == "__main__":
    pytest.main()
