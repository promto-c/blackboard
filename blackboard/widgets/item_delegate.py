from typing import Dict, List, Optional, Union
from numbers import Number
import datetime
import dateutil.parser as date_parser

from qtpy import QtCore, QtGui, QtWidgets

from blackboard.utils.color_utils import ColorUtils
from blackboard.utils.file_path_utils import SequenceFileUtil
from blackboard.utils.qimage_utils import ThumbnailUtils, ThumbnailLoader
from blackboard.utils.thread_pool import ThreadPoolManager, RunnableTask


def create_pastel_color(color: QtGui.QColor, saturation: float = 0.4, value: float = 0.9) -> QtGui.QColor:
    """Create a pastel version of the given color.

    Args:
        color (QtGui.QColor): The original color.
        saturation (float): The desired saturation factor (default: 0.4).
        value (float): The desired value/brightness factor (default: 0.9).

    Returns:
        QtGui.QColor: The pastel color.
    """
    h, s, v, a = color.getHsvF()

    # Decrease saturation and value to achieve a more pastel look
    s *= saturation
    v *= value

    pastel_color = QtGui.QColor.fromHsvF(h, s, v, a)
    return pastel_color

def parse_date(date_string: str) -> Optional[datetime.datetime]:
    """Parse the given date string into a datetime.datetime object.

    Args:
        date_string: The date string to parse.

    Returns:
        The parsed datetime object, or None if parsing fails.
    """
    try:
        parsed_date = date_parser.parse(date_string)
        return parsed_date
    except ValueError:
        return None

class HighlightItemDelegate(QtWidgets.QStyledItemDelegate):
    """Custom item delegate class that highlights the rows specified by the `target_model_indexes` list.
    """
    # List of target model index for highlighting
    target_model_indexes: List[QtCore.QModelIndex] = list()
    target_focused_model_indexes: List[QtCore.QModelIndex] = list()
    target_selected_model_indexes: List[QtCore.QModelIndex] = list()

    # Define default highlight color
    DEFAULT_HIGHLIGHT_COLOR = QtGui.QColor(165, 165, 144, 65)
    DEFAULT_SELECTION_COLOR = QtGui.QColor(102, 119, 119, 51)
    
    def __init__(self, parent=None, highlight_color: QtGui.QColor = DEFAULT_HIGHLIGHT_COLOR, 
                 selection_color: QtGui.QColor = DEFAULT_SELECTION_COLOR):
        """Initialize the highlight item delegate.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
            color (QtGui.QColor, optional): The color to use for highlighting. Defaults to a light grayish-yellow.
        """
        # Initialize the super class
        super().__init__(parent)

        # Set the color attribute
        self.highlight_color = highlight_color
        self.selection_color = selection_color

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, model_index: QtCore.QModelIndex):
        """Paint the delegate.
        
        Args:
            painter (QtGui.QPainter): The painter to use for drawing.
            option (QtWidgets.QStyleOptionViewItem): The style option to use for drawing.
            model_index (QtCore.QModelIndex): The model index of the item to be painted.
        """
        # Check if the current model index is not in the target list
        if model_index not in self.target_selected_model_indexes and model_index not in self.target_model_indexes:
            # If not, paint the item normally using the parent implementation
            super().paint(painter, option, model_index)
            return

        # ...
        color = painter.background().color()

        # ...
        if model_index in self.target_model_indexes:
            color = ColorUtils.blend_colors(color, self.highlight_color)
        if model_index in self.target_focused_model_indexes:
            color = ColorUtils.blend_colors(color, self.highlight_color)
        if model_index in self.target_selected_model_indexes:
            color = ColorUtils.blend_colors(color, self.selection_color)

        # If the current model index is in the target list, set the background color and style
        option.backgroundBrush.setColor(color)
        option.backgroundBrush.setStyle(QtCore.Qt.BrushStyle.SolidPattern)

        # Fill the rect with the background brush
        painter.fillRect(option.rect, option.backgroundBrush)

        # Paint the item normally using the parent implementation
        super().paint(painter, option, model_index)

    def clear(self):
        # Reset the previous target model indexes
        self.target_model_indexes.clear()
        self.target_focused_model_indexes.clear()

class AdaptiveColorMappingDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate class for adaptive color mapping in Qt items.

    This delegate maps values to colors based on specified rules and color definitions.
    It provides functionality to map numerical values, keywords, and date strings to colors.

    Class Constants:
        COLOR_DICT: A dictionary that maps color names to corresponding QColor objects.

    Attributes:
        min_value (Optional[Number]): The minimum value of the range.
        max_value (Optional[Number]): The maximum value of the range.
        min_color (QtGui.QColor): The color corresponding to the minimum value.
        max_color (QtGui.QColor): The color corresponding to the maximum value.
        keyword_color_dict (Dict[str, QtGui.QColor]): A dictionary that maps keywords to specific colors.
        date_format (str): The date format string.
        date_color_dict (Dict[str, QtGui.QColor]): A dictionary that caches colors for date values.
    """
    # Class constants
    # ---------------
    COLOR_DICT = {
        'pastel_green': create_pastel_color(QtGui.QColor(65, 144, 0)),
        'pastel_red': create_pastel_color(QtGui.QColor(144, 0, 0)),
        'red': QtGui.QColor(183, 26, 28),
        'light_red': QtGui.QColor(183, 102, 77),
        'light_green': QtGui.QColor(170, 140, 88),
        'dark_green': QtGui.QColor(82, 134, 74),
        'green': QtGui.QColor(44, 65, 44),
        'blue': QtGui.QColor(0, 120, 215),
    }

    # Initialization and Setup
    # ------------------------
    def __init__(
        self,
        parent: Optional[QtCore.QObject] = None,
        min_value: Optional[Number] = None,
        max_value: Optional[Number] = None,
        min_color: QtGui.QColor = COLOR_DICT['pastel_green'],
        max_color: QtGui.QColor = COLOR_DICT['pastel_red'],
        keyword_color_dict: Dict[str, QtGui.QColor] = dict(),
        date_color_dict: Dict[str, QtGui.QColor] = dict(),
        date_format: str = '%Y-%m-%d',
    ):
        """Initialize the AdaptiveColorMappingDelegate.

        Args:
            parent (QtCore.QObject, optional): The parent object. Default is None.
            min_value (Number, optional): The minimum value of the range. Default is None.
            max_value (Number, optional): The maximum value of the range. Default is None.
            min_color (QtGui.QColor, optional): The color corresponding to the minimum value.
                Default is a pastel green.
            max_color (QtGui.QColor, optional): The color corresponding to the maximum value.
                Default is a pastel red.
            keyword_color_dict (Dict[str, QtGui.QColor], optional): A dictionary that maps
                keywords to specific colors. Default is an empty dictionary.
            date_format (str, optional): The date format string. Default is '%Y-%m-%d'.
        """
        # Initialize the super class
        super().__init__(parent)

        # Store the arguments
        self.min_value = min_value
        self.max_value = max_value
        self.min_color = min_color
        self.max_color = max_color
        self.keyword_color_dict = keyword_color_dict
        self.date_color_dict = date_color_dict
        self.date_format = date_format

    # Private Methods
    # ---------------
    def _interpolate_color(self, value: Number) -> QtGui.QColor:
        """Interpolate between the min_color and max_color based on the given value.

        Args:
            value (Number): The value within the range.

        Returns:
            QtGui.QColor: The interpolated color.
        """
        if not value:
            return QtGui.QColor()

        # Normalize the value between 0 and 1
        normalized_value = (value - self.min_value) / (self.max_value - self.min_value)

        # Interpolate between the min_color and max_color based on the normalized value
        color = QtGui.QColor()
        color.setRgbF(
            self.min_color.redF() + (self.max_color.redF() - self.min_color.redF()) * normalized_value,
            self.min_color.greenF() + (self.max_color.greenF() - self.min_color.greenF()) * normalized_value,
            self.min_color.blueF() + (self.max_color.blueF() - self.min_color.blueF()) * normalized_value
        )

        return color

    def _get_keyword_color(self, keyword: str, is_pastel_color: bool = True) -> QtGui.QColor:
        """Get the color associated with a keyword.

        Args:
            keyword (str): The keyword for which to retrieve the color.

        Returns:
            QtGui.QColor: The color associated with the keyword.
        """
        if not keyword:
            return QtGui.QColor()

        # Check if the keyword color is already cached in the keyword_color_dict
        if keyword in self.keyword_color_dict:
            return self.keyword_color_dict[keyword]

        # Generate a new color for the keyword
        hue = (hash(keyword) % 360) / 360
        saturation, value = 0.6, 0.6
        keyword_color = QtGui.QColor.fromHsvF(hue, saturation, value)

        # Optionally create a pastel version of the color
        keyword_color = create_pastel_color(keyword_color, 0.6, 0.9) if is_pastel_color else keyword_color

        # Cache the color in the keyword_color_dict
        self.keyword_color_dict[keyword] = keyword_color

        return keyword_color

    def _get_deadline_color(self, difference: int) -> QtGui.QColor:
        """Get the color based on the difference from the current date.

        Args:
            difference (int): The difference in days from the current date.

        Returns:
            QtGui.QColor: The color corresponding to the difference.
        """
        color_palette = {
            0: self.COLOR_DICT['red'],              # Red (today's deadline)
            1: self.COLOR_DICT['light_red'],        # Slightly lighter tone for tomorrow
            2: self.COLOR_DICT['light_green'],      # Light green for the day after tomorrow
            **{diff: self.COLOR_DICT['dark_green'] 
               for diff in range(3, 8)},            # Dark green for the next 3-7 days
        }

        if difference >= 7:
            # Green for dates more than 7 days away
            return self.COLOR_DICT['green']
        else:
            # Blue for other dates
            return color_palette.get(difference, self.COLOR_DICT['blue'])

    def _get_date_color(self, date_value: str, is_pastel_color: bool = True) -> QtGui.QColor:
        """Get the color based on the given date value.

        Args:
            date_value (str): The date string to determine the color for.
            is_pastel_color (bool, optional): Whether to create a pastel version of the color.
                Default is True.

        Returns:
            QtGui.QColor: The color corresponding to the date.
        """
        # Check if the date color is already cached in the date_color_dict
        if date_value in self.date_color_dict:
            return self.date_color_dict[date_value]

        # Get the current date
        today = datetime.date.today()

        # If a date format is specified, use datetime.strptime to parse the date string
        if self.date_format:
            # Use datetime.strptime to parse the date string
            parsed_date = datetime.datetime.strptime(date_value, self.date_format).date()
        else:
            # Otherwise, use the parse_date function to parse the date string
            parsed_date = parse_date(date_value).date()

        # Calculate the difference in days between the parsed date and today
        difference = (parsed_date - today).days

        # Get the color based on the difference in days
        date_color = self._get_deadline_color(difference)
        # Optionally create a pastel version of the color
        date_color = create_pastel_color(date_color, 0.6, 0.9) if is_pastel_color else date_color

        # Cache the color in the date_color_dict
        self.date_color_dict[date_value] = date_color

        return date_color

    # Event Handling or Override Methods
    # ----------------------------------
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, model_index: QtCore.QModelIndex):
        """Paint the delegate.
        
        Args:
            painter (QtGui.QPainter): The painter to use for drawing.
            option (QtWidgets.QStyleOptionViewItem): The style option to use for drawing.
            model_index (QtCore.QModelIndex): The model index of the item to be painted.
        """
        # Retrieve the value from the model using UserRole
        value = model_index.data(QtCore.Qt.ItemDataRole.UserRole)

        if isinstance(value, Number):
            # If the value is numerical, use _interpolate_color
            color = self._interpolate_color(value)
        elif isinstance(value, str):
            if not parse_date(value):
                # If the value is a string and not a date, use _get_keyword_color
                color = self._get_keyword_color(value)
            else:
                # If the value is a date string, use _get_date_color
                color = self._get_date_color(value)
        else:
            # For other data types, paint the item normally
            super().paint(painter, option, model_index)
            return

        # If the current model index is in the target list, set the background color and style
        option.backgroundBrush.setColor(color)
        option.backgroundBrush.setStyle(QtCore.Qt.BrushStyle.SolidPattern)

        # Fill the rect with the background brush
        painter.fillRect(option.rect, option.backgroundBrush)

        # Paint the item normally using the parent implementation
        super().paint(painter, option, model_index)

class HighlightTextDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that highlights text matches within items."""
    
    def __init__(self, parent=None, highlight_text: str = ''):
        """Initializes the HighlightDelegate with optional highlighting text.
        
        Args:
            parent: The parent widget.
            highlight_text: The text to highlight within the delegate's items.
        """
        super().__init__(parent)
        self.highlight_text = highlight_text

        # Get the QApplication instance (creating a new one if necessary) and retrieve the frame margin for highlight positioning.
        app_instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.spacing = app_instance.style().pixelMetric(QtWidgets.QStyle.PixelMetric.PM_FocusFrameHMargin)

        # Highlight color
        self.highlight_color = QtGui.QColor(QtCore.Qt.yellow)
        self.highlight_color.setAlpha(65)
    
        # Create a pen with the custom color and set its style to DashLine
        pen_color = QtGui.QColor("#777")
        self.pen = QtGui.QPen(pen_color)
        self.pen.setStyle(QtCore.Qt.PenStyle.DashLine)

    def set_highlight_text(self, text: str):
        """Updates the delegate with the current filter text.
        """
        self.highlight_text = text

    def paint(self, painter, option, index):
        """Paints the delegate's items, highlighting matches of the highlight text.
        
        Args:
            painter: The QPainter instance used for painting the item.
            option: The style options for the item.
            index: The index of the item in the model.
        """
        if self.highlight_text:
            # Custom painting code here
            text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            painter.save()

            # Apply the highlight color and pen to the painter
            painter.setBrush(self.highlight_color)
            painter.setPen(self.pen)

            # Find all occurrences of the highlight text
            start_pos = 0
            while True:
                start_pos = text.lower().find(self.highlight_text.lower(), start_pos)
                if start_pos == -1:
                    break
                end_pos = start_pos + len(self.highlight_text)

                # Calculate the bounding rect for the highlight text
                font_metrics = painter.fontMetrics()
                before_text_width = font_metrics.width(text[:start_pos])
                highlight_text_width = font_metrics.width(text[start_pos:end_pos])

                # Adjust highlight_rect to include padding
                highlight_rect = QtCore.QRect(option.rect.left() + before_text_width + self.spacing, option.rect.top(),
                                            highlight_text_width + self.spacing, option.rect.height())
        
                radius = 2
                # Fill the background of the highlight text
                painter.drawRoundedRect(highlight_rect, radius, radius)
                start_pos += len(self.highlight_text)

            painter.restore()

        # Call the base class to do the default painting
        super().paint(painter, option, index)

