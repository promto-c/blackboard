# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class FocusEventFilter(QtCore.QObject):

    focus_widget: QtWidgets.QWidget = None

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Custom event filter to track focus changes."""

        if event.type() == QtCore.QEvent.Type.FocusIn and not isinstance(obj, QtWidgets.QCommonStyle):
            FocusEventFilter.focus_widget = obj

        elif event.type() == QtCore.QEvent.Type.FocusOut and FocusEventFilter.focus_widget == obj:
            FocusEventFilter.focus_widget = None

        return super().eventFilter(obj, event)
