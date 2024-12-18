# Type Checking Imports
# ---------------------
from typing import Any, Union, Optional

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui


# Class Definitions
# -----------------
class SectionAction(QtWidgets.QWidgetAction):

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent_menu: QtWidgets.QMenu, text: str = None, icon: QtGui.QIcon = None):
        super().__init__(parent_menu)

        self.parent_menu = parent_menu

        # Create a container widget
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        # Optional Icon
        if icon:
            self.icon_label = QtWidgets.QLabel()
            pixmap = icon.pixmap(16, 16)  # Adjust size as needed
            self.icon_label.setPixmap(pixmap)
            layout.addWidget(self.icon_label)
        else:
            self.icon_label = None

        # Text Label
        self.text_label = QtWidgets.QLabel(text)
        layout.addWidget(self.text_label)

        # Set the layout to the container
        container.setLayout(layout)

        # Set the container as the default widget for the action
        self.setDefaultWidget(container)

        # Add the action to the parent menu
        self.parent_menu.addAction(self)

        # Add a separator after the section
        self.separator = self.parent_menu.addSeparator()

    def addAction(self, action: QtGui.QAction = None, icon: QtGui.QIcon = QtGui.QIcon(), text: str = '', toolTip: str = None, 
                  data: Any = None, *args, **kwargs) -> QtGui.QAction:
        if not isinstance(action, QtGui.QAction):
            toolTip = toolTip or text
            action = QtGui.QAction(icon=icon, text=text, toolTip=toolTip, parent=self, *args, **kwargs)
            if data is not None:
                action.setData(data)

        self.parent_menu.insertAction(self.separator, action)

        return action

    def addMenu(self, title: str, *args, **kwargs) -> QtWidgets.QMenu:
        menu = ContextMenu(title, self.parent_menu, *args, **kwargs)
        self.parent_menu.insertMenu(self.separator, menu)

        return menu

    def addSeparator(self) -> QtWidgets.QAction:
        return self.parent_menu.insertSeparator(self.separator)

class ContextMenu(QtWidgets.QMenu):

    # Initialization and Setup
    # ------------------------
    def __init__(self, title: str = '', parent: QtWidgets.QWidget = None, *args, **kwargs):
        super().__init__(title, parent, *args, **kwargs)

        # Set UI attributes
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    def addSection(self, text: str, icon: QtGui.QIcon = None) -> 'SectionAction':
        return SectionAction(self, text, icon)

    def insert_after_action(self, target_action: QtWidgets.QAction, action_to_insert: QtWidgets.QAction):
        """Insert an action after a specific target action in the menu.
        """
        actions = self.actions()
        for index, action in enumerate(actions):
            if action != target_action:
                continue

            if index + 1 < len(actions):
                self.insertAction(actions[index + 1], action_to_insert)
            else:
                self.addAction(action_to_insert)
            break

class ResizableMenu(ContextMenu):
    """A resizable popup menu with drag-and-resize functionality.

    Attributes:
        button (Optional[QtWidgets.QPushButton]): Optional button to position the menu relative to.
        resized (QtCore.Signal): Signal emitted when the menu is resized.
    """

    # Constants
    # ---------
    RESIZE_HANDLE_SIZE = 20

    # Signals
    # -------
    resized = QtCore.Signal(QtCore.QSize)

    # Initialization and Setup
    # ------------------------
    def __init__(self, button: Optional[QtWidgets.QPushButton] = None):
        """Initialize the popup menu and set up drag-resize functionality.

        Args:
            button (Optional[QtWidgets.QPushButton]): Optional button to position the menu relative to.
        """
        super().__init__()

        # Store the arguments
        self.button = button

        # Initialize setup
        self.__init_attributes()

    def __init_attributes(self):
        """Initialize drag functionality for resizing the menu.
        """
        self._is_dragging = False
        self._drag_start_point = QtCore.QPoint()
        self._initial_size = self.size()

    # Overridden Methods
    # ------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Handle key press events to prevent closing the popup on Enter or Return keys.
        """
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            # Do nothing, preventing the popup from closing
            pass
        else:
            super().keyPressEvent(event)

    def showEvent(self, event: QtGui.QShowEvent):
        """Override show event to modify the position of the menu popup.
        """
        if self.button:
            # Adjust the position
            pos = self.button.mapToGlobal(QtCore.QPoint(0, self.button.height()))
            self.move(pos)
        super().showEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        """Handle the resize event and emit a signal with the new size.
        """
        self.resized.emit(self.size())
        super().resizeEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handle the mouse press event for resizing the menu.
        """
        # Calculate the rectangle representing the resize handle area
        handle_rect = QtCore.QRect(
            self.width() - self.RESIZE_HANDLE_SIZE,
            self.height() - self.RESIZE_HANDLE_SIZE,
            self.RESIZE_HANDLE_SIZE,
            self.RESIZE_HANDLE_SIZE
        )

        if handle_rect.contains(event.pos()):
            # Only start dragging if the mouse is within the handle area
            self._is_dragging = True
            self._drag_start_point = event.pos()
            self._initial_size = self.size()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.SizeFDiagCursor))
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handle the mouse move event to resize the menu.
        """
        # If dragging, resize the widget
        if self._is_dragging:
            delta = event.pos() - self._drag_start_point
            new_size = QtCore.QSize(
                max(self._initial_size.width() + delta.x(), self.minimumWidth()),
                max(self._initial_size.height() + delta.y(), self.minimumHeight())
            )
            self.resize(new_size)
        else:
            # TODO: Test
            # Only change the cursor if the mouse is in the resize handle area
            handle_rect = QtCore.QRect(
                self.width() - self.RESIZE_HANDLE_SIZE,
                self.height() - self.RESIZE_HANDLE_SIZE,
                self.RESIZE_HANDLE_SIZE,
                self.RESIZE_HANDLE_SIZE
            )
            if handle_rect.contains(event.pos()):
                # Change to a diagonal resize cursor
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.SizeFDiagCursor))
            else:
                # Reset to default cursor
                self.unsetCursor()

            # Call base implementation for default behavior
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handle the mouse release event to stop resizing the menu.
        """
        self._is_dragging = False
        self.unsetCursor()
