
# Type Checking Imports
# ---------------------
from typing import Dict, List, Generator

# Standard Library Imports
# ------------------------
import re, glob, os, pwd, datetime
from pathlib import Path
from itertools import product

# Local Imports
# -------------
from blackboard.utils.path_utils import PathPattern


# Class Definitions
# -----------------
class FileUtils:
    """Utilities for working with files.
    """
    # Units for formatting file sizes
    UNITS = ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB']
    FILE_INFO_FIELDS = ['file_name', 'file_path', 'file_size', 'file_extension', 'last_modified', 'file_owner']

    @staticmethod
    def extract_file_info(file_path: str) -> Dict[str, str]:
        """Extracts detailed information about a file.

        Args:
            file_path (str): The path to the file for which information is to be extracted.

        Returns:
            Dict[str, str]: A dictionary containing detailed file information, including:
                - file_name: The base name of the file.
                - file_path: The full path to the file.
                - file_size: The size of the file in a human-readable format.
                - file_extension: The file extension.
                - last_modified: The last modification timestamp in ISO 8601 format.
                - file_owner: The owner of the file.
        """
        # Retrieve file statistics and details: file info, owner, last modified time, extension, and formatted size
        file_info = os.stat(file_path)
        owner = pwd.getpwuid(file_info.st_uid).pw_name
        modified_time = datetime.datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')
        extension = file_path.rsplit('.', 1)[-1] if '.' in file_path else ''
        readable_size = FileUtils.format_size(file_info.st_size)
        
        # Compile the file details into a dictionary
        details = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "file_size": readable_size,
            "file_extension": extension,
            "last_modified": modified_time,
            "file_owner": owner,
        }
        
        return details

    @staticmethod
    def format_size(size: int, precision: int = 2) -> str:
        """Converts a file size to a human-readable form with adjustable precision.

        Args:
            size (int): The size of the file in bytes.
            precision (int, optional): The number of decimal places for the formatted size. Defaults to 2.

        Returns:
            str: The size of the file in a human-readable format, such as '1.23 MB'.
        """
        # Loop through each unit until the size is smaller than 1024
        for unit in FileUtils.UNITS:
            if size < 1024:
                # Use the appropriate format string based on the unit
                format_str = f"{{:.{precision}f}} {unit}" if unit != 'bytes' else f"{{:.0f}} {unit}"
                return format_str.format(size)
            
            # Divide the size by 1024 to move to the next unit
            size /= 1024
        
        # Handle extremely large sizes that exceed petabytes
        return f"{size:.{precision}f} PB"

class FilePatternQuery:
    """Queries files matching a specified pattern.
    """

    def __init__(self, pattern: str) -> None:
        """Initializes a FilePatternQuery instance.

        Args:
            pattern (str): The pattern to match files with.
        """
        self.pattern = os.path.normpath(pattern) + '/'
        self.regex_pattern = PathPattern.convert_pattern_to_regex(self.pattern)
        self.fields = PathPattern.extract_variable_names(self.pattern) + FileUtils.FILE_INFO_FIELDS

    def format_for_recursive_glob(self, values: List[str]) -> str:
        """Formats a string with named placeholders for use with glob.iglob, including adding '**' at the end for recursive searches.
        
        Args:
            values (List[str]): Arguments to fill the placeholders, provided by index.
        
        Returns:
            str: The formatted string prepared for recursive glob search.
        """
        # Use str.format with the modified pattern
        return PathPattern.format_by_index(self.pattern, values) + '/**'

    def extract_variables(self, path: str) -> Dict[str, str]:
        """Extracts variables from a given path based on a specified string pattern.

        Args:
            string_pattern: The pattern as a string with variables in curly braces.
            path: The path string from which to extract variable values.

        Returns:
            A dictionary of variable names and their corresponding values if the path matches the pattern,
            or an empty dictionary if there is no match.
        """
        match = re.match(self.regex_pattern, path)
        if match:
            return match.groupdict()
        return {}

    def construct_search_paths(self, filters: Dict[str, List[str]]) -> Generator[str, None, None]:
        """Constructs and yields search paths based on provided filters and the pattern.

        Args:
            filters (Dict[str, List[str]]): A dictionary where keys are field names extracted
                                            from the pattern, and values are lists of strings
                                            that specify the filter values for each field.

        Yields:
            Generator[str, None, None]: Paths to files that match the constructed search patterns.
        """
        # Construct combinations using specific filter values or wildcard '*' for each field
        values_combinations = [filters[field] if field in filters and filters[field] else ['*'] for field in self.fields]

        # Generate all possible paths based on combinations of field values
        all_value_combinations = product(*values_combinations)
        # Using map to apply format_for_recursive_glob for each combination of values
        search_paths = map(self.format_for_recursive_glob, all_value_combinations)

        for search_path in search_paths:
            # Find and yield file paths matching the pattern using recursive glob
            yield from glob.iglob(search_path, recursive=True)

    def query_files(self, filters: Dict[str, List[str]] = dict()) -> Generator[Dict[str, str], None, None]:
        """Queries files matching the pattern and filters, returning their info.

        Args:
            filters (Dict[str, List[str]]): Filters for querying files.

        Returns:
            Generator[Dict[str, str], None, None]: File information for each matching file.
        """
        # Construct search paths based on the filters
        paths = self.construct_search_paths(filters)

        # Iterate over the paths and extract file information
        for path in paths:
            path = os.path.normpath(path)
            if not os.path.isfile(path):
                continue

            # Extract file metadata using FileUtils
            file_info = FileUtils.extract_file_info(path)

            # Extract variables from the path based on the pattern
            data_dict = self.extract_variables(path)
            # Merge file info into the data dictionary
            data_dict.update(file_info)

            yield data_dict


if __name__ == '__main__':
    from pprint import pprint
    # Example usage
    pattern = "blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/{asset_type}"
    filters = {
        'project_name': ['ProjectA'],
        'shot_name': ['shot01', 'shot02'],
    }

    work_file_query = FilePatternQuery(pattern)
    pprint(list(work_file_query.query_files()))
