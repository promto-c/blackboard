import os
import re
import datetime
from typing import Dict, List, Optional, Tuple, Union
import time
from enum import Enum
import random
from collections import defaultdict

if os.name == 'nt':
    import win32security
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
            name, domain, _type = win32security.LookupAccountSid(None, owner_sid)
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
    HASH = 'hash'                                           # '#'
    PERCENT = 'percent'                                     # '%0Nd'
    BRACKETS = 'brackets'                                   # '[0-9]'
    BRACES = 'braces'                                       # '{0..9}'
    HASH_WITH_RANGE = 'hash_with_range'                     # '####.ext 0-9'
    PERCENT_WITH_RANGE = 'percent_with_range'               # '%0Nd.ext 0-9'
    BRACKETS_SEPARATE_RANGES = 'brackets_separate_ranges'   # '[0-4,6-7,9]'

    def requires_range(self) -> bool:
        """Determines if the format style requires a range of frame numbers."""
        return self in {FormatStyle.BRACKETS, FormatStyle.BRACES, FormatStyle.HASH_WITH_RANGE, FormatStyle.PERCENT_WITH_RANGE}

    def requires_separate_ranges(self) -> bool:
        """Determines if the format style requires separate ranges."""
        return self == FormatStyle.BRACKETS_SEPARATE_RANGES

