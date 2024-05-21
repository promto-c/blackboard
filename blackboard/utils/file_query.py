
from typing import Dict, List, Generator

import re, glob, os
from pathlib import Path
from itertools import product

from blackboard.utils.path_utils import PathPattern


class FilePatternQuery:

    META_FIELDS = ['_file_path', '_file_name']

    def __init__(self, pattern: str) -> None:
        self.pattern = Path(pattern).as_posix() + '/'
        self.regex_pattern = PathPattern.convert_pattern_to_regex(self.pattern)
        self.fields = PathPattern.extract_variable_names(self.pattern) + self.META_FIELDS

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

        # Construct combinations using specific filter values or wildcard '*' for each field
        values_combinations = [filters[field] if field in filters and filters[field] else ['*'] for field in self.fields]

        # Generate all possible paths based on combinations of field values
        all_value_combinations = product(*values_combinations)
        # Using map to apply format_by_index for each combination of values
        search_paths = map(self.format_for_recursive_glob, all_value_combinations)

        for search_path in search_paths:
            # Find file paths matching the pattern
            yield from glob.iglob(search_path, recursive=True)

    def query_files(self, filters: Dict[str, List[str]] = dict()) -> Generator[Dict[str, str], None, None]:

        paths = self.construct_search_paths(filters)

        for path in paths:
            path = Path(path).as_posix()
            if not os.path.isfile(path):
                continue
            data_dict = self.extract_variables(path)
            data_dict['_file_path'] = path
            data_dict['_file_name'] = os.path.basename(path)
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
