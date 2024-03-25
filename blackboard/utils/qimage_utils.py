import cv2
import numpy as np
from functools import lru_cache
from qtpy import QtGui, QtCore, QtWidgets

from blackboard.utils.image_utils import ImageReader

class ThumbnailUtils:

    @staticmethod
    def create_qpixmap_from_image_data(image_data: np.ndarray, desired_height: int = 64):
        """
        Creates a QPixmap from a NumPy array of various data types, scaling it down to
        a thumbnail size for improved performance.

        Args:
            image_data (np.ndarray): The image data as a NumPy array.
            thumbnail_size (tuple): The desired thumbnail size as (width, height).

        Returns:
            QPixmap: The QPixmap created from the image data.
        """
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
        
        h, w, ch = img_8bit.shape
        bytes_per_line = ch * w
        q_img = QtGui.QImage(img_8bit.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)

        return QtGui.QPixmap.fromImage(q_img)

    @classmethod
    @lru_cache(maxsize=1024)
    def get_pixmap_thumbnail(cls, file_path, desired_height: int = 64):
        """
        Generates a thumbnail QPixmap for a given image file path.

        Args:
            file_path (str): Path to the image file.
            desired_height (int): Desired height of the thumbnail in pixels.

        Returns:
            QtGui.QPixmap: The generated thumbnail as a QPixmap.
        """
        pixmap = QtGui.QPixmap(file_path)

        if pixmap.isNull():
            try:
                # Attempt to read the image using a custom method for unsupported formats
                image_data = ImageReader.read_image(file_path)  # Ensure this method is defined
                if image_data is not None:
                    pixmap = cls.create_qpixmap_from_image_data(image_data, desired_height=desired_height)
                else:
                    file_info = QtCore.QFileInfo(file_path)
                    file_icon_provider = QtWidgets.QFileIconProvider()
                    pixmap = file_icon_provider.icon(file_info).pixmap(desired_height)

            except FileNotFoundError:
                # TODO: Create pixmap to shown that file not found.
                ...
        else:
            # Update the pixmap with the scaled version
            pixmap = pixmap.scaledToHeight(desired_height, QtCore.Qt.TransformationMode.FastTransformation)

        return pixmap
