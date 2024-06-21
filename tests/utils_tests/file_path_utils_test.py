import os
import pytest
from blackboard.utils.file_path_utils import FileUtil, FilePatternQuery, FilePathWalker


# Define a fixture for a sample directory structure
@pytest.fixture(scope="module")
def setup_test_directory(tmp_path_factory):
    root = tmp_path_factory.mktemp("test_dir")
    (root / "file1.txt").write_text("File 1 content")
    (root / "file2.log").write_text("File 2 content")
    (root / "dir1").mkdir()
    (root / "dir1" / "file3.txt").write_text("File 3 content")
    (root / "dir1" / "file4.log").write_text("File 4 content")
    (root / "dir1" / "subdir1").mkdir()
    (root / "dir1" / "subdir2").mkdir()
    (root / "dir1" / "subdir1" / "file1.txt").write_text("File 1 content")
    (root / "dir2").mkdir()
    (root / "dir2" / "file5.txt").write_text("File 5 content")
    (root / "dir2" / "file6.log").write_text("File 6 content")
    (root / "dir2" / "dir3").mkdir()
    (root / "dir2" / "dir3" / "file7.txt").write_text("File 7 content")
    (root / "excluded_dir").mkdir()
    (root / ".hidden").mkdir()
    (root / ".hidden_file.txt").write_text("Hidden file content")

    # Create some files that follow the sequence pattern
    for i in range(1, 6):
        (root / f"image.{i:04d}.jpg").write_text(f"Image {i} content")

    return root

class TestFilePathWalker:

    def test_traverse_files_no_sequence(self, setup_test_directory):
        root = setup_test_directory
        expected_files = [
            str(root / "file1.txt"),
            str(root / "file2.log"),
            str(root / "dir1" / "file3.txt"),
            str(root / "dir1" / "file4.log"),
            str(root / "dir1" / "subdir1" / "file1.txt"),
            str(root / "dir2" / "file5.txt"),
            str(root / "dir2" / "file6.log"),
            str(root / "dir2" / "dir3" / "file7.txt"),
            str(root / "image.0001.jpg"),
            str(root / "image.0002.jpg"),
            str(root / "image.0003.jpg"),
            str(root / "image.0004.jpg"),
            str(root / "image.0005.jpg")
        ]

        result_files = list(FilePathWalker.traverse_files(root, use_sequence_format=False))
        assert sorted(result_files) == sorted(expected_files)

    def test_traverse_files_with_sequence(self, setup_test_directory):
        root = setup_test_directory
        expected_files = [
            str(root / "file1.txt"),
            str(root / "file2.log"),
            str(root / "dir1" / "file3.txt"),
            str(root / "dir1" / "file4.log"),
            str(root / "dir1" / "subdir1" / "file1.txt"),
            str(root / "dir2" / "file5.txt"),
            str(root / "dir2" / "file6.log"),
            str(root / "dir2" / "dir3" / "file7.txt"),
            str(root / "image.####.jpg")
        ]

        result_files = list(FilePathWalker.traverse_files(root, use_sequence_format=True))
        assert sorted(result_files) == sorted(expected_files)

    def test_traverse_files_excluded_extensions(self, setup_test_directory):
        root = setup_test_directory
        expected_files = [
            str(root / "file1.txt"),
            str(root / "dir1" / "file3.txt"),
            str(root / "dir2" / "file5.txt"),
            str(root / "dir1" / "subdir1" / "file1.txt"),
            str(root / "dir2" / "dir3" / "file7.txt"),
            str(root / "image.0001.jpg"),
            str(root / "image.0002.jpg"),
            str(root / "image.0003.jpg"),
            str(root / "image.0004.jpg"),
            str(root / "image.0005.jpg"),
        ]

        result_files = list(FilePathWalker.traverse_files(root, excluded_extensions=["log"], use_sequence_format=False))
        assert sorted(result_files) == sorted(expected_files)

    def test_traverse_files_excluded_folders(self, setup_test_directory):
        root = setup_test_directory
        expected_files = [
            str(root / "file1.txt"),
            str(root / "file2.log"),
            str(root / "image.0001.jpg"),
            str(root / "image.0002.jpg"),
            str(root / "image.0003.jpg"),
            str(root / "image.0004.jpg"),
            str(root / "image.0005.jpg")
        ]

        result_files = list(FilePathWalker.traverse_files(root, excluded_folders=["dir1", "dir2"], use_sequence_format=False))
        assert sorted(result_files) == sorted(expected_files)

    def test_traverse_files_skip_hidden(self, setup_test_directory):
        root = setup_test_directory
        hidden_file = root / ".hidden_file.txt"
        hidden_file.write_text("Hidden file content")
        expected_files = [
            str(root / "file1.txt"),
            str(root / "file2.log"),
            str(root / "dir1" / "file3.txt"),
            str(root / "dir1" / "file4.log"),
            str(root / "dir1" / "subdir1" / "file1.txt"),
            str(root / "dir2" / "file5.txt"),
            str(root / "dir2" / "file6.log"),
            str(root / "dir2" / "dir3" / "file7.txt"),
            str(root / "image.0001.jpg"),
            str(root / "image.0002.jpg"),
            str(root / "image.0003.jpg"),
            str(root / "image.0004.jpg"),
            str(root / "image.0005.jpg")
        ]

        result_files = list(FilePathWalker.traverse_files(root, is_skip_hidden=True, use_sequence_format=False))
        assert sorted(result_files) == sorted(expected_files)

        result_files_with_hidden = list(FilePathWalker.traverse_files(root, is_skip_hidden=False, use_sequence_format=False))
        assert sorted(result_files_with_hidden) == sorted(expected_files + [str(hidden_file)])

    def test_return_absolute_paths(self, setup_test_directory):
        root = setup_test_directory
        expected = {str(root / "dir1"), str(root / "dir2"), str(root / "excluded_dir")}
        result = set(FilePathWalker.traverse_directories(root, target_depth=1))
        assert result == expected

    def test_return_relative_paths(self, setup_test_directory):
        root = str(setup_test_directory)
        expected = {"dir1", "dir2", "excluded_dir"}
        result = set(FilePathWalker.traverse_directories(root, target_depth=1, is_return_relative=True))
        assert result == expected

    def test_skip_hidden_directories(self, setup_test_directory):
        root = setup_test_directory
        expected = {str(root / "dir1"), str(root / "dir2"), str(root / "excluded_dir")}
        result = set(FilePathWalker.traverse_directories(root, target_depth=1, is_skip_hidden=True))
        assert result == expected
        assert str(root / ".hidden") not in result

    def test_not_skip_hidden_directories(self, setup_test_directory):
        root = setup_test_directory
        expected = {str(root / "dir1"), str(root / "dir2"), str(root / ".hidden"), str(root / "excluded_dir")}
        assert set(FilePathWalker.traverse_directories(root, target_depth=1, is_skip_hidden=False)) == expected

    def test_excluded_folders_directories(self, setup_test_directory):
        root = setup_test_directory
        expected = {str(root / "dir1"), str(root / "dir2")}
        result = set(FilePathWalker.traverse_directories(root, target_depth=1, excluded_folders=["excluded_dir"]))
        assert result == expected
        assert str(root / "excluded_dir") not in result

    def test_traverse_all_levels(self, setup_test_directory):
        root = setup_test_directory
        expected = {
            str(root / "dir1"),
            str(root / "dir1" / "subdir1"),
            str(root / "dir1" / "subdir2"),
            str(root / "dir2"),
            str(root / "dir2" / "dir3"),
            str(root / "excluded_dir")
        }
        result = set(FilePathWalker.traverse_directories(root))
        assert result == expected

class TestFileUtil:

    @pytest.mark.parametrize("file_content, expected", [
        ("This is a sample file.", {'file_name': 'temp.txt', 'file_extension': 'txt'}),
        ("Example image data.", {'file_name': 'temp.jpg', 'file_extension': 'jpg'}),
    ])
    def test_extract_file_info_param(self, setup_test_directory, file_content, expected):
        """Test for extract_file_info method with different files."""
        temp_file = setup_test_directory / f"temp.{expected['file_extension']}"
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
    def test_format_size_param(self, size, precision, expected):
        """Test for format_size method with different sizes and precisions."""
        assert FileUtil.format_size(size, precision) == expected

class TestFilePatternQuery:

    def test_file_pattern_query(self, setup_test_directory):
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
        expected_path = os.path.join('dir1', 'subdir1', 'file1.txt')
        assert result['file_path'].endswith(expected_path)


# Run the tests
if __name__ == "__main__":
    pytest.main()
