# Type Checking Imports
# ---------------------
from typing import Callable, Optional

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class OverlayToolBar(QtWidgets.QToolBar):

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None, icon_size: QtCore.QSize = QtCore.QSize(24, 24), orientation: QtCore.Qt.Orientation = QtCore.Qt.Orientation.Horizontal):
        super().__init__(parent)
        self.setOrientation(orientation)
        self.setIconSize(icon_size)
        self.setMovable(False)
        self.setFloatable(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setProperty('widget-style', 'overlay')

        # Hide the toolbar initially
        self.setVisible(False)

    # Public Methods
    # --------------
    def add_action(self, icon: QtGui.QIcon, tooltip: str, callback: Optional[Callable] = None) -> QtGui.QAction:
        """Adds an action to the toolbar."""
        action = self.addAction(icon, '')
        action.setToolTip(tooltip)
        if callback:
            action.triggered.connect(callback)
        
        # Access the widget for the action and set the cursor
        self.widgetForAction(action).setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        
        return action

    def show_overlay(self):
        self.setVisible(True)

    def hide_overlay(self):
        self.setVisible(False)
