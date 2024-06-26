# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, Dict, List
if TYPE_CHECKING:
    from numbers import Number

# Standard Library Imports
# ------------------------
import glob, re
from pathlib import Path

# Constant Definitions
# --------------------
PACKAGE_ROOT = Path(__file__).parent.parent


# Class Definitions
# -----------------
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
    
    def get_frame_path(self, frame_number: 'Number'):
        return f'{self.name_part}.{int(frame_number):0{self.padding_length}}.{self.extension}'

    def __str__(self):
        return f"Name Part: {self.name_part}, Frame Padding: {self.frame_padding} (Length: {self.padding_length}), Extension: {self.extension}"

class PathPattern:
    """A utility class for handling and manipulating file path patterns with named placeholders.
    """

    # Define regex pattern for variable placeholders
    VARIABLE_PLACEHOLDER_PATTERN = r'\{(\w+)\}'

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
        formatted_pattern = re.sub(PathPattern.VARIABLE_PLACEHOLDER_PATTERN, '{}', pattern)
        
        # Use str.format with the modified pattern
        return formatted_pattern.format(*values)

    @staticmethod
    def convert_pattern_to_regex(pattern: str) -> str:
        """Converts a string pattern with variables in curly braces to a regex pattern that captures across directory names.

        Args:
            pattern (str): A string containing the pattern, with variables enclosed in curly braces.

        Returns:
            str: The converted regular expression pattern.

        Examples:
            >>> PathPattern.convert_pattern_to_regex("path/to/{var1}/and/{var2}/")
            'path/to/(?P<var1>.*?)/and/(?P<var2>.*?)/'
        """
        # Escape all regex characters except for the curly braces which are used for variables
        pattern = re.escape(pattern).replace(r'\{', '{').replace(r'\}', '}')
        # Use a non-greedy match up to the next literal slash or end of string, which allows variable capture over multiple segments
        regex_pattern = re.sub(PathPattern.VARIABLE_PLACEHOLDER_PATTERN, r'(?P<\1>.*?)', pattern)

        return regex_pattern

    @staticmethod
    def extract_variables(pattern: str, path: str, is_regex: bool = False) -> Dict[str, str]:
        """Extracts variables from a given path based on a specified pattern.

        Args:
            pattern (str): The pattern as a string with variables in curly braces or a regex pattern.
            path (str): The path string from which to extract variable values.
            is_regex (bool): Boolean flag to indicate if the pattern is a regex.

        Returns:
            Dict[str, str]: A dictionary of variable names and their corresponding values if the path matches the pattern,
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
            >>> PathPattern.extract_variables(r'path/to/(?P<var1>\w+)/and/(?P<var2>\w+)/', "path/to/value1/and/value2/", is_regex=True)
            {'var1': 'value1', 'var2': 'value2'}
        """
        # Convert the pattern to a regex pattern if not already a regex
        regex_pattern = pattern if is_regex else PathPattern.convert_pattern_to_regex(pattern)

        # Match the regex pattern against the provided path
        match = re.match(regex_pattern, path)
        if match:
            return match.groupdict()
        return {}

    @staticmethod
    def extract_variable_names(pattern: str) -> List[str]:
        """Extract only the variable names from the pattern, excluding the static parts.

        Args:
            pattern (str): The string pattern with variables in curly braces.

        Returns:
            List[str]: A list of variable names.

        Examples:
            >>> PathPattern.extract_variable_names("blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files")
            ['project_name', 'sequence_name', 'shot_name']
            >>> PathPattern.extract_variable_names("{var1}/static/{var2}/end")
            ['var1', 'var2']
            >>> PathPattern.extract_variable_names("no/dynamic/parts")
            []
        """
        return re.findall(PathPattern.VARIABLE_PLACEHOLDER_PATTERN, pattern)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
