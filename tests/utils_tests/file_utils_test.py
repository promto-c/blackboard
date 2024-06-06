import pytest
from blackboard.utils.file_utils import FileUtils, FilePatternQuery


@pytest.fixture
def create_test_file(tmp_path):
    """Creates a temporary file for testing."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("This is a test file.")
    return test_file


@pytest.mark.parametrize("file_content, expected", [
    ("This is a sample file.", {'file_name': 'sample_file.txt', 'file_extension': 'txt'}),
    ("Example image data.", {'file_name': 'example_image.jpg', 'file_extension': 'jpg'}),
])
def test_extract_file_info_param(tmp_path, file_content, expected):
    """Test for extract_file_info method with different files."""
    temp_file = tmp_path / f"temp.{expected['file_extension']}"
    temp_file.write_text(file_content)

    file_info = FileUtils.extract_file_info(str(temp_file))

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
    assert FileUtils.format_size(size, precision) == expected


@pytest.fixture(scope="module")
def setup_test_directory(tmp_path_factory):
    """Sets up a temporary directory structure for testing."""
    base_dir = tmp_path_factory.mktemp("test_dir")
    (base_dir / "dir1" / "subdir1").mkdir(parents=True)
    (base_dir / "dir1" / "subdir2").mkdir()
    (base_dir / "dir2").mkdir()
    (base_dir / ".hidden").mkdir()
    (base_dir / "excluded_dir").mkdir()

    # Create files in the directory structure
    file1 = base_dir / "dir1" / "subdir1" / "file1.txt"
    file2 = base_dir / "dir1" / "subdir2" / "file2.txt"
    file3 = base_dir / "dir2" / "file3.txt"
    hidden_file = base_dir / ".hidden" / "hidden.txt"
    excluded_file = base_dir / "excluded_dir" / "excluded.txt"
    
    for f in [file1, file2, file3, hidden_file, excluded_file]:
        f.write_text("Sample content")

    return base_dir


def test_file_pattern_query(setup_test_directory):
    """Test for FilePatternQuery class using the directory structure."""
    pattern = str(setup_test_directory / "{dir}/{subdir}/{file_name}")
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


# Run the tests
if __name__ == "__main__":
    pytest.main()
