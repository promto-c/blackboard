# Type Checking Imports
# ---------------------
from typing import Optional, Union, BinaryIO, Dict, Union, Tuple

# Standard Library Imports
# ------------------------
import os, math
from pathlib import Path
import numpy as np
from numbers import Number
from functools import lru_cache

# Third Party Imports
# -------------------
try:
    import OpenEXR
    import Imath
except ImportError:
    IS_SUPPORT_OPENEXR_LIB = False
else:
    IS_SUPPORT_OPENEXR_LIB = True
import cv2

# Local Imports
# -------------
from blackboard.utils.path_utils import PathSequence
from blackboard.utils.file_path_utils import FileUtil
from blackboard.utils.external.dpx_metadata_reader import DPXMetadata


# Class Definitions
# -----------------
class ImageReader:

    MOVIE_CLIP_FORMATS = ['mov', 'mp4', 'avi']

    @classmethod
    def read_image(cls, file_path: Union[str, Path]):
        """Reads an image or video file based on its extension.

        This method determines the type of the file based on its extension and calls the appropriate
        reading function. It supports reading standard image formats as well as specific video formats.
        If the file does not exist or the extension is not recognized, it raises an error.

        Args:
            file_path: A string path to the image or video file.

        Returns:
            The image or a video frame data read from the file.

        Raises:
            FileNotFoundError: If the file does not exist or is not a file.
            ValueError: If the file extension is not supported by any read method.

        Note:
            Supported image formats include 'exr' and 'dpx'. Supported video formats include 'mov',
            'mp4', and 'avi'. If an unsupported format is provided, the method defaults to using OpenCV's
            image reading capabilities, which supports a wide range of image formats.
        """
        if isinstance(file_path, Path):
            file_path = file_path.as_posix()

        # Check if the path is a file
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The path {file_path} does not exist or is not a file.")
    
        file_type_handlers = {
                'exr': cls.read_exr if IS_SUPPORT_OPENEXR_LIB else cls.cv2_read_image,
                'dpx': DpxReader.read_dpx,
            }

        file_extension = FileUtil.get_file_extension(file_path)

        # Determine if the video file type supports
        if file_extension in cls.MOVIE_CLIP_FORMATS:
            return cls.read_video(file_path)

        # Lookup read method for given file extension
        read_method = file_type_handlers.get(file_extension, cls.cv2_read_image)

        return read_method(file_path)

    @staticmethod
    def cv2_read_image(file_path: str):
        # Read file using OpenCV
        try:
            image_data = cv2.imread(file_path, cv2.IMREAD_ANYCOLOR)
        except cv2.error:
            image_data = None

        # Check if the image was successfully loaded
        if image_data is None:
            return image_data
            # raise FileNotFoundError(f"Unable to load image at {file_path}")

        image_data = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)

        return image_data

    @classmethod
    def read_exr(cls, image_path: str) -> np.ndarray:
        """Read an EXR image from file and return it as a NumPy array.

        Args:
            image_path (str): The path to the EXR image file.

        Returns:
            np.ndarray: The image data as a NumPy array.

        """
        if not os.path.isfile(image_path):
            return

        # Open the EXR file for reading
        exr_file = OpenEXR.InputFile(image_path)

        # Get the image header
        header = exr_file.header()

        # Get the data window (bounding box) and channels of the image
        data_window = header['dataWindow']
        channels = header['channels']

        # Calculate the width and height of the image
        width = data_window.max.x - data_window.min.x + 1
        height = data_window.max.y - data_window.min.y + 1

        # Determine the channel keys
        channel_keys = 'RGB' if len(channels.keys()) == 3 else channels.keys()

        # Read all channels at once
        channel_data = exr_file.channels(channel_keys, Imath.PixelType(Imath.PixelType.FLOAT))

        # Using list comprehension to transform the channel data
        channel_data = [
            np.frombuffer(data, dtype=np.float32).reshape(height, width)
            for data in channel_data
        ]

        # Convert to NumPy array
        image_data = np.array(channel_data)

        return image_data.transpose(1, 2, 0)

    @staticmethod
    def read_video(file_path: str, frame_number: Optional[int] = None):
        """Generalized method to read a specific frame from a video file.

        Args:
            file_path (str): Path to the video file.
            frame_number (int): Frame number to read, defaults to 0 (first frame).

        Returns:
            np.ndarray: Image data as a NumPy array.
        """
        cap = cv2.VideoCapture(file_path)
        if frame_number is not None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame")
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame


