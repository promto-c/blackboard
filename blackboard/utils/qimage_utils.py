# Standard Library Imports
# ------------------------
import os
from functools import lru_cache

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets

import cv2
import numpy as np

# Local Imports
# -------------
from blackboard.utils.image_utils import ImageReader


# Class Definitions
# -----------------
class ThumbnailUtils:
    """Utility class for creating and managing image thumbnails.

    This class provides methods for creating `QPixmap` objects from image data,
    as well as for generating cached thumbnails for image files.

    Methods:
        create_qpixmap_from_image_data(image_data: np.ndarray, desired_height: int) -> QtGui.QPixmap:
            Creates a `QPixmap` from a NumPy array, scaling it to a specified height.
        
        get_pixmap_thumbnail(file_path: str, desired_height: int) -> QtGui.QPixmap:
            Generates a cached thumbnail `QPixmap` for a given image file path.
    """

    @staticmethod
    def create_qpixmap_from_image_data(image_data: 'np.ndarray', desired_height: int = 64) -> QtGui.QPixmap:
        """Creates a QPixmap from a NumPy array of various data types, scaling it down to
        a thumbnail size for improved performance.

        Args:
            image_data (np.ndarray): The image data as a NumPy array.
            desired_height (int): The desired height of the thumbnail in pixels.

        Returns:
            QPixmap: The QPixmap created from the image data.
        """
        # Check if the image data is valid
        if image_data is None:
            return QtGui.QPixmap()

        # Calculate the new width to maintain aspect ratio
        original_height, original_width = image_data.shape[:2]
        aspect_ratio = original_width / original_height
        new_width = int(desired_height * aspect_ratio)

        # Resize the image to the new dimensions for performance
        img_resized = cv2.resize(image_data, (new_width, desired_height), interpolation=cv2.INTER_AREA)

        # Normalize and convert the data to 8-bit per channel for QImage compatibility
        if img_resized.dtype != np.uint8:
            # Normalize data types to float64 for consistent processing
            norm_img = img_resized.astype(np.float64)
            
            # Scale the normalized data to the 0-255 range
            norm_img -= norm_img.min()
            if norm_img.max() != 0:
                norm_img *= (255.0 / norm_img.max())
            img_8bit = norm_img.astype(np.uint8)
        else:
            img_8bit = img_resized

        # Ensure the image has 3 channels (RGB)
        if len(img_8bit.shape) == 2 or img_8bit.shape[2] == 1:
            img_8bit = np.stack([img_8bit.squeeze()] * 3, axis=-1)
        
        # Convert the image data to QImage
        h, w, ch = img_8bit.shape
        bytes_per_line = ch * w
        q_img = QtGui.QImage(img_8bit.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)

        return QtGui.QPixmap.fromImage(q_img)

    @classmethod
    @lru_cache(maxsize=1024)
    def get_pixmap_thumbnail(cls, file_path: str, desired_height: int = 64) -> QtGui.QPixmap:
        """Generates a thumbnail QPixmap for a given image file path.

        Args:
            file_path (str): Path to the image file.
            desired_height (int): Desired height of the thumbnail in pixels.

        Returns:
            QtGui.QPixmap: The generated thumbnail as a QPixmap.
        """
        # Check if the file exists
        if not os.path.isfile(file_path):
            # TODO: Create pixmap to shown that file not found.
            return QtGui.QPixmap()

        # Load the image
        pixmap = QtGui.QPixmap(file_path)

        if pixmap.isNull():
            # Attempt to read the image using a custom method for unsupported formats
            image_data = ImageReader.read_image(file_path)
            if image_data is not None:
                pixmap = cls.create_qpixmap_from_image_data(image_data, desired_height=desired_height)
            else:
                file_info = QtCore.QFileInfo(file_path)
                file_icon_provider = QtWidgets.QFileIconProvider()
                pixmap = file_icon_provider.icon(file_info).pixmap(desired_height)

        else:
            # Update the pixmap with the scaled version
            pixmap = pixmap.scaledToHeight(desired_height, QtCore.Qt.TransformationMode.FastTransformation)

        return pixmap

class ThumbnailLoader(QtCore.QObject):
    """Asynchronous loader for generating and emitting thumbnail images.

    This class emits a signal when the thumbnail is successfully loaded.

    Attributes:
        file_path (str): Path to the image file.
        thumbnail_height (int): Desired height of the thumbnail in pixels.

    Signals:
        thumbnail_loaded (str, QtGui.QPixmap): Emitted when the thumbnail is loaded.
    """

    thumbnail_loaded = QtCore.Signal(str, QtGui.QPixmap)

    def __init__(self, file_path: str, desired_height: int = 64) -> None:
        """Initialize the ThumbnailLoader with the file path and thumbnail height.

        Args:
            file_path (str): Path to the image file.
            desired_height (int): Desired height of the thumbnail in pixels.
        """
        super().__init__()
        self.file_path = file_path
        self.desired_height = desired_height

    def run(self) -> None:
        """Run the thumbnail loading process and emit the thumbnail_loaded signal."""
        pixmap = ThumbnailUtils.get_pixmap_thumbnail(self.file_path, self.desired_height)
        if not pixmap.isNull():
            self.thumbnail_loaded.emit(self.file_path, pixmap)
