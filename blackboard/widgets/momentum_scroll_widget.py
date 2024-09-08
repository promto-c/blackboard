# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui

# Local Imports
# -------------
from blackboard.utils import MomentumScrollHandler


# Class Definitions
# -----------------
class MomentumScrollListView(QtWidgets.QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(False)  # Ensure that the default drag behavior is disabled
        self.setVerticalScrollMode(QtWidgets.QListView.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QListView.ScrollPerPixel)

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

class MomentumScrollTreeView(QtWidgets.QTreeView):
    """A QTreeView with momentum scrolling functionality.
    """

    def __init__(self, parent=None):
        """Initialize the MomentumScrollListView.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(parent)

        self.setVerticalScrollMode(QtWidgets.QTreeView.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QTreeView.ScrollPerPixel)

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

class MomentumScrollListWidget(QtWidgets.QListWidget):
    """A QListWidget with momentum scrolling functionality."""

    def __init__(self, parent=None):
        """Initialize the MomentumScrollListWidget.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(parent)
        self.setDragEnabled(False)  # Ensure that the default drag behavior is disabled
        self.setVerticalScrollMode(QtWidgets.QListWidget.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QListWidget.ScrollPerPixel)

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

class MomentumScrollTreeWidget(QtWidgets.QTreeWidget):
    """A QTreeWidget with momentum scrolling functionality."""

    def __init__(self, parent=None):
        """Initialize the MomentumScrollTreeWidget.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(parent)

        self.setVerticalScrollMode(QtWidgets.QTreeWidget.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QTreeWidget.ScrollPerPixel)

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