class DpxReader:

    _DEPTH_PACKING_TO_METHOD: Dict[Tuple[int, int], str] = {
        (8, 0): 'read_dpx_8bit',
        (8, 1): 'read_dpx_8bit',
        # (10, 0): 'read_dpx_10bit_packed',
        (10, 1): 'read_dpx_10bit_filled',
        (12, 0): 'read_dpx_12bit_packed',
        (12, 1): 'read_dpx_12bit_filled',
        (16, 0): 'read_dpx_16bit',
        (16, 1): 'read_dpx_16bit',
    }

    @staticmethod
    def read_dpx_metadata(file: BinaryIO):
        return DPXMetadata.read_metadata(file)

    @classmethod
    def read_dpx(cls, image_path: str) -> np.ndarray:
        with open(image_path, "rb") as file:
            meta = cls.read_dpx_metadata(file)
            if meta is None:
                raise ValueError("Invalid DPX file")

            encoding = meta['encoding']
            if encoding != 0:
                raise NotImplementedError("RLE compression is not supported")

            depth = meta['depth']
            packing = meta['packing']

            reader_method_name = cls._DEPTH_PACKING_TO_METHOD.get((depth, packing))
            if reader_method_name is None:
                raise ValueError("Unsupported DPX format")

            reader_method = getattr(cls, reader_method_name)
            return reader_method(file, meta)

    @staticmethod
    def read_dpx_8bit(file_obj: BinaryIO, meta: Dict[str, Union[str, int]]) -> np.ndarray:
        width = meta['width']
        height = meta['height']
        offset = meta['offset']
        descriptor = meta['descriptor']

        # Determine the number of channels from the descriptor
        descriptor_channels = {
            50: 3,  # RGB
            51: 4,  # RGBA
            52: 4,  # ABGR
        }

        if descriptor not in descriptor_channels:
            raise ValueError("Unsupported DPX descriptor")

        components_per_pixel = descriptor_channels[descriptor]

        file_obj.seek(offset)
        raw = np.fromfile(file_obj, dtype=np.uint8, count=width * height * components_per_pixel)

        image_data = raw.reshape(height, width, components_per_pixel)

        return image_data

    @staticmethod
    def read_dpx_10bit_filled(file_obj: BinaryIO, meta: Dict[str, Union[str, int]]) -> np.ndarray:
        width = meta['width']
        height = meta['height']
        offset = meta['offset']

        file_obj.seek(offset)
        raw = np.fromfile(file_obj, dtype=np.int32, count=width * height)

        raw = raw.reshape(height, width)

        if meta['endianness'] == 'be':
            raw.byteswap(True)

        image_data = np.array([raw >> 22, raw >> 12, raw >> 2], dtype=np.uint16)
        image_data &= 0x3FF

        # NOTE: to uint8
        # image_data = (image_data >> 2).astype(np.uint8)

        # Convert to float32 and normalize
        image_data = image_data.astype(np.float32)
        image_data /= 0x3FF

        return image_data.transpose(1, 2, 0)

    @staticmethod
    def read_dpx_12bit_packed(file_obj: BinaryIO, meta: Dict[str, Union[str, int]]) -> np.ndarray:
        width = meta['width']
        height = meta['height']
        offset = meta['offset']
        descriptor = meta['descriptor']

        # Determine the number of channels from the descriptor
        descriptor_channels = {
            50: 3,  # RGB
            51: 4,  # RGBA
            52: 4,  # ABGR
        }

        if descriptor not in descriptor_channels:
            raise ValueError("Unsupported DPX descriptor")

        components_per_pixel = descriptor_channels[descriptor]

        file_obj.seek(offset)

        words_per_line = math.ceil(width * 9 / 4)
        raw = np.fromfile(file_obj, dtype=np.uint16, count=words_per_line * height)

        word_lines = raw.reshape(height, words_per_line)

        if meta['endianness'] == 'be':
            raw.byteswap(True)

        # Extract 8 components from 6 halfwords (read as 16bit)
        # Word 1: | B05 B06 B07 B08 B09 B10 B11 B12|G01 G02 G03 G04 G05 G06 G07 G08 || G09 G10 G11 G12|R01 R02 R03 R04 R05 R06 R07 R08 R09 R10 R11 R12 |
        # Word 2: | B09 B10 B11 B12|G01 G02 G03 G04 G05 G06 G07 G08 G09 G10 G11 G12 || R01 R02 R03 R04 R05 R06 R07 R08 R09 R10 R11 R12|B01 B02 B03 B04 |
        # Word 3: | G01 G02 G03 G04 G05 G06 G07 G08 G09 G10 G11 G12|R01 R02 R03 R04 || R05 R06 R07 R08 R09 R10 R11 R12|B01 B02 B03 B04 B05 B06 B07 B08 |
        image_data = np.array([
            (word_lines[:, 1::6] & 0xFFF),
            ((word_lines[:, 0::6] & 0xFF) << 4) | (word_lines[:, 1::6] >> 12),
            ((word_lines[:, 3::6] & 0xF) << 8) | (word_lines[:, 0::6] >> 8),
            (word_lines[:, 3::6] >> 4),
            (word_lines[:, 2::6] & 0xFFF),
            ((word_lines[:, 5::6] & 0xFF) << 4) | (word_lines[:, 2::6] >> 12),
            ((word_lines[:, 4::6] & 0xF) << 8) | (word_lines[:, 5::6] >> 8),
            (word_lines[:, 4::6] >> 4 & 0xFFF)
        ], dtype=np.uint16).transpose(1, 2, 0).reshape(height, width, components_per_pixel)  # Reshape to (height, width, components_per_pixel)

        # Convert to float32 and normalize
        image_data = image_data.astype(np.float32)
        image_data /= 0x0FFF

        return image_data

    @staticmethod
    def read_dpx_12bit_filled(file_obj: BinaryIO, meta: Dict[str, Union[str, int]]) -> np.ndarray:
        width = meta['width']
        height = meta['height']
        offset = meta['offset']
        descriptor = meta['descriptor']

        # Determine the number of channels from the descriptor
        descriptor_channels = {
            50: 3,  # RGB
            51: 4,  # RGBA
            52: 4,  # ABGR
        }

        if descriptor not in descriptor_channels:
            raise ValueError("Unsupported DPX descriptor")

        components_per_pixel = descriptor_channels[descriptor]

        file_obj.seek(offset)
        raw = np.fromfile(file_obj, dtype=np.uint16, count=width * height * components_per_pixel)

        raw = raw.reshape(height, width, components_per_pixel)

        if meta['endianness'] == 'be':
            raw.byteswap(True)

        # Extract the 12-bit pixel values
        image_data = raw >> 4  # Right shift by 4 bits to discard the lower 4 bits

        # Convert to float32 and normalize
        image_data = image_data.astype(np.float32)
        image_data /= 0xFFF

        return image_data

    @staticmethod
    def read_dpx_16bit(file_obj: BinaryIO, meta: Dict[str, Union[str, int]]) -> np.ndarray:
        width = meta['width']
        height = meta['height']
        offset = meta['offset']
        descriptor = meta['descriptor']

        # Determine the number of channels from the descriptor
        descriptor_channels = {
            50: 3,  # RGB
            51: 4,  # RGBA
            52: 4,  # ABGR
        }

        if descriptor not in descriptor_channels:
            raise ValueError("Unsupported DPX descriptor")

        components_per_pixel = descriptor_channels[descriptor]

        file_obj.seek(offset)
        raw = np.fromfile(file_obj, dtype=np.uint16, count=width * height * components_per_pixel)

        raw = raw.reshape(height, width, components_per_pixel)

        if meta['endianness'] == 'be':
            raw.byteswap(True)

        # Convert to float32 and normalize
        image_data = raw.astype(np.float32)
        image_data /= 0xFFFF

        return image_data

class ImageSequence:

    def __init__(self, input_path: str) -> None:
        self.input_path = input_path

        # Set up the initial attributes
        self._setup_attributes()

    def _setup_attributes(self):
        self.path_sequence = PathSequence(self.input_path)

    @lru_cache(maxsize=400)
    def read_image(self, file_path: str):
        return ImageReader.read_image(file_path)

    def get_image_data(self, frame: Number):
        file_path = self.get_frame_path(frame)
        return self.read_image(file_path)
    
    # From Path Sequence
    # ------------------
    def frame_range(self):
        return self.path_sequence.get_frame_range()

    def get_frame_path(self, frame: Number):
        return self.path_sequence.get_frame_path(frame)
