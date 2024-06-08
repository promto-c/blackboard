import os
import datetime
from typing import Dict, List, Optional, Tuple
import time
from enum import Enum
import random
from collections import defaultdict

if os.name == 'nt':
    import win32security
    import ntsecuritycon as con
else:
    import pwd

class FileUtils:
    """Utilities for working with files."""
    # Units for formatting file sizes
    UNITS = ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB']
    FILE_INFO_FIELDS = ['file_name', 'file_path', 'file_size', 'file_extension', 'last_modified', 'file_owner']

    @staticmethod
    def extract_file_info(file_path: str) -> Dict[str, str]:
        """Extracts detailed information about a file.

        Args:
            file_path (str): Path to the file for extracting information.

        Returns:
            Dict[str, str]: A dictionary containing detailed file information, including:
                - file_name: The base name of the file.
                - file_path: The full path to the file.
                - file_size: File size in a human-readable format.
                - file_extension: The file extension.
                - last_modified: The last modification timestamp in `YYYY-MM-DD HH:MM:SS` format.
                - file_owner: The owner of the file.
        """
        # Retrieve file statistics and details: file info, owner, last modified time, extension, and formatted size
        file_info = os.stat(file_path)
        owner = FileUtils.get_file_owner(file_path)
        modified_time = datetime.datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
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
    def get_file_owner(file_path: str) -> str:
        """Gets the owner of a file.

        Args:
            file_path (str): Path to the file.

        Returns:
            str: The name of the file owner.
        """
        if os.name == 'nt':
            sd = win32security.GetFileSecurity(file_path, win32security.OWNER_SECURITY_INFORMATION)
            owner_sid = sd.GetSecurityDescriptorOwner()
            name, domain, type = win32security.LookupAccountSid(None, owner_sid)
            return f"{domain}\\{name}"
        else:
            file_info = os.stat(file_path)
            return pwd.getpwuid(file_info.st_uid).pw_name

    @staticmethod
    def format_size(size: int, precision: int = 2) -> str:
        """Converts a file size to a human-readable form with adjustable precision.

        Args:
            size (int): The size of the file in bytes.
            precision (int, optional): The number of decimal places for the formatted size. Defaults to 2.

        Returns:
            str: File size in a human-readable format, such as '1.23 MB'.
        """
        # Loop through each unit until the size is smaller than 1024
        for unit in FileUtils.UNITS:
            if size < 1024:
                # Use the appropriate format string based on the unit
                formatted_size = f"{size:.{precision}f} {unit}" if unit != 'bytes' else f"{size} {unit}"
                return formatted_size
            
            # Divide the size by 1024 to move to the next unit
            size /= 1024
        
        # Handle extremely large sizes that exceed petabytes
        return f"{size:.{precision}f} PB"

class FormatStyle(Enum):
    """Enum for different placeholder formats for file sequences.
    """
    HASH = 'hash'                               # '#'
    PERCENT = 'percent'                         # '%0Nd'
    BRACKETS = 'brackets'                       # '[0-9]'
    BRACES = 'braces'                           # '{0..9}'
    HASH_WITH_RANGE = 'hash_with_range'         # '####.ext 0-9'
    PERCENT_WITH_RANGE = 'percent_with_range'   # '%0Nd.ext 0-9'

    def requires_frame_range(self) -> bool:
        """Determines if the format style requires a range of frame numbers."""
        return self in {FormatStyle.BRACKETS, FormatStyle.BRACES}

    def format_sequence(self, base_name: str, length: int, extension: str, min_num: Optional[int] = None, max_num: Optional[int] = None) -> str:
        """Constructs the formatted sequence string based on the format style."""
        if self == FormatStyle.HASH:
            return f"{base_name}.{'#' * length}.{extension}"
        elif self == FormatStyle.PERCENT:
            return f"{base_name}.%0{length}d.{extension}"
        elif self == FormatStyle.BRACKETS:
            return f"{base_name}.[{str(min_num).zfill(length)}-{str(max_num).zfill(length)}].{extension}"
        elif self == FormatStyle.BRACES:
            return f"{base_name}.{{{str(min_num).zfill(length)}..{str(max_num).zfill(length)}}}.{extension}"
        elif self == FormatStyle.HASH_WITH_RANGE:
            return f"{base_name}.{'#' * length}.{extension} {min_num}-{max_num}"
        elif self == FormatStyle.PERCENT_WITH_RANGE:
            return f"{base_name}.%0{length}d.{extension} {min_num}-{max_num}"
        else:
            raise ValueError(f"Unsupported format style: {self}")