class ThumbnailDelegate(QtWidgets.QStyledItemDelegate):

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent=None, thumbnail_height: int = 64, top_margin: int = 4, rounded_rect_height_threshold: int = 20):
        # Initialize the super class
        super().__init__(parent)

        # Store the arguments
        self.thumbnail_height = thumbnail_height
        self.top_margin = top_margin
        self.rounded_rect_height_threshold = rounded_rect_height_threshold

        # Initialize setup
        self.__init_attributes()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        # Private Attributes
        # ------------------
        self._thumbnail_column = None
        self._source_column = None
        self._sequence_range_column = None
        self._sequence_range_column = None
        self._loading_threads = dict()
        self._loaded_thumbnails = dict()

    # Public Methods
    # --------------
    def set_source_column(self, column: int):
        self._source_column = column

    def set_thumbnail_column(self, column: int):
        self._thumbnail_column = column

    def set_sequence_range_column(self, column: int):
        self._sequence_range_column = column

    def load_thumbnail(self, file_path: str, is_background_process: bool = True) -> QtGui.QPixmap:
        if is_background_process:
            pixmap = self._load_thumbnail_using_worker(file_path)
        else:
            pixmap = ThumbnailUtils.get_pixmap_thumbnail(file_path, self.thumbnail_height)

        return pixmap

    # Utility Methods
    # ---------------
    @staticmethod
    def create_pixmap_round_rect_path(start_point: Union[QtCore.QPoint, QtCore.QPointF], pixmap: QtGui.QPixmap, corner_radius: int = 4):
        painter_path = QtGui.QPainterPath(start_point)
        painter_path.addRoundedRect(
            QtCore.QRectF(start_point, QtCore.QSizeF(pixmap.size())), 
            corner_radius, corner_radius
        )

        return painter_path

    # Private Methods
    # ---------------
    def _load_thumbnail_using_worker(self, file_path: str):
        if file_path in self._loading_threads:
            return

        elif file_path not in self._loaded_thumbnails:
            worker = ThumbnailLoader(file_path, self.thumbnail_height)
            # runnable = RunnableTask(worker)
            worker.thumbnail_loaded.connect(self.on_thumbnail_loaded)
            self._loading_threads[file_path] = worker

            # Use the shared thread pool to start the worker
            ThreadPoolManager.thread_pool().start(worker.run)
            # ThreadPoolManager.thread_pool().start(runnable)
            return

        return self._loaded_thumbnails[file_path]

    def _paint_pixmap(self, painter: QtGui.QPainter, rect: QtCore.QRect, pixmap: QtGui.QPixmap):
        scaled_pixmap = pixmap.scaled(
            int(rect.width() - 2 * self.top_margin), 
            int(rect.height() - 2 * self.top_margin), 
            QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation
        )

        # Calculate the center position
        x = rect.x() + (rect.width() - scaled_pixmap.width()) / 2
        y = rect.y() + (rect.height() - scaled_pixmap.height()) / 2
        start_point = QtCore.QPointF(x, y)

        # Save the painter's current state
        painter.save()

        # Draw rounded rect
        if scaled_pixmap.height() >= self.rounded_rect_height_threshold:
            # Create a rounded rectangle path
            path = self.create_pixmap_round_rect_path(start_point, scaled_pixmap)
            # Set the path as the clip path
            painter.setClipPath(path)

        # Draw the pixmap within the clipped region
        painter.drawPixmap(start_point, scaled_pixmap)

        # Restore the painter's state
        painter.restore()

    def on_thumbnail_loaded(self, file_path, pixmap):
        self._loaded_thumbnails[file_path] = pixmap
        del self._loading_threads[file_path]
        self.parent().viewport().update()  # Request a repaint

    def get_sibling_data(self, index: QtCore.QModelIndex, column: int, data_role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole):
        sibling_index = index.sibling(index.row(), column)
        return sibling_index.data(data_role)

    # Overridden Methods
    # ------------------
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        super().paint(painter, option, index)

        file_path = self.get_sibling_data(index, self._source_column)

        if not file_path:
            return

        if self._sequence_range_column is not None:
            sequence_range = self.get_sibling_data(index, self._sequence_range_column)
            if sequence_range:
                first_frame_number = int(sequence_range.split('-')[0])
                file_path = SequenceFileUtil.generate_frame_path(file_path, first_frame_number)

        pixmap = self.load_thumbnail(file_path)

        if pixmap is None or pixmap.isNull():
            # TODO: Paint loading pixmap
            return

        self._paint_pixmap(painter, option.rect, pixmap)
