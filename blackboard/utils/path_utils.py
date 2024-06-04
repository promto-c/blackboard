from typing import Dict, List, Generator, Optional
import glob, re, os
from pathlib import Path
from numbers import Number

PACKAGE_ROOT = Path(__file__).parent.parent

class PathUtil:

    @staticmethod
    def traverse_directories(root: str, target_depth: Optional[int] = None, is_skip_hidden: bool = True,
                             is_return_relative: bool = False, excluded_folders: List[str] = list(),
                            ) -> Generator[str, None, None]:
        """Traverse directory paths from a root directory, optionally returning relative paths.

        If a target_depth is specified, only directories at that depth are yielded.

        Args:
            root (str): A string specifying the root directory path.
            target_depth (Optional[int]): An optional integer specifying the target depth to yield directories from.
                   If not specified, all directories are yielded.
            is_skip_hidden (bool): A boolean indicating whether to skip hidden directories (those starting with '.').
            is_return_relative (bool): A boolean indicating whether to return relative paths instead of absolute paths.
            excluded_folders (List[str]): A list of folder names to be excluded from the traversal.

        Yields:
            Generator[str, None, None]: Directory paths from the root, either absolute or relative.
            If target_depth is specified, only directories at that depth are yielded.
        """
        # Normalize the root directory path to ensure a consistent format
        root = os.path.normpath(root)

        def _traverse(directory: str, current_depth: int = 0) -> Generator[str, None, None]:
            """Helper function to recursively traverse directories.

            Args:
                directory (str): The current directory path.
                current_depth (int): The current depth level of traversal.

            Yields:
                Generator[str, None, None]: Directory paths based on the specified criteria.
            """
            # Determine the path to yield (relative or absolute)
            path = directory[len(root) + 1:] if is_return_relative else directory

            # Check if the current depth matches the target depth
            if target_depth is None and current_depth:
                yield path
            elif current_depth == target_depth:
                yield path
                return

            # Check if the directory can be accessed, skip if not 
            if not os.access(directory, os.R_OK):
                return

            # Continue traversal for subdirectories
            for entry in os.scandir(directory):
                # Skip non-directories, hidden directories, and excluded folders
                if not entry.is_dir() or (is_skip_hidden and entry.name.startswith('.')) or entry.name in excluded_folders:
                    continue

                yield from _traverse(entry.path, current_depth + 1)

        yield from _traverse(root)

class PathSequence:
    def __init__(self, path: str):
        self.path = str(path)
        self.name_part, self.frame_padding, self.extension = self._extract_components()
        self.padding_length = len(self.frame_padding)

    def _extract_components(self):
        return self.path.rsplit('.', 2)

    def get_frame_range(self):
        # Use glob to get all matching filenames
        matching_files = sorted(glob.glob(self.path.replace("#", "*")))

        if not matching_files:
            return None, None

        # Extracting frame numbers from the first and last filenames
        first_frame = int(matching_files[0].split('.')[-2])
        last_frame = int(matching_files[-1].split('.')[-2])
        
        return first_frame, last_frame
    
    def get_frame_count_from_range(self):
        first_frame, last_frame = self.get_frame_range()
        
        if first_frame is None or last_frame is None:
            return 0
        
        return last_frame - first_frame + 1
    
    def get_frame_path(self, frame_number: Number):
        return f'{self.name_part}.{int(frame_number):0{self.padding_length}}.{self.extension}'

    def __str__(self):
        return f"Name Part: {self.name_part}, Frame Padding: {self.frame_padding} (Length: {self.padding_length}), Extension: {self.extension}"

