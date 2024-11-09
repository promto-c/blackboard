from typing import List

from qtpy import QtWidgets, QtCore, QtGui

class HeaderColumnWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__( *args, **kwargs)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 4)

        line_edit = QtWidgets.QLineEdit(self)

        layout.addWidget(line_edit)

        line_edit.setPlaceholderText(f"Header")

# NOTE: WIP
class SearchableHeaderView(QtWidgets.QHeaderView):

    MARGIN = 4

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QTreeWidget, orientation: QtCore.Qt.Orientation = QtCore.Qt.Orientation.Horizontal):
        super().__init__(orientation, parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_icons()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        # Attributes
        # ------------------
        self.line_edits: List[QtWidgets.QLineEdit] = []

        # Private Attributes
        # ------------------
        ...

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create widgets and layouts
        self.setFixedHeight(int(self.height()*1.5))
        self.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.set_line_edits()

        if self.parent():
            self.parent().setHeader(self)
            self.update_positions()

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.sectionResized.connect(self.update_positions)
        self.sectionCountChanged.connect(self.on_columns_changed)
        self.parent().horizontalScrollBar().valueChanged.connect(self.update_positions)

    def __init_icons(self):
        """Set the icons for the widgets.
        """
        # Set the icons for the widgets
        pass

    # Private Methods
    # ---------------
    def on_columns_changed(self, start=None, end=None):
        """Handle column changes in the model."""
        if end <= len(self.line_edits):
            return
        
        num = end - len(self.line_edits)
        for _ in range(num):
            widget = HeaderColumnWidget(self)
            widget.show()
            self.line_edits.append(widget)
        self.update_positions()

    # Extended Methods
    # ----------------
    def update_positions(self):

        if not self.line_edits:
            return

        header_height = self.height()
        line_edit_height = self.line_edits[0].sizeHint().height()

        # Calculate the y-position to align the line_edit at the bottom
        y_pos = header_height - line_edit_height - (self.MARGIN * 2)

        for i, line_edit in enumerate(self.line_edits):
            x_pos = self.sectionViewportPosition(i) + self.MARGIN

            rect = QtCore.QRect(x_pos, y_pos, self.sectionSize(i) - (self.MARGIN * 2), header_height)
            line_edit.setGeometry(rect)

    def set_line_edits(self):
        for _ in range(self.parent().model().columnCount()):
            widget = HeaderColumnWidget(self)
            self.line_edits.append(widget)

    # Event Handling or Override Methods
    # ----------------------------------
    def mousePressEvent(self, event):
        for line_edit in self.line_edits:
            if line_edit.geometry().contains(event.pos()):
                line_edit.setFocus()
                return

        super().mousePressEvent(event)
