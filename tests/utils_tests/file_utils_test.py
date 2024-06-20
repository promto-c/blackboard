import os
import pytest
from blackboard.utils.file_utils import FileUtil, FilePatternQuery, FilePathWalker


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
    (base_dir / "file1.txt").write_text("content")
    (base_dir / "file2.log").write_text("content")
    (base_dir / ".hidden_file").write_text("content")
    (base_dir / "dir1" / "file3.txt").write_text("content")
    (base_dir / "dir2" / "file4.log").write_text("content")
    (base_dir / "dir1" / "subdir1" / "file1.txt").write_text("content")
    return base_dir

def test_traverse_files_absolute(create_test_directory):
    root = str(create_test_directory)
    expected = {
        os.path.join(root, "file1.txt"),
        os.path.join(root, "file2.log"),
        os.path.join(root, "dir1", "file3.txt"),
        os.path.join(root, "dir2", "file4.log"),
        os.path.join(root, "dir1", "subdir1", "file1.txt"),
    }
    result = set(FilePathWalker.traverse_files(root))
    assert result == expected

def test_traverse_files_relative(create_test_directory):
    root = str(create_test_directory)
    expected = {
        "file1.txt",
        "file2.log",
        os.path.join("dir1", "file3.txt"),
        os.path.join("dir2", "file4.log"),
        os.path.join("dir1", "subdir1", "file1.txt"),
    }
    result = set(FilePathWalker.traverse_files(root, is_return_relative=True))
    assert result == expected

def test_traverse_files_skip_hidden(create_test_directory):
    root = str(create_test_directory)
    expected = {
        os.path.join(root, "file1.txt"),
        os.path.join(root, "file2.log"),
        os.path.join(root, "dir1", "file3.txt"),
        os.path.join(root, "dir2", "file4.log"),
        os.path.join(root, "dir1", "subdir1", "file1.txt"),
    }
    result = set(FilePathWalker.traverse_files(root, is_skip_hidden=True))
    assert result == expected
    assert os.path.join(root, ".hidden_file") not in result

def test_traverse_files_excluded_extensions(create_test_directory):
    root = str(create_test_directory)
    expected = {
        os.path.join(root, "file1.txt"),
        os.path.join(root, "dir1", "file3.txt"),
        os.path.join(root, "dir1", "subdir1", "file1.txt"),
    }
    result = set(FilePathWalker.traverse_files(root, excluded_extensions=[".log"]))
    assert result == expected
    assert os.path.join(root, "file2.log") not in result
    assert os.path.join(root, "dir2", "file4.log") not in result

@pytest.mark.parametrize("file_content, expected", [
    ("This is a sample file.", {'file_name': 'sample_file.txt', 'file_extension': 'txt'}),
    ("Example image data.", {'file_name': 'example_image.jpg', 'file_extension': 'jpg'}),
])
def test_extract_file_info_param(create_test_directory, file_content, expected):
    """Test for extract_file_info method with different files."""
    temp_file = create_test_directory / f"temp.{expected['file_extension']}"
    temp_file.write_text(file_content)

    file_info = FileUtil.extract_file_info(str(temp_file))

    assert file_info['file_name'] == temp_file.name
    assert file_info['file_extension'] == expected['file_extension']
    assert 'file_size' in file_info
    assert 'last_modified' in file_info
    assert 'file_owner' in file_info
    assert file_info['file_path'] == str(temp_file)

@pytest.mark.parametrize("size, precision, expected", [
    (1023, 2, '1023 bytes'),
    (1024, 2, '1.00 kB'),
    (1048576, 1, '1.0 MB'),
    (1073741824, 3, '1.000 GB'),
])
def test_format_size_param(size, precision, expected):
    """Test for format_size method with different sizes and precisions."""
    assert FileUtil.format_size(size, precision) == expected

def test_file_pattern_query(create_test_directory):
    """Test for FilePatternQuery class using the directory structure."""
    pattern = str(create_test_directory / "{dir}/{subdir}/{file_name}")
    fpq = FilePatternQuery(pattern)

    filters = {'dir': ['dir1'], 'subdir': ['subdir1'], 'file_name': ['file1.txt']}
    results = list(fpq.query_files(filters))

    assert len(results) == 1
    result = results[0]
    assert result['file_name'] == 'file1.txt'
    assert result['file_extension'] == 'txt'
    assert 'file_size' in result
    assert 'last_modified' in result
    assert 'file_owner' in result
    assert result['file_path'].endswith('dir1/subdir1/file1.txt')

def test_return_absolute_paths(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2"), os.path.join(root, "excluded_dir")}
    result = set(FilePathWalker.traverse_directories(root, target_depth=1))
    assert result == expected

def test_return_relative_paths(create_test_directory):
    root = str(create_test_directory)
    expected = {"dir1", "dir2", "excluded_dir"}
    result = set(FilePathWalker.traverse_directories(root, target_depth=1, is_return_relative=True))
    assert result == expected

def test_skip_hidden(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2"), os.path.join(root, "excluded_dir")}
    result = set(FilePathWalker.traverse_directories(root, target_depth=1, is_skip_hidden=True))
    assert result == expected
    assert os.path.join(root, ".hidden") not in result

def test_not_skip_hidden(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2"), os.path.join(root, ".hidden"), os.path.join(root, "excluded_dir")}
    assert set(FilePathWalker.traverse_directories(root, target_depth=1, is_skip_hidden=False)) == expected

def test_excluded_folders(create_test_directory):
    root = str(create_test_directory)
    expected = {os.path.join(root, "dir1"), os.path.join(root, "dir2")}
    result = set(FilePathWalker.traverse_directories(root, target_depth=1, excluded_folders=["excluded_dir"]))
    assert result == expected
    assert os.path.join(root, "excluded_dir") not in result

def test_traverse_all_levels(create_test_directory):
    root = str(create_test_directory)
    expected = {
        os.path.join(root, "dir1"),
        os.path.join(root, "dir1", "subdir1"),
        os.path.join(root, "dir1", "subdir2"),
        os.path.join(root, "dir2"),
        os.path.join(root, "excluded_dir")
    }
    result = set(FilePathWalker.traverse_directories(root))
    assert result == expected


# Run the tests
if __name__ == "__main__":
    pytest.main()