class PathPattern:

    @staticmethod
    def format_by_index(pattern: str, values: List[str]) -> str:
        """Formats a string with named placeholders using indexed arguments by replacing all named placeholders with '{}'.
        
        Args:
            pattern (str): The string pattern with named placeholders.
            values (List[str]): Arguments to fill the placeholders, provided by index.
        
        Returns:
            str: The formatted string.
        
        Examples:
            >>> PathPattern.format_by_index("File {name} has size {size} bytes.", ["example.txt", "1024"])
            'File example.txt has size 1024 bytes.'
            >>> PathPattern.format_by_index("No placeholders here!", [])
            'No placeholders here!'
            >>> PathPattern.format_by_index("{first} {second} {third}", ["1", "2", "3"])
            '1 2 3'
        """
        # Replace all named placeholders with '{}' in one go
        new_pattern = re.sub(r'\{\w+\}', '{}', pattern)
        
        # Use str.format with the modified pattern
        return new_pattern.format(*values)

    @staticmethod
    def convert_pattern_to_regex(string_pattern: str) -> str:
        """Converts a string pattern with variables in curly braces to a regex pattern that captures across directory names.

        Args:
            string_pattern: A string containing the pattern, with variables enclosed in curly braces.

        Returns:
            A string representing the converted regular expression pattern.

        Examples:
            >>> PathPattern.convert_pattern_to_regex("path/to/{var1}/and/{var2}/")
            'path/to/(?P<var1>.*?)/and/(?P<var2>.*?)/'
        """
        # Escape all regex characters except for the curly braces which are used for variables
        string_pattern = re.escape(string_pattern).replace(r'\{', '{').replace(r'\}', '}')
        # # Use a non-greedy match up to the next literal slash or end of string, which allows variable capture over multiple segments
        regex_pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>.*?)', string_pattern)

        return regex_pattern

    @classmethod
    def extract_variables(cls, string_pattern: str, path: str) -> Dict[str, str]:
        """Extracts variables from a given path based on a specified string pattern.

        Args:
            string_pattern: The pattern as a string with variables in curly braces.
            path: The path string from which to extract variable values.

        Returns:
            A dictionary of variable names and their corresponding values if the path matches the pattern,
            or an empty dictionary if there is no match.

        Examples:
            >>> PathPattern.extract_variables("path/to/{var1}/and/{var2}/", "path/to/value1/and/value2/")
            {'var1': 'value1', 'var2': 'value2'}
            >>> PathPattern.extract_variables("projects\{project_name}\seq_{sequence_name}\{shot_name}\work_files",
            ...                               "projects\ProjectB\seq_seq01\shot03\work_files\texture.png")
            {'project_name': 'ProjectB', 'sequence_name': 'seq01', 'shot_name': 'shot03'}
            >>> PathPattern.extract_variables("projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files",
            ...                               "projects/ProjectB/seq_seq02/shot04/01/work_files/texture.png")
            {'project_name': 'ProjectB', 'sequence_name': 'seq02', 'shot_name': 'shot04/01'}
        """
        regex_pattern = cls.convert_pattern_to_regex(string_pattern)
        match = re.match(regex_pattern, path)
        if match:
            return match.groupdict()
        return {}

    @staticmethod
    def extract_variable_names(pattern: str) -> List[str]:
        """Extract only the variable names from the pattern, excluding the static parts.

        >>> PathPattern.extract_variable_names("blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files")
        ['project_name', 'sequence_name', 'shot_name']
        
        >>> PathPattern.extract_variable_names("{var1}/static/{var2}/end")
        ['var1', 'var2']
        
        >>> PathPattern.extract_variable_names("no/dynamic/parts")
        []
        """
        return re.findall(r'\{(\w+)\}', pattern)


if __name__ == '__main__':
    import doctest
    doctest.testmod()

    path = 'example_exr_plates\C0653.####.exr'
    path_sequence = PathSequence(path)

    print(path_sequence.get_frame_range())
    print(path_sequence.padding_length)

    from pprint import pprint
    pprint(PathPattern.extract_variables(
        "projects/{project_name}/seq_{sequence_name}/shot/{shot_name}/work_files", 
        "projects/ProjectB/seq_seq01/test/shot/shot03/work_files/texture.png"
    ))

    # {'project_name': 'ProjectB', 'sequence_name': 'seq01/test', 'shot_name': 'shot03'}