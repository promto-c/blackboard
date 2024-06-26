# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui

# Local Imports
# -------------
from blackboard.utils import FlatProxyModel
from blackboard.widgets import MomentumScrollListView


# Class Definitions
# -----------------
class TagListView(MomentumScrollListView):

    tag_changed = QtCore.Signal()

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._proxy_model = FlatProxyModel(show_only_checked=True, show_only_leaves=True)
        self._proxy_model.set_show_checkbox(False)

        self._press_position = None
        super().setModel(self._proxy_model)
        self._proxy_model.layoutChanged.connect(self.tag_changed.emit)

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setEditTriggers(QtWidgets.QListView.EditTrigger.NoEditTriggers)
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)

        self.setDragDropMode(QtWidgets.QListView.DragDropMode.NoDragDrop)
        self.setMouseTracking(True)

        self.setStyleSheet('''
            QListView::item {
                background-color: #355;
                border-radius: 4px;
                border: transparent;
                padding: 2px 5px;
                color: #DDD;
                margin: 2px;
            }
            QListView::item:hover {
                background-color: #466;
            }
            QListView::item:pressed {
                background-color: #244;
            }
        ''')

    # Public Methods
    # --------------
    def get_tags(self):
        """Retrieve all tags from the model.
        """
        return [self.model().index(row, 0).data() for row in range(self.model().rowCount())]

    def get_tags_count(self):
        """Get the count of tags.
        """
        return self.model().rowCount()

    # Class Properties
    # ----------------
    @property
    def source_model(self):
        return self._proxy_model.sourceModel()

    @property
    def proxy_model(self):
        return self._proxy_model

    # Override Methods
    # ----------------
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        index = self.indexAt(event.pos())
        if index.isValid():
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._press_position = event.pos()  # Store mouse press position
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        super().mouseReleaseEvent(event)
        if self._press_position != event.pos():
            self._press_position = None
            return

        index = self.indexAt(event.pos())
        if not index.isValid():
            self._press_position = None
            return

        tag_name = index.data()

        # Set the new state
        self.model().setData(index, QtCore.Qt.CheckState.Unchecked, QtCore.Qt.ItemDataRole.CheckStateRole)
        QtWidgets.QToolTip.showText(event.globalPos(), f"'{tag_name}' Removed.", self)

        self._press_position = None

    def setModel(self, model):
        self._proxy_model.setSourceModel(model)


# Example usage
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    tag_list_view = TagListView()
    main_window.setCentralWidget(tag_list_view)
    main_window.show()
    sys.exit(app.exec_())
