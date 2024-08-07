from typing import List

from qtpy import QtWidgets, QtCore, QtGui

class HeaderColumnWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__( *args, **kwargs)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 4)
        # layout.setSpacing(0)

        # label = QtWidgets.QLabel('test', self)
        # layout.addSpacing(20)
        line_edit = QtWidgets.QLineEdit(self)

        # layout.addWidget(label)
        layout.addWidget(line_edit)
        
        line_edit.setPlaceholderText(f"Header")

class SearchableHeaderView(QtWidgets.QHeaderView):

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
        self.parent().horizontalScrollBar().valueChanged.connect(self.update_positions)

    def __init_icons(self):
        """Set the icons for the widgets.
        """
        # Set the icons for the widgets
        pass

    # Private Methods
    # ---------------

    # Extended Methods
    # ----------------
    def update_positions(self):
        for i, line_edit in enumerate(self.line_edits):
            section_rect = self.sectionViewportPosition(i)
            rect = QtCore.QRect(section_rect+4, 11, self.sectionSize(i)-8, self.height())
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
