
# Type Checking Imports
# ---------------------
...

# Standard Library Imports
# ------------------------
...

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore

# Local Imports
# -------------
...


class MatchContainsCompleter(QtWidgets.QCompleter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set the completion mode to match items containing the typed text
        self.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
