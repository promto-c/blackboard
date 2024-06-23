"""
dpx.py

Read Metadata and Image data from 10-bit DPX files in Python 3
Original code from: [jackdoerner/dpx.py](https://gist.github.com/jackdoerner/1c9c48956a1e00a29dbc)
Copyright (c) 2016 Jack Doerner

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
# Type Checking Imports
# ---------------------
from typing import BinaryIO, Dict, Union

# Standard Library Imports
# ------------------------
import struct


# Class Definitions
# -----------------
class DPXMetadata:

    ORIENTATIONS = {
        0: "Left to Right, Top to Bottom",
        1: "Right to Left, Top to Bottom",
        2: "Left to Right, Bottom to Top",
        3: "Right to Left, Bottom to Top",
        4: "Top to Bottom, Left to Right",
        5: "Top to Bottom, Right to Left",
        6: "Bottom to Top, Left to Right",
        7: "Bottom to Top, Right to Left"
    }

    DESCRIPTORS = {
        1: "Red",
        2: "Green",
        3: "Blue",
        4: "Alpha",
        6: "Luma (Y)",
        7: "Color Difference",
        8: "Depth (Z)",
        9: "Composite Video",
        50: "RGB",
        51: "RGBA",
        52: "ABGR",
        100: "Cb, Y, Cr, Y (4:2:2)",
        102: "Cb, Y, Cr (4:4:4)",
        103: "Cb, Y, Cr, A (4:4:4:4)"
    }

    PACKINGS = {
        0: "Packed into 32-bit words",
        1: "Filled to 32-bit words, Padding First",
        2: "Filled to 32-bit words, Padding Last"
    }

    ENCODINGS = {
        0: "No encoding",
        1: "Run Length Encoding"
    }

    TRANSFERS = {
        1: "Printing Density",
        2: "Linear",
        3: "Logarithmic",
        4: "Unspecified Video",
        5: "SMPTE 274M",
        6: "ITU-R 709-4",
        7: "ITU-R 601-5 system B or G",
        8: "ITU-R 601-5 system M",
        9: "Composite Video (NTSC)",
        10: "Composite Video (PAL)",
        11: "Z (Linear Depth)",
        12: "Z (Homogenous Depth)"
    }

    COLORIMETRIES = {
        1: "Printing Density",
        4: "Unspecified Video",
        5: "SMPTE 274M",
        6: "ITU-R 709-4",
        7: "ITU-R 601-5 system B or G",
        8: "ITU-R 601-5 system M",
        9: "Composite Video (NTSC)",
        10: "Composite Video (PAL)"
    }

    PROPERTYMAP = [
        # (field name, offset, length, type)

        ('magic', 0, 4, 'magic'),
        ('offset', 4, 4, 'I'),
        ('dpx_version', 8, 8, 'utf8'),
        ('file_size', 16, 4, 'I'),
        ('ditto', 20, 4, 'I'),
        ('filename', 36, 100, 'utf8'),
        ('timestamp', 136, 24, 'utf8'),
        ('creator', 160, 100, 'utf8'),
        ('project_name', 260, 200, 'utf8'),
        ('copyright', 460, 200, 'utf8'),
        ('encryption_key', 660, 4, 'I'),

        ('orientation', 768, 2, 'H'),
        ('image_element_count', 770, 2, 'H'),
        ('width', 772, 4, 'I'),
        ('height', 776, 4, 'I'),

        ('data_sign', 780, 4, 'I'),
        ('descriptor', 800, 1, 'B'),
        ('transfer_characteristic', 801, 1, 'B'),
        ('colorimetry', 802, 1, 'B'),
        ('depth', 803, 1, 'B'),
        ('packing', 804, 2, 'H'),
        ('encoding', 806, 2, 'H'),
        ('line_padding', 812, 4, 'I'),
        ('image_padding', 816, 4, 'I'),
        ('image_element_description', 820, 32, 'utf8'),

        ('input_device_name', 1556, 32, 'utf8'),
        ('input_device_sn', 1588, 32, 'utf8')
    ]

    @staticmethod
    def read_metadata(file_obj: BinaryIO) -> Dict[str, Union[str, int]]:
        """Reads DPX metadata from a file object.

        Args:
            file_obj: A file object to read the DPX metadata from.

        Returns:
            A dictionary containing the DPX metadata, or None if the file is not a valid DPX file.
        """
        file_obj.seek(0)
        bytes_read = file_obj.read(4)
        magic = bytes_read.decode(encoding='UTF-8')
        if magic not in ["SDPX", "XPDS"]:
            return None
        endianness = ">" if magic == "SDPX" else "<"

        metadata = {}

        for prop in DPXMetadata.PROPERTYMAP:
            file_obj.seek(prop[1])
            bytes_read = file_obj.read(prop[2])
            if prop[3] == 'magic':
                metadata[prop[0]] = bytes_read.decode(encoding='UTF-8')
                metadata['endianness'] = "be" if magic == "SDPX" else "le"
            elif prop[3] == 'utf8':
                try:
                    metadata[prop[0]] = bytes_read.decode(encoding='UTF-8')
                except UnicodeDecodeError:
                    metadata[prop[0]] = bytes_read.decode(encoding='ISO-8859-1')
            elif prop[3] == 'B':
                metadata[prop[0]] = struct.unpack(endianness + 'B', bytes_read)[0]
            elif prop[3] == 'H':
                metadata[prop[0]] = struct.unpack(endianness + 'H', bytes_read)[0]
            elif prop[3] == 'I':
                metadata[prop[0]] = struct.unpack(endianness + 'I', bytes_read)[0]

        return metadata
