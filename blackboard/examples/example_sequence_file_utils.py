import os
import glob
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

class FileUtil:
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
        owner = FileUtil.get_file_owner(file_path)
        modified_time = datetime.datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        extension = FileUtil.get_file_extension(file_path)
        readable_size = FileUtil.format_size(file_info.st_size)

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
    def get_file_extension(file_path: str) -> str:
        """Gets the file extension of a file.

        Args:
            file_path (str): Path to the file.

        Returns:
            str: The file extension, or an empty string if the file has no extension.
        """
        return file_path.rsplit('.', 1)[-1] if '.' in file_path else ''

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
        for unit in FileUtil.UNITS:
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

class SequenceFileUtil(FileUtil):
    """Utilities for working with sequence files."""

    DEFAULT_PADDING = 4

    FORMAT_TO_REGEX = {
        # NOTE: FormatStyle.HASH_WITH_RANGE and FormatStyle.PERCENT_WITH_RANGE
        # should be ordered before FormatStyle.HASH and FormatStyle.PERCENT to ensure
        # that the more specific patterns with ranges are matched first.
        FormatStyle.HASH_WITH_RANGE: re.compile(r"(?P<base_name>.*)\.(?P<hashes>#+)\.(?P<extension>\w+) (?P<start_frame>\d+)-(?P<end_frame>\d+)"),
        FormatStyle.PERCENT_WITH_RANGE: re.compile(r"(?P<base_name>.*)\.%0(?P<padding>\d+)d\.(?P<extension>\w+) (?P<start_frame>\d+)-(?P<end_frame>\d+)"),
        FormatStyle.HASH: re.compile(r"(?P<base_name>.*)\.(?P<hashes>#+)\.(?P<extension>\w+)"),
        FormatStyle.PERCENT: re.compile(r"(?P<base_name>.*)\.%0(?P<padding>\d+)d\.(?P<extension>\w+)"),
        FormatStyle.BRACKETS: re.compile(r"(?P<base_name>.*)\.\[(?P<start_frame>\d+)-(?P<end_frame>\d+)\]\.(?P<extension>\w+)"),
        FormatStyle.BRACES: re.compile(r"(?P<base_name>.*)\.\{(?P<start_frame>\d+)\.\.(?P<end_frame>\d+)\}\.(?P<extension>\w+)"),
        FormatStyle.BRACKETS_SEPARATE_RANGES: re.compile(r"(?P<base_name>.*)\.\[(?P<ranges>[0-9,\-]+)\]\.(?P<extension>\w+)"),
    }

    FORMAT_TO_PADDING_RULES = {
        FormatStyle.HASH: lambda match_data: len(match_data['hashes']),
        FormatStyle.PERCENT: lambda match_data: int(match_data['padding']),
        FormatStyle.BRACKETS: lambda match_data: len(match_data['start_frame']),
        FormatStyle.BRACES: lambda match_data: len(match_data['start_frame']),
        FormatStyle.HASH_WITH_RANGE: lambda match_data: len(match_data['hashes']),
        FormatStyle.PERCENT_WITH_RANGE: lambda match_data: int(match_data['padding']),
        FormatStyle.BRACKETS_SEPARATE_RANGES: lambda match_data: len(match_data['ranges'].split(',')[0].split('-')[0]),
    }

    FORMAT_TO_STRING_PATTERNS = {
        FormatStyle.HASH: "{base_name}.{range_str}.{extension}",
        FormatStyle.PERCENT: "{base_name}.%0{padding}d.{extension}",
        FormatStyle.BRACKETS: "{base_name}.[{start_frame:0{padding}}-{end_frame:0{padding}}].{extension}",
        FormatStyle.BRACES: "{base_name}.{{{start_frame:0{padding}}..{end_frame:0{padding}}}}.{extension}",
        FormatStyle.HASH_WITH_RANGE: "{base_name}.{range_str}.{extension} {start_frame}-{end_frame}",
        FormatStyle.PERCENT_WITH_RANGE: "{base_name}.%0{padding}d.{extension} {start_frame}-{end_frame}",
        FormatStyle.BRACKETS_SEPARATE_RANGES: "{base_name}.[{range_str}].{extension}",
    }

    @staticmethod
    def extract_sequence_details(sequence_path_format: str, format_style: Optional['FormatStyle'] = None) -> Dict[str, str]:
        """Extracts groups from the sequence path format.

        Args:
            sequence_path_format (str): The sequence path format.
            format_style (Optional[FormatStyle]): The format style to use, if not provided, it will be detected.

        Returns:
            Dict[str, str]: The extracted groups from the sequence path format.
        """
        format_style = format_style or SequenceFileUtil.detect_sequence_format(sequence_path_format)
        if not format_style:
            raise ValueError("Unsupported format style")

        match = SequenceFileUtil.FORMAT_TO_REGEX[format_style].match(sequence_path_format)
        if not match:
            raise ValueError("Invalid format")
        
        return match.groupdict()

    @staticmethod
    def get_padding(input_data: Union[Dict[str, str], str], format_style: Optional[FormatStyle] = None) -> int:
        """Determines the padding for sequence numbers based on the format style and match groups or sequence path format.

        Args:
            input_data (Union[dict, str]): The match groups from the regex or the sequence path format.
            format_style (Optional[FormatStyle]): The format style to use, if not provided, it will be detected.

        Returns:
            int: The number of digits to pad the sequence numbers.
        """
        # Detect format style and extract sequence details if input_data is a sequence path format string
        if isinstance(input_data, str):
            format_style = format_style or SequenceFileUtil.detect_sequence_format(input_data)
            sequence_data = SequenceFileUtil.extract_sequence_details(input_data, format_style)
        # Use input_data directly if it's already a dictionary of sequence details
        elif isinstance(input_data, dict):
            sequence_data = input_data
        else:
            raise TypeError("input_data must be a dict or str")

        # Ensure the format style is valid
        if not format_style:
            raise ValueError("Unsupported format style")

        # Determine and return the padding based on the format style and sequence details
        return SequenceFileUtil.FORMAT_TO_PADDING_RULES.get(format_style, lambda _: SequenceFileUtil.DEFAULT_PADDING)(sequence_data)

    @staticmethod
    def construct_sequence_file_path(format_style: 'FormatStyle', base_name: str, frame_numbers: List[str], extension: str,
                                     padding: int = DEFAULT_PADDING) -> str:
        """Constructs the formatted sequence file path based on the specified format style using cached patterns.

        Args:
            format_style (FormatStyle): The format style to use, determining the pattern applied to the sequence.
            base_name (str): The base name of the sequence.
            frame_numbers (List[str]): The list of frame numbers to be included in the sequence.
            extension (str): The file extension to be appended to the formatted sequence.
            padding (int, optional): The number of digits to pad the sequence numbers. Default is 4.

        Returns:
            str: The formatted sequence file path based on the provided parameters and format style.

        Raises:
            ValueError: If the provided format style is unsupported.

        Examples:
            >>> SequenceFileUtil.construct_sequence_file_path(FormatStyle.HASH, 'image', ['1', '2', '3'], 'jpg', 4)
            'image.####.jpg'
            >>> SequenceFileUtil.construct_sequence_file_path(FormatStyle.HASH_WITH_RANGE, 'image', ['1', '2', '3'], 'jpg', 4)
            'image.####.jpg 1-3'
            >>> SequenceFileUtil.construct_sequence_file_path(FormatStyle.PERCENT, 'image', ['1', '2', '3'], 'jpg', 4)
            'image.%04d.jpg'
            >>> SequenceFileUtil.construct_sequence_file_path(FormatStyle.BRACKETS_SEPARATE_RANGES, 'project/shot/comp_v1', ['988', '1001', '1002', '1011'], 'jpg', 4)
            'project/shot/comp_v1.[0988,1001-1002,1011].jpg'
        """
        # Get the string pattern corresponding to the format style
        string_pattern = SequenceFileUtil.FORMAT_TO_STRING_PATTERNS.get(format_style)

        # Raise an error if the format style is unsupported
        if string_pattern is None:
            raise ValueError(f"Unsupported format style: {format_style}")

        # Initialize variables for range string, minimum, and maximum numbers
        range_str = None
        start_frame = None
        end_frame = None

        # Check if the format style requires a range and get the sequence range if true
        if format_style.requires_range():
            start_frame, end_frame = SequenceFileUtil.get_sequence_range(frame_numbers)

        # Handle specific format styles that require pre-processing of the string.
        if format_style in (FormatStyle.HASH, FormatStyle.HASH_WITH_RANGE):
            range_str = '#' * padding
        elif format_style.requires_separate_ranges():
            ranges = SequenceFileUtil.get_sequence_ranges(frame_numbers, padding)
            range_str = ','.join(ranges)

        # Construct and return the formatted sequence file path
        return string_pattern.format(
            base_name=base_name,
            padding=padding,
            extension=extension,
            start_frame=start_frame,
            end_frame=end_frame,
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
        return parts[-2].isdigit()

    @staticmethod
    def detect_sequence_format(sequence_path_format: str) -> Optional['FormatStyle']:
        """Detects the format of the sequence path format.

        Args:
            sequence_path_format (str): The sequence path format.

        Returns:
            Optional[FormatStyle]: The detected format style, or None if no match is found.

        Examples:
            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.######.exr')
            <FormatStyle.HASH: 'hash'>

            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.%04d.exr')
            <FormatStyle.PERCENT: 'percent'>

            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.[001001-001012].exr')
            <FormatStyle.BRACKETS: 'brackets'>

            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.{1001..1002}.exr')
            <FormatStyle.BRACES: 'braces'>

            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.[1001,1001-1002,1011-1012].exr')
            <FormatStyle.BRACKETS_SEPARATE_RANGES: 'brackets_separate_ranges'>

            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.####.exr 0-9')
            <FormatStyle.HASH_WITH_RANGE: 'hash_with_range'>

            >>> SequenceFileUtil.detect_sequence_format('project/shot/comp_v1.%04d.exr 0-9')
            <FormatStyle.PERCENT_WITH_RANGE: 'percent_with_range'>
        """
        return next((style for style, pattern in SequenceFileUtil.FORMAT_TO_REGEX.items() if pattern.match(sequence_path_format)), None)

    @staticmethod
    def construct_file_paths(base_name: str, frames: List[int], extension: str, padding: int) -> List[str]:
        """Constructs file paths based on the base name, list of frames, and extension.

        Args:
            base_name (str): The base name of the sequence.
            frames (List[int]): A list of frame numbers.
            extension (str): The file extension.
            padding (int): The number of digits in the frame number.

        Returns:
            List[str]: A list of constructed file paths.
        """
        return [f"{base_name}.{frame:0{padding}}.{extension}" for frame in frames]

    @staticmethod
    def extract_paths_from_format(sequence_path_format: str, sequence_range: Optional[Tuple[int, int]] = None, format_style: Optional['FormatStyle'] = None) -> List[str]:
        """Extracts individual file paths from a sequence path format.

        Args:
            sequence_path_format (str): The sequence path format.
            sequence_range (Optional[Tuple[int, int]]): An optional range of sequence numbers (start, end).
            format_style (Optional[FormatStyle]): The format style to use, if not provided, it will be detected.

        Returns:
            List[str]: A list of individual file paths.
        """
        # Detect the format style if not provided
        format_style = format_style or SequenceFileUtil.detect_sequence_format(sequence_path_format)
        if not format_style:
            raise ValueError("Unsupported format style")

        # Initialize file paths list
        file_paths = []

        # Extract details from the sequence path format
        sequence_data = SequenceFileUtil.extract_sequence_details(sequence_path_format, format_style=format_style)
        base_name = sequence_data['base_name']
        extension = sequence_data['extension']
        padding = SequenceFileUtil.get_padding(sequence_data, format_style=format_style)

        # Handle formats that include a range of frames
        if format_style.requires_range():
            start_frame = int(sequence_data['start_frame'])
            end_frame = int(sequence_data['end_frame'])
            file_paths = SequenceFileUtil.construct_file_paths(base_name, range(start_frame, end_frame + 1), extension, padding)
        
        # Handle formats that include separate ranges
        elif format_style.requires_separate_ranges():
            ranges = sequence_data['ranges'].split(',')
            frames = SequenceFileUtil.ranges_to_sequence_numbers(ranges)
            file_paths = SequenceFileUtil.construct_file_paths(base_name, frames, extension, padding)
        
        # Handle other formats
        else:
            # If a sequence range is provided, use it
            if sequence_range:
                start_frame, end_frame = sequence_range
                file_paths = SequenceFileUtil.construct_file_paths(base_name, range(start_frame, end_frame + 1), extension, padding)

            # Otherwise, determine the sequence range from the files on disk
            else:
                # Replace format placeholders with '?' for glob pattern
                if format_style == FormatStyle.HASH:
                    pattern = sequence_path_format.replace('#', '?')
                elif format_style == FormatStyle.PERCENT:
                    pattern = sequence_path_format.replace(f'%0{padding}d', '?' * padding)
                else:
                    raise ValueError("Sequence range must be provided for this format style")

                # Use glob to find matching files
                file_paths = glob.glob(pattern)

        return sorted(file_paths)

    @staticmethod
    def parse_sequence_file_name(file_name: str) -> Tuple[str, str, str]:
        """Parses sequence information from a file name.

        Args:
            file_name (str): The file name to extract information from.

        Returns:
            Tuple[str, str, str]: A tuple containing the base name, sequence number, and extension
                if the file name follows the sequence pattern, otherwise a tuple of Nones.
        """
        parts = file_name.rsplit('.', 2)
        if len(parts) == 3 and parts[1].isdigit():
            return tuple(parts)
        else:
            return None, None, None

    @staticmethod
    def get_sequence_range(sequence_numbers: List[str]) -> Tuple[int, int]:
        """Gets the range of sequence numbers from a list of sequence numbers.

        Args:
            sequence_numbers (List[str]): A list of sequence numbers.

        Returns:
            Tuple[int, int]: The minimum and maximum sequence numbers in the list.
        """
        # Convert all sequence numbers to integers and return the minimum and maximum sequence numbers
        sequence_numbers = [int(num) for num in sequence_numbers if num.isdigit()]
        return min(sequence_numbers), max(sequence_numbers)

    @staticmethod
    def get_sequence_ranges(sequence_numbers: List[str], padding: int = 0) -> List[str]:
        """Gets the ranges of sequence numbers from a list of sequence numbers.

        Args:
            sequence_numbers (List[str]): A list of sequence numbers.
            padding (int, optional): The number of digits to pad the sequence numbers. If not set, no padding is added.

        Returns:
            List[str]: A list of ranges in the format 'start-end' or individual numbers as strings.

        Examples:
            >>> SequenceFileUtil.get_sequence_ranges(["988", "989", "1003", "1007", "1008", "1006"])
            ['988-989', '1003', '1006-1008']
            >>> SequenceFileUtil.get_sequence_ranges(["999", "1000", "1001", "1002", "1003", "1007", "1008", "1010"], padding=4)
            ['0999-1003', '1007-1008', '1010']
            >>> SequenceFileUtil.get_sequence_ranges([], padding=0)
            []
        """
        # Initialize an empty list to store the resulting ranges
        ranges = []

        # Return early with empty ranges if the input list is empty
        if not sequence_numbers:
            return ranges

        # Sort the sequence numbers, remove duplicates, and add a sentinel value (None) at the end
        sorted_numbers = sorted(set(map(int, sequence_numbers))) + [None]
        range_start = sorted_numbers[0]

        # Iterate through pairs of previous and current numbers in the sorted list
        for previous_num, current_num in zip(sorted_numbers, sorted_numbers[1:]):
            # Continue the loop if the current number is consecutive to the previous number
            if previous_num + 1 == current_num:
                continue

            # If the range start is the same as the previous number, add it as a single number
            # Otherwise, add the range from the start to the previous number
            if range_start == previous_num:
                ranges.append(f'{range_start:0{padding}}')
            else:
                ranges.append(f'{range_start:0{padding}}-{previous_num:0{padding}}')

            # Update the range start to the current number
            range_start = current_num

        return ranges

    @staticmethod
    def ranges_to_sequence_numbers(ranges: List[str]) -> List[int]:
        """Converts ranges in the format 'start-end' or individual numbers as strings to a list of integers.

        Args:
            ranges (List[str]): The ranges to convert.

        Returns:
            List[int]: A list of sequence numbers.
        """
        # Initialize the list to hold sequence numbers
        sequence_numbers = []

        # Process each part of the ranges
        for part in ranges:
            if '-' in part:
                start, end = map(int, part.split('-'))
                sequence_numbers.extend(range(start, end + 1))
            else:
                sequence_numbers.append(int(part))

        # Return the list of sequence numbers
        return sequence_numbers

    @staticmethod
    def convert_to_sequence_format(file_paths: List[str], format_style: 'FormatStyle' = FormatStyle.HASH, use_unique_padding: bool = True) -> List[str]:
        """Converts a list of file paths to a list with sequence path formats.

        Args:
            file_paths (List[str]): A list of file paths.
            format_style (FormatStyle): The format style to use for padding.
            use_unique_padding (bool): Whether to include distinct formats for each sequence length.

        Returns:
            List[str]: A list of file paths with sequence path formats.

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
            >>> SequenceFileUtil.convert_to_sequence_format(file_paths)
            ['project/shot/comp_v1.######.exr', 'project/shot/comp_v1.####.exr', 'project/shot/comp_v1.####.jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtil.convert_to_sequence_format(file_paths, use_unique_padding=False)
            ['project/shot/comp_v1.######.exr', 'project/shot/comp_v1.####.jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtil.convert_to_sequence_format(file_paths, format_style=FormatStyle.PERCENT)
            ['project/shot/comp_v1.%04d.exr', 'project/shot/comp_v1.%04d.jpg', 'project/shot/comp_v1.%06d.exr', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtil.convert_to_sequence_format(file_paths, format_style=FormatStyle.BRACKETS)
            ['project/shot/comp_v1.[001001-001012].exr', 'project/shot/comp_v1.[1001-1002].exr', 'project/shot/comp_v1.[1001-1002].jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtil.convert_to_sequence_format(file_paths, format_style=FormatStyle.BRACES)
            ['project/shot/comp_v1.{001001..001012}.exr', 'project/shot/comp_v1.{1001..1002}.exr', 'project/shot/comp_v1.{1001..1002}.jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtil.convert_to_sequence_format(file_paths, format_style=FormatStyle.BRACKETS_SEPARATE_RANGES)
            ['project/shot/comp_v1.[001001,001011-001012].exr', 'project/shot/comp_v1.[1001-1002].exr', 'project/shot/comp_v1.[1001-1002].jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']

            >>> SequenceFileUtil.convert_to_sequence_format(file_paths, format_style=FormatStyle.BRACKETS_SEPARATE_RANGES, use_unique_padding=False)
            ['project/shot/comp_v1.[001001-001002,001011-001012].exr', 'project/shot/comp_v1.[1001-1002].jpg', 'project/shot/notes.txt', 'project/shot/reference_image.png']
        """
        # Initialize dictionary to store sequences and results
        sequence_dict: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        formatted_paths = set()

        # Parse each file path and categorize them into sequences
        for file_path in file_paths:
            # Extract the base name, sequence number, and extension from the file path
            base_name, sequence_number, extension = SequenceFileUtil.parse_sequence_file_name(file_path)
            if all([base_name, sequence_number, extension]):
                sequence_dict[(base_name, extension)].append(sequence_number)
            # If the file path does not match the sequence pattern, add it directly to the formatted paths
            else:
                formatted_paths.add(file_path)

        # Process each sequence to generate formatted paths
        for (base_name, extension), sequence_numbers in sequence_dict.items():
            # Handle unique padding for each sequence length if specified
            if use_unique_padding:
                # Group sequences by their padding length
                padding_to_sequences = defaultdict(list)
                for seq in sequence_numbers:
                    padding_to_sequences[len(seq)].append(seq)

                # Generate sequence formats for each padding length
                sequence_format_set = {
                    SequenceFileUtil.construct_sequence_file_path(
                        format_style=format_style,
                        base_name=base_name,
                        frame_numbers=sequences,
                        extension=extension,
                        padding=padding,
                    ) for padding, sequences in padding_to_sequences.items()
                }

                formatted_paths.update(sequence_format_set)

            else:
                # Generate a single sequence path format for all sequences
                sequence_path_format = SequenceFileUtil.construct_sequence_file_path(
                    format_style=format_style,
                    base_name=base_name,
                    frame_numbers=sequence_numbers, 
                    extension=extension,
                    padding=len(max(sequence_numbers, key=len)),
                )

                formatted_paths.add(sequence_path_format)

        return sorted(formatted_paths)

    @staticmethod
    def calculate_total_size(sequence_path_format: str) -> int:
        """Calculates the total size of the files in bytes.

        Args:
            sequence_path_format (str): The path to the sequence file.

        Returns:
            int: The total size of the files in bytes.
        """
        file_paths = SequenceFileUtil.extract_paths_from_format(sequence_path_format)

        return sum(map(os.path.getsize, file_paths))

    @staticmethod
    def extract_frame_number(file_name: str) -> Optional[int]:
        """Extracts the frame number from a sequence file name.

        Args:
            file_name (str): The file name to extract the frame number from.

        Returns:
            Optional[str]: The frame number if the file name follows the sequence pattern, otherwise None.
        """
        _, frame_number, _ = SequenceFileUtil.parse_sequence_file_name(file_name)
        return frame_number

    @staticmethod
    def extract_file_info(file_path: str) -> Dict[str, str]:
        """Extracts detailed information about a file, supporting sequence files.

        Args:
            file_path (str): Path to the file or sequence file format for extracting information.

        Returns:
            Dict[str, str]: A dictionary containing detailed file information, including:
                - file_name: The base name of the file.
                - file_path: The full path to the file.
                - file_size: File size in a human-readable format or total size for sequences.
                - file_extension: The file extension.
                - last_modified: The last modification timestamp in `YYYY-MM-DD HH:MM:SS` format.
                - file_owner: The owner of the file.
                - sequence_range: The range of sequence numbers if the file is part of a sequence.
        """
        # Detect if the file path is a sequence path format
        format_style = SequenceFileUtil.detect_sequence_format(file_path)
        if not format_style:
            return FileUtil.extract_file_info(file_path)

        # Extract sequence files from the file path
        sequence_files = SequenceFileUtil.extract_paths_from_format(file_path, format_style=format_style)
        total_size = sum(map(os.path.getsize, sequence_files))
        latest_file = max(sequence_files, key=lambda f: os.stat(f).st_mtime)

        # Retrieve file statistics and details: file info, owner, last modified time, extension, and formatted size
        file_info = os.stat(latest_file)
        owner = FileUtil.get_file_owner(latest_file)
        modified_time = datetime.datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        extension = FileUtil.get_file_extension(latest_file)
        readable_size = FileUtil.format_size(total_size)

        # Get the sequence range directly from the sorted sequence files
        start_frame = SequenceFileUtil.extract_frame_number(sequence_files[0])
        end_frame = SequenceFileUtil.extract_frame_number(sequence_files[-1])

        # Compile the details into a dictionary
        details = {
            "file_name": os.path.basename(latest_file),
            "file_path": file_path,
            "file_size": readable_size,
            "file_extension": extension,
            "last_modified": modified_time,
            "file_owner": owner,
            "sequence_range": f"{start_frame}-{end_frame}",
        }
        return details


if __name__ == '__main__':
    import doctest
    doctest.testmod()

    def construct_file_paths(num_files: int) -> List[str]:
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
    file_paths = construct_file_paths(2000)

    start_time = time.time()
    padded_paths_single = SequenceFileUtil.convert_to_sequence_format(file_paths, distinct_formats=True, format_style=FormatStyle.BRACKETS_SEPARATE_RANGES)
    end_time = time.time()
    print(f"Single format (separate ranges): {padded_paths_single[:10]}...")  # Print only the first 10 for brevity
    print(f"Time taken with single format (separate ranges): {end_time - start_time} seconds")