class SequenceFileUtils(FileUtils):
    """Utilities for working with sequence files."""

    FORMAT_TO_REGEX = {
        # NOTE: FormatStyle.HASH_WITH_RANGE and FormatStyle.PERCENT_WITH_RANGE
        # should be ordered before FormatStyle.HASH and FormatStyle.PERCENT to ensure
        # that the more specific patterns with ranges are matched first.
        FormatStyle.HASH_WITH_RANGE: re.compile(r"(.*)\.(#+)\.(\w+) (\d+)-(\d+)"),
        FormatStyle.PERCENT_WITH_RANGE: re.compile(r"(.*)\.%0(\d+)d\.(\w+) (\d+)-(\d+)"),
        FormatStyle.HASH: re.compile(r"(.*)\.(#+)\.(\w+)"),
        FormatStyle.PERCENT: re.compile(r"(.*)\.%0(\d+)d\.(\w+)"),
        FormatStyle.BRACKETS: re.compile(r"(.*)\.\[(\d+)-(\d+)\]\.(\w+)"),
        FormatStyle.BRACES: re.compile(r"(.*)\.\{(\d+)\.\.(\d+)\}\.(\w+)"),
        FormatStyle.BRACKETS_SEPARATE_RANGES: re.compile(r"(.*)\.\[([0-9,\-]+)\]\.(\w+)"),
    }

    FORMAT_TO_STRING_PATTERNS = {
        FormatStyle.HASH: "{base_name}.{range_str}.{extension}",
        FormatStyle.PERCENT: "{base_name}.%0{length}d.{extension}",
        FormatStyle.BRACKETS: "{base_name}.[{min_num:0{length}}-{max_num:0{length}}].{extension}",
        FormatStyle.BRACES: "{base_name}.{{{min_num:0{length}}..{max_num:0{length}}}}.{extension}",
        FormatStyle.HASH_WITH_RANGE: "{base_name}.{range_str}.{extension} {min_num}-{max_num}",
        FormatStyle.PERCENT_WITH_RANGE: "{base_name}.%0{length}d.{extension} {min_num}-{max_num}",
        FormatStyle.BRACKETS_SEPARATE_RANGES: "{base_name}.[{range_str}].{extension}",
    }

    @staticmethod
    def format_sequence(style: FormatStyle, base_name: str, sequences: List[str], extension: str, length: int = 4, preserve_length: bool = False) -> str:
        """Constructs the formatted sequence string based on the format style using cached patterns."""
        format_string = SequenceFileUtils.FORMAT_TO_STRING_PATTERNS.get(style)
        
        if format_string is None:
            raise ValueError(f"Unsupported format style: {style}")

        range_str = None
        min_num = None
        max_num = None
        if style in (FormatStyle.HASH, FormatStyle.HASH_WITH_RANGE):
            range_str = '#' * length
        elif style.requires_range():
            min_num, max_num = SequenceFileUtils.get_sequence_range(sequences)
        elif style.requires_separate_ranges():
            ranges = SequenceFileUtils.get_sequence_ranges(sequences, preserve_length)
            range_str = ','.join(ranges)

        return format_string.format(
            base_name=base_name,
            length=length,
            extension=extension,
            min_num=min_num,
            max_num=max_num,
            range_str=range_str,
        )

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
    def detect_sequence_format(padded_format: str) -> Optional[FormatStyle]:
        """Detects the format of the padded sequence.

        Args:
            padded_format (str): The padded sequence format.

        Returns:
            Optional[FormatStyle]: The detected format style, or None if no match is found.

        Examples:
            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.######.exr')
            <FormatStyle.HASH: 'hash'>

            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.%04d.exr')
            <FormatStyle.PERCENT: 'percent'>

            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.[001001-001012].exr')
            <FormatStyle.BRACKETS: 'brackets'>

            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.{1001..1002}.exr')
            <FormatStyle.BRACES: 'braces'>

            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.[1001,1001-1002,1011-1012].exr')
            <FormatStyle.BRACKETS_SEPARATE_RANGES: 'brackets_separate_ranges'>

            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.####.exr 0-9')
            <FormatStyle.HASH_WITH_RANGE: 'hash_with_range'>

            >>> SequenceFileUtils.detect_sequence_format('project/shot/comp_v1.%04d.exr 0-9')
            <FormatStyle.PERCENT_WITH_RANGE: 'percent_with_range'>
        """
        return next((style for style, pattern in SequenceFileUtils.FORMAT_TO_REGEX.items() if pattern.match(padded_format)), None)

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
    def get_sequence_range(sequence_numbers: List[str]) -> Tuple[int, int]:
        """Gets the range of sequence numbers from a list of sequence files.

        Args:
            sequence_numbers (List[str]): A list of sequence numbers.

        Returns:
            Tuple[int, int]: The minimum and maximum sequence numbers in the list.
        """
        sequence_numbers = [int(num) for num in sequence_numbers if num.isdigit()]
        return min(sequence_numbers), max(sequence_numbers)

    @staticmethod
    def get_sequence_ranges(sequence_numbers: List[str], preserve_length: bool = False) -> List[str]:
        """Gets the ranges of sequence numbers from a list of sequence numbers.

        Args:
            sequence_numbers (List[str]): A list of sequence numbers.
            preserve_length (bool): Whether to preserve the length of the sequence numbers using zfill.

        Returns:
            List[str]: A list of ranges in the format 'start-end' or individual numbers as strings.
        """
        sequence_numbers_int = sorted([int(num) for num in sequence_numbers])
        ranges = []
        range_start = sequence_numbers_int[0]
        previous_num = sequence_numbers_int[0]
        length = len(sequence_numbers[0])

        for num in sequence_numbers_int[1:]:
            if num != previous_num + 1:
                if range_start == previous_num:
                    ranges.append(f'{range_start:0{length}}' if preserve_length else str(range_start))
                else:
                    ranges_str = f'{range_start:0{length}}-{previous_num:0{length}}' if preserve_length else f'{range_start}-{previous_num}'
                    ranges.append(ranges_str)
                range_start = num
            previous_num = num

        if range_start == previous_num:
            ranges.append(f'{range_start:0{length}}' if preserve_length else str(range_start))
        else:
            ranges_str = f'{range_start:0{length}}-{previous_num:0{length}}' if preserve_length else f'{range_start}-{previous_num}'
            ranges.append(ranges_str)

        return ranges

    @staticmethod
    def convert_to_padded_format(file_paths: List[str], distinct_formats: bool = True, format_style: FormatStyle = FormatStyle.HASH) -> List[str]:
        """Converts a list of file paths to a list with padded sequence formats.

        Args:
            file_paths (List[str]): A list of file paths.
            distinct_formats (bool): Whether to include distinct formats for each sequence length.
            format_style (FormatStyle): The format style to use for padding.

        Returns:
            List[str]: A list of file paths with padded sequence formats.

        Examples:
            >>> file_paths = [
            ... 'project/shot/comp_v1.001001.exr',
            ... 'project/shot/comp_v1.001011.exr',
            ... 'project/shot/comp_v1.001012.exr',
            ... 'project/shot/comp_v1.1001.exr',
            ... 'project/shot/comp_v1.1002.exr',
            ... 'project/shot/comp_v1.1001.jpg',
            ... 'project/shot/comp_v1.1002.jpg',
            ... 'project/shot/reference_image.png',
            ... 'project/shot/notes.txt'
            ... ]
            >>> SequenceFileUtils.convert_to_padded_format(file_paths)
            ['project/shot/comp_v1.######.exr', 'project/shot/comp_v1.####.exr', 'project/shot/comp_v1.####.jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=False)
            ['project/shot/comp_v1.######.exr', 'project/shot/comp_v1.####.jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtils.convert_to_padded_format(file_paths, format_style=FormatStyle.PERCENT)
            ['project/shot/comp_v1.%04d.exr', 'project/shot/comp_v1.%04d.jpg', 'project/shot/comp_v1.%06d.exr', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtils.convert_to_padded_format(file_paths, format_style=FormatStyle.BRACKETS)
            ['project/shot/comp_v1.[001001-001012].exr', 'project/shot/comp_v1.[1001-1002].exr', 'project/shot/comp_v1.[1001-1002].jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtils.convert_to_padded_format(file_paths, format_style=FormatStyle.BRACES)
            ['project/shot/comp_v1.{001001..001012}.exr', 'project/shot/comp_v1.{1001..1002}.exr', 'project/shot/comp_v1.{1001..1002}.jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtils.convert_to_padded_format(file_paths, format_style=FormatStyle.BRACKETS_SEPARATE_RANGES)
            ['project/shot/comp_v1.[001001,001011-001012].exr', 'project/shot/comp_v1.[1001-1002].exr', 'project/shot/comp_v1.[1001-1002].jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=False, format_style=FormatStyle.BRACKETS_SEPARATE_RANGES)
            ['project/shot/comp_v1.[1001,1001-1002,1011-1012].exr', 'project/shot/comp_v1.[1001-1002].jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']
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
            if distinct_formats:
                length_to_sequences = defaultdict(list)
                for seq in sequence_numbers:
                    length_to_sequences[len(seq)].append(seq)

                padded_format_set = {
                    SequenceFileUtils.format_sequence(
                        style=format_style,
                        base_name=base_name,
                        sequences=sequences,
                        extension=extension,
                        length=length,
                        preserve_length=True
                    ) for length, sequences in length_to_sequences.items()
                }

                result.update(padded_format_set)

            else:
                padded_format = SequenceFileUtils.format_sequence(
                    style=format_style,
                    base_name=base_name,
                    sequences=sequence_numbers, 
                    extension=extension,
                    length=len(max(sequence_numbers, key=len)),
                    preserve_length=False
                )

                result.add(padded_format)

        return sorted(result)

    @staticmethod
    def calculate_total_size(base_path: Union[str, List[str]], start_frame: int = None, end_frame: int = None, extension: str = None) -> int:
        """Calculates the total size of a sequence of files or a list of files.

        Args:
            base_path (Union[str, List[str]]): The base path of the sequence or a list of file paths.
            start_frame (int, optional): The starting frame number. Required if base_path is a str.
            end_frame (int, optional): The ending frame number. Required if base_path is a str.
            extension (str, optional): The file extension. Required if base_path is a str.

        Returns:
            int: The total size of the sequence of files or the list of files.
        """
        file_paths = []

        if isinstance(base_path, str):
            if start_frame is None or end_frame is None or extension is None:
                raise ValueError("start_frame, end_frame, and extension are required when base_path is a string")

            for frame_number in range(start_frame, end_frame + 1):
                filename = f"{base_path}.{str(frame_number).zfill(5)}{extension}"
                file_paths.append(filename)

        elif isinstance(base_path, list):
            file_paths = base_path

        else:
            raise TypeError("base_path must be either a string or a list of strings")

        return sum(map(os.path.getsize, file_paths))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

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

    start_time = time.time()
    padded_paths_single = SequenceFileUtils.convert_to_padded_format(file_paths, distinct_formats=True, format_style=FormatStyle.BRACKETS_SEPARATE_RANGES)
    end_time = time.time()
    print(f"Single format (separate ranges): {padded_paths_single[:10]}...")  # Print only the first 10 for brevity
    print(f"Time taken with single format (separate ranges): {end_time - start_time} seconds")