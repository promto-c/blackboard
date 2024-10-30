# Standard Library Imports
# ------------------------
import enum

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.utils.thread_pool import ThreadPoolManager
from blackboard.utils.qimage_utils import ThumbnailLoader, ThumbnailUtils
from blackboard.widgets.tool_bar import OverlayToolBar


# Class Definitions
# -----------------
class ResizeMode(enum.Enum):
    Fit = QtCore.Qt.AspectRatioMode.KeepAspectRatio
    Fill = QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding
    Stretch = QtCore.Qt.AspectRatioMode.IgnoreAspectRatio

class ThumbnailWidget(QtWidgets.QWidget):

    ResizeMode = ResizeMode

    thumbnail_loaded = QtCore.Signal(str, QtGui.QPixmap)

    # Initialization and Setup
    # ------------------------
    def __init__(self, file_path: str, desired_height: int = 512, 
                 resize_mode: ResizeMode = ResizeMode.Fit, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        # Store the arguments
        self.file_path = file_path
        self.desired_height = desired_height
        self._resize_mode = resize_mode

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._pixmap = None
        self._loading_thread = None

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create a toolbar instead of a button
        self.tool_bar = OverlayToolBar(self)
        self.tool_bar.add_action(TablerQIcon.arrows_diagonal, "View full image", self.show_image)

        # Overlay button on the image
        self.overlay_layout = QtWidgets.QHBoxLayout(self)
        self.overlay_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight)
        self.overlay_layout.setContentsMargins(4, 4, 4, 4)
        self.overlay_layout.addWidget(self.tool_bar)

        # Start loading thumbnail
        # QtCore.QTimer.singleShot(0, self._load_thumbnail)
        self._load_thumbnail()

    # Public Methods
    # --------------
    def show_image(self):
        """Display the full image in a dialog."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Image Viewer")
        dialog_layout = QtWidgets.QVBoxLayout(dialog)
        # pixmap = QtGui.QPixmap(self.file_path)
        pixmap = ThumbnailUtils.get_pixmap_thumbnail(self.file_path, 1000)
        image_label = QtWidgets.QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(image_label)
        dialog.resize(800, 600)
        dialog.exec_()

    def get_scaled_pixmap(self, pixmap: QtGui.QPixmap, target_size: QtCore.QSize) -> QtGui.QPixmap:
        """Scale the pixmap based on the current size mode."""
        return pixmap.scaled(
            target_size,
            self._resize_mode.value,
            QtCore.Qt.TransformationMode.FastTransformation
        )

    def set_resize_mode(self, resize_mode: ResizeMode):
        if not isinstance(resize_mode, ResizeMode):
            raise ValueError("Invalid resize mode")
        self._resize_mode = resize_mode
        self.update()

    def set_pixmap(self, pixmap: QtGui.QPixmap):
        if not isinstance(pixmap, QtGui.QPixmap):
            raise ValueError("pixmap must be an instance of QPixmap.")
        self._pixmap = pixmap
        self.update()

    # Class Properties
    # ----------------
    @property
    def pixmap(self) -> QtGui.QPixmap:
        return self._pixmap

    @pixmap.setter
    def pixmap(self, pixmap: QtGui.QPixmap):
        self.set_pixmap(pixmap)

    @property
    def resize_mode(self) -> ResizeMode:
        return self._resize_mode

    @resize_mode.setter
    def resize_mode(self, resize_mode: ResizeMode):
        self.set_resize_mode(resize_mode)

    # Private Methods
    # ---------------
    def _load_thumbnail(self, use_background_thread: bool = True):
        if self._loading_thread is not None:
            return

        # Create a worker for loading the thumbnail
        self._loading_thread = ThumbnailLoader(self.file_path, self.desired_height)
        self._loading_thread.thumbnail_loaded.connect(self._on_thumbnail_loaded)

        if use_background_thread:
            ThreadPoolManager.thread_pool().start(self._loading_thread.run)
        else:
            # Run the thumbnail loading if not using a background thread
            self._loading_thread.run()

    def _on_thumbnail_loaded(self, _file_path: str, pixmap: QtGui.QPixmap):
        self._pixmap = pixmap
        self._loading_thread.deleteLater()
        self._loading_thread = None
        self.update()

    def _paint_thumbnail(self, painter: QtGui.QPainter):
        rect = self.rect()
        scaled_pixmap = self.get_scaled_pixmap(self._pixmap, rect.size())

        # Center the pixmap within the widget
        x = (rect.width() - scaled_pixmap.width()) // 2
        y = (rect.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)

    def _paint_placeholder(self, painter: QtGui.QPainter):
        rect = self.rect()
        painter.setPen(QtGui.QColor(200, 200, 200))
        painter.setBrush(QtGui.QColor(240, 240, 240))
        painter.drawRect(rect)

        painter.setPen(QtGui.QColor(150, 150, 150))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, "Loading...")

    # Overridden Methods
    # ------------------
    def enterEvent(self, event):
        """Show the button when mouse enters the widget."""
        self.tool_bar.show_overlay()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide the button when mouse leaves the widget."""
        self.tool_bar.hide_overlay()
        super().leaveEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        if self._loading_thread is None and self._pixmap and not self._pixmap.isNull():
            self._paint_thumbnail(painter)
        else:
            self._paint_placeholder(painter)