class SequenceFileUtils(FileUtils):
    """Utilities for working with sequence files."""

    @staticmethod
    def is_sequence_file(file_name: str) -> bool:
        """Checks if a file name follows the sequence file pattern (e.g., 'image.####.ext').

        Args:
            file_name (str): The file name to check.

        Returns:
            bool: True if the file name follows the sequence pattern, False otherwise.
        """
        parts = file_name.split('.')
        if len(parts) < 3:
            return False
        return parts[-2].isdigit() and len(parts[-2]) > 1

    @staticmethod
    def extract_sequence_info(file_name: str) -> Optional[Dict[str, str]]:
        """Extracts sequence information from a file name.

        Args:
            file_name (str): The file name to extract information from.

        Returns:
            Optional[Dict[str, str]]: A dictionary containing sequence information if the file name follows the sequence pattern, otherwise None.
        """
        if not SequenceFileUtils.is_sequence_file(file_name):
            return None

        parts = file_name.rsplit('.', 2)
        return {
            "base_name": parts[0],
            "sequence_number": parts[1],
            "extension": parts[2]
        }

    @staticmethod
    def find_sequence_files(directory: str, base_name: str) -> List[str]:
        """Finds all files in a directory that belong to the same sequence.

        Args:
            directory (str): The directory to search in.
            base_name (str): The base name of the sequence (e.g., 'image' for 'image.####.ext').

        Returns:
            List[str]: A list of file names that belong to the same sequence.
        """
        sequence_files = []
        for file_name in os.listdir(directory):
            sequence_info = SequenceFileUtils.extract_sequence_info(file_name)
            if sequence_info and sequence_info['base_name'] == base_name:
                sequence_files.append(file_name)
        return sorted(sequence_files)

    @staticmethod
    def get_sequence_range(sequence_files: List[str]) -> Tuple[int, int]:
        """Gets the range of sequence numbers from a list of sequence files.

        Args:
            sequence_files (List[str]): A list of sequence file names.

        Returns:
            Tuple[int, int]: The minimum and maximum sequence numbers in the list.
        """
        sequence_numbers = [int(f) for f in sequence_files if f.isdigit()]
        return min(sequence_numbers), max(sequence_numbers)

    @staticmethod
    def convert_to_padded_format(file_paths: List[str], distinct_formats: bool = True, format_style: FormatStyle = FormatStyle.HASH) -> List[str]:
        """Converts a list of file paths to a list with padded sequence formats.

        Args:
            file_paths (List[str]): A list of file paths.
            distinct_formats (bool): Whether to include distinct formats for each sequence length.
            format_style (FormatStyle): The format style to use for padding.

        Returns:
            List[str]: A list of file paths with padded sequence formats.
        """
        sequence_dict = defaultdict(list)
        result = set()

        for file_path in file_paths:
            sequence_info = SequenceFileUtils.extract_sequence_info(file_path)
            if sequence_info:
                base_name = sequence_info['base_name']
                sequence_number = sequence_info['sequence_number']
                extension = sequence_info['extension']
                key = (base_name, extension)
                sequence_dict[key].append(sequence_number)
            else:
                result.add(file_path)

        for (base_name, extension), sequence_numbers in sequence_dict.items():
            max_length = len(max(sequence_numbers, key=len))

            min_num, max_num = None, None
            if format_style.requires_frame_range():
                min_num, max_num = SequenceFileUtils.get_sequence_range(sequence_numbers)

            if distinct_formats:
                for length in set(map(len, sequence_numbers)):
                    padded_format = format_style.format_sequence(base_name, length, extension, min_num, max_num)
                    result.add(padded_format)
            else:
                padded_format = format_style.format_sequence(base_name, max_length, extension, min_num, max_num)
                result.add(padded_format)

        return sorted(result)

