# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class GroupWidget(QtWidgets.QWidget):
    def __init__(self, *widgets: QtWidgets.QWidget):
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # No space between buttons
        self.setMaximumHeight(22)

        # Set custom properties for styling based on button position
        if widgets:
            widgets[0].setProperty("position", "first")
            widgets[-1].setProperty("position", "last")

        for button in widgets:
            layout.addWidget(button)

        # Apply the stylesheet to the container (QFrame) only
        self.setStyleSheet("""
            QWidget {
                border-radius: 0;
                border-left: none;
                border-right: none;
            }
            QWidget[position="first"] {
                border-top-left-radius: 4;
                border-bottom-left-radius: 4;
                border-left: 1px solid gray;
            }
            QWidget[position="last"] {
                border-top-right-radius: 4;
                border-bottom-right-radius: 4;
                border-right: 1px solid gray;
            }
        """)
