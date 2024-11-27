# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui

# Local Imports
# -------------
from blackboard.utils import MomentumScrollHandler


# Class Definitions
# -----------------
class MomentumScrollListView(QtWidgets.QListView):
    """A QListView with momentum scrolling functionality."""

    def __init__(self, parent: QtWidgets.QWidget = None, dragEnabled: bool = False, *args, **kwargs):
        super().__init__(
            parent,
            dragEnabled=dragEnabled,
            horizontalScrollMode=QtWidgets.QListWidget.ScrollMode.ScrollPerPixel,
            verticalScrollMode=QtWidgets.QListWidget.ScrollMode.ScrollPerPixel,
            *args, **kwargs
        )

        self.scroll_handler = MomentumScrollHandler(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press event."""
        # Check if middle mouse button is pressed
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_press(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse move event."""
        is_success = self.scroll_handler.handle_mouse_move(event)

        if is_success:
            event.ignore()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse release event."""
        # Check if middle mouse button is released
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_release(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handle wheel events for touchpad scrolling."""
        self.scroll_handler.handle_wheel_event(event)

class MomentumScrollListWidget(QtWidgets.QListWidget):
    """A QListWidget with momentum scrolling functionality."""

    def __init__(self, parent: QtWidgets.QWidget = None, dragEnabled: bool = False, *args, **kwargs):
        """Initialize the MomentumScrollListWidget.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(
            parent,
            dragEnabled=dragEnabled,
            horizontalScrollMode=QtWidgets.QListWidget.ScrollMode.ScrollPerPixel,
            verticalScrollMode=QtWidgets.QListWidget.ScrollMode.ScrollPerPixel,
            *args, **kwargs
        )

        # Initialize the MomentumScrollHandler
        self.scroll_handler = MomentumScrollHandler(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press event."""
        # Check if middle mouse button is pressed
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_press(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse move event."""
        is_success = self.scroll_handler.handle_mouse_move(event)

        if is_success:
            event.ignore()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse release event."""
        # Check if middle mouse button is released
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_release(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handle wheel events for touchpad scrolling."""
        self.scroll_handler.handle_wheel_event(event)

class MomentumScrollTreeView(QtWidgets.QTreeView):
    """A QTreeView with momentum scrolling functionality.
    """

    def __init__(self, parent: QtWidgets.QWidget = None, *args, **kwargs):
        """Initialize the MomentumScrollListView.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(
            parent, 
            horizontalScrollMode=QtWidgets.QTreeWidget.ScrollPerPixel,
            verticalScrollMode=QtWidgets.QTreeWidget.ScrollPerPixel,
            *args, **kwargs
        )

        # Initialize the MomentumScrollHandler
        self.scroll_handler = MomentumScrollHandler(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press event."""
        # Check if middle mouse button is pressed
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_press(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse move event."""
        is_success = self.scroll_handler.handle_mouse_move(event)

        if is_success:
            event.ignore()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse release event."""
        # Check if middle mouse button is released
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_release(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handle wheel events for touchpad scrolling."""
        self.scroll_handler.handle_wheel_event(event)

class MomentumScrollTreeWidget(QtWidgets.QTreeWidget):
    """A QTreeWidget with momentum scrolling functionality."""

    def __init__(self, parent: QtWidgets.QWidget = None, *args, **kwargs):
        """Initialize the MomentumScrollTreeWidget.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(
            parent, 
            horizontalScrollMode=QtWidgets.QTreeWidget.ScrollPerPixel,
            verticalScrollMode=QtWidgets.QTreeWidget.ScrollPerPixel,
            *args, **kwargs
        )

        # Initialize the MomentumScrollHandler
        self.scroll_handler = MomentumScrollHandler(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press event."""
        # Check if middle mouse button is pressed
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_press(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse move event."""
        is_success = self.scroll_handler.handle_mouse_move(event)

        if is_success:
            event.ignore()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse release event."""
        # Check if middle mouse button is released
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_release(event)
        # If not middle button, call the parent class method to handle the event
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handle wheel events for touchpad scrolling."""
        self.scroll_handler.handle_wheel_event(event)

class MomentumScrollArea(QtWidgets.QScrollArea):
    """A QScrollArea with momentum scrolling functionality."""

    def __init__(self, parent: QtWidgets.QWidget = None, *args, **kwargs):
        """Initialize the MomentumScrollArea.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(
            parent, 
            horizontalScrollBarPolicy=QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded,
            verticalScrollBarPolicy=QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded,
            *args, **kwargs
        )

        # Initialize the MomentumScrollHandler
        self.scroll_handler = MomentumScrollHandler(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse press event."""
        # Check if middle mouse button is pressed
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse move event."""
        is_success = self.scroll_handler.handle_mouse_move(event)

        if is_success:
            event.ignore()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle mouse release event."""
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.scroll_handler.handle_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Handle wheel events for touchpad scrolling."""
        self.scroll_handler.handle_wheel_event(event)
