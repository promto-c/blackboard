import pytest
from blackboard.utils.path_utils import PathSequence, PathPattern
from pathlib import Path


@pytest.fixture
def create_test_sequence_files(tmp_path):
    base_dir = tmp_path / "sequence"
    base_dir.mkdir()
    for i in range(1, 11):
        (base_dir / f"frame.{str(i).zfill(4)}.exr").write_text("content")
    return base_dir

def test_path_sequence_get_frame_range(create_test_sequence_files):
    path = str(create_test_sequence_files / "frame.####.exr")
    ps = PathSequence(path)
    assert ps.get_frame_range() == (1, 10)

def test_path_sequence_get_frame_count_from_range(create_test_sequence_files):
    path = str(create_test_sequence_files / "frame.####.exr")
    ps = PathSequence(path)
    assert ps.get_frame_count_from_range() == 10

def test_path_sequence_get_frame_path(create_test_sequence_files):
    path = str(create_test_sequence_files / "frame.####.exr")
    ps = PathSequence(path)
    assert ps.get_frame_path(5) == str(create_test_sequence_files / "frame.0005.exr")

@pytest.mark.parametrize("pattern, values, expected", [
    ("File {name} has size {size} bytes.", ["example.txt", "1024"], "File example.txt has size 1024 bytes."),
    ("No placeholders here!", [], "No placeholders here!"),
    ("{first} {second} {third}", ["1", "2", "3"], "1 2 3")
])
def test_format_by_index(pattern, values, expected):
    assert PathPattern.format_by_index(pattern, values) == expected

@pytest.mark.parametrize("pattern, expected", [
    ("path/to/{var1}/and/{var2}/", "path/to/(?P<var1>.*?)/and/(?P<var2>.*?)/"),
    ("projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files", 
     "projects/(?P<project_name>.*?)/seq_(?P<sequence_name>.*?)/(?P<shot_name>.*?)/work_files")
])
def test_convert_pattern_to_regex(pattern, expected):
    assert PathPattern.convert_pattern_to_regex(pattern) == expected

@pytest.mark.parametrize("pattern, path, is_regex, expected", [
    ("path/to/{var1}/and/{var2}/", "path/to/value1/and/value2/", False, {'var1': 'value1', 'var2': 'value2'}),
    ("projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files", 
     "projects/ProjectB/seq_seq01/shot03/work_files/texture.png", False,
     {'project_name': 'ProjectB', 'sequence_name': 'seq01', 'shot_name': 'shot03'}),
    (r"path/to/(?P<var1>\w+)/and/(?P<var2>\w+)/", "path/to/value1/and/value2/", True, {'var1': 'value1', 'var2': 'value2'})
])
def test_extract_variables(pattern, path, is_regex, expected):
    assert PathPattern.extract_variables(pattern, path, is_regex) == expected

@pytest.mark.parametrize("pattern, expected", [
    ("blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files", 
     ['project_name', 'sequence_name', 'shot_name']),
    ("{var1}/static/{var2}/end", ['var1', 'var2']),
    ("no/dynamic/parts", [])
])
def test_extract_variable_names(pattern, expected):
    assert PathPattern.extract_variable_names(pattern) == expected


# Run the tests
if __name__ == "__main__":
    pytest.main()
