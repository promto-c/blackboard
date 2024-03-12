from typing import List

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class FocusEventFilter(QtCore.QObject):

    focus_widgets: List[QtWidgets.QWidget] = list()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Custom event filter to track focus changes."""
        if event.type() == QtCore.QEvent.Type.FocusIn:
            FocusEventFilter.focus_widgets.append(obj)

        elif event.type() == QtCore.QEvent.Type.FocusOut and obj in FocusEventFilter.focus_widgets:
            FocusEventFilter.focus_widgets.remove(obj)

        return super().eventFilter(obj, event)