# Example usage
file_paths = [
    'path/to/file.1001.exr',
    'path/to/file.1002.exr',
    'path/to/file.1003.exr',
    'path/to/file.1004.exr',
    'path/to/file.1005.exr',
    'path/to/file.143541.exr',
    'path/to/file.143542.exr',
    'path/to/file.2001.exr',
    'path/to/file.2002.exr',
    'path/to/file.2003.exr',
    'path/to/file.300001.exr',
    'path/to/file.300002.exr',
    'path/to/file.300003.exr',
    'path/to/file.40001.exr',
    'path/to/file.40002.exr',
    'path/to/simple_file.conf',
    'path/to/another_file.conf',
    'path/to/some_file.txt',
    'path/to/other_file.log',
    'path/to/yet_another_file.dat'
]

def generate_file_paths(num_files: int) -> List[str]:
    sequence_bases = ['file', 'image', 'video', 'audio']
    non_sequence_files = ['config.conf', 'readme.txt', 'data.log', 'notes.doc']
    extensions = ['exr', 'jpg', 'png', 'mp4', 'mp3']

    file_paths = []

    for i in range(num_files):
        if random.choice([True, False]):
            base = random.choice(sequence_bases)
            sequence_number = str(random.randint(1, 999999)).zfill(random.randint(4, 6))
            extension = random.choice(extensions)
            file_path = f"path/to/{base}.{sequence_number}.{extension}"
        else:
            file_path = f"path/to/{random.choice(non_sequence_files)}"

        file_paths.append(file_path)

    return file_paths

# Generate 2000 file paths for testing
file_paths = generate_file_paths(2000)
from pprint import pprint
# Performance comparison
start_time = time.time()
padded_paths_distinct = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=True, format_style=FormatStyle.HASH)
end_time = time.time()
pprint(f"Distinct formats (hash): {padded_paths_distinct[:10]}...")  # Print only the first 10 for brevity
pprint(f"Time taken with distinct formats (hash): {end_time - start_time} seconds")

start_time = time.time()
padded_paths_single = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=False, format_style=FormatStyle.HASH)
end_time = time.time()
pprint(f"Single format (hash): {padded_paths_single[:10]}...")  # Print only the first 10 for brevity
pprint(f"Time taken with single format (hash): {end_time - start_time} seconds")

# Test with %0Nd format
start_time = time.time()
padded_paths_distinct = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=True, format_style=FormatStyle.PERCENT)
end_time = time.time()
pprint(f"Distinct formats (%0Nd): {padded_paths_distinct[:10]}...")  # Print only the first 10 for brevity
pprint(f"Time taken with distinct formats (%0Nd): {end_time - start_time} seconds")

start_time = time.time()
padded_paths_single = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=False, format_style=FormatStyle.PERCENT)
end_time = time.time()
pprint(f"Single format (%0Nd): {padded_paths_single[:10]}...")  # Print only the first 10 for brevity
pprint(f"Time taken with single format (%0Nd): {end_time - start_time} seconds")

# Test with [0-9] format
start_time = time.time()
padded_paths_distinct = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=True, format_style=FormatStyle.BRACKETS)
end_time = time.time()
pprint(f"Distinct formats ([0-9]): {padded_paths_distinct[:10]}...")  # Print only the first 10 for brevity
pprint(f"Time taken with distinct formats ([0-9]): {end_time - start_time} seconds")

start_time = time.time()
padded_paths_single = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=False, format_style=FormatStyle.BRACKETS)
end_time = time.time()
pprint(f"Single format ([0-9]): {padded_paths_single[:10]}...")  # Print only the first 10 for brevity
pprint(f"Time taken with single format ([0-9]): {end_time - start_time} seconds")

# Test with {0..9} format
start_time = time.time()
padded_paths_distinct = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=True, format_style=FormatStyle.BRACES)
end_time = time.time()
print(f"Distinct formats ({{0..9}}): {padded_paths_distinct[:10]}...")  # Print only the first 10 for brevity
print(f"Time taken with distinct formats ({{0..9}}): {end_time - start_time} seconds")

start_time = time.time()
padded_paths_single = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=False, format_style=FormatStyle.BRACES)
end_time = time.time()
print(f"Single format ({{0..9}}): {padded_paths_single[:10]}...")  # Print only the first 10 for brevity
print(f"Time taken with single format ({{0..9}}): {end_time - start_time} seconds")