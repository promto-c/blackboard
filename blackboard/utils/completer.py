# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore


# Class Definitions
# -----------------
class MatchContainsCompleter(QtWidgets.QCompleter):
    """A QCompleter subclass that matches items containing the typed text."""

    def __init__(self, parent: QtWidgets.QWidget = None):
        """Initialize the completer with custom matching settings.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        # Set the completion mode to match items containing the typed text
        self.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
