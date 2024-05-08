# Standard Library Imports
# ------------------------
import time

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.utils import FlatProxyModel

# Class Definitions
# -----------------
class InertiaScrollListView(QtWidgets.QListView):
    def __init__(self, parent=None, max_velocity=15, deceleration_rate=0.9, timer_interval=10):
        super().__init__(parent)
        self.setDragEnabled(False)  # Ensure that the default drag behavior is disabled
        self.setVerticalScrollMode(QtWidgets.QListView.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QListView.ScrollPerPixel)
        # self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.max_velocity = max_velocity
        self.deceleration_rate = deceleration_rate
        self.timer_interval = timer_interval

        self.velocity = 0
        self.last_time = 0
        self.dragging = False

        self.inertia_timer = QtCore.QTimer()
        self.inertia_timer.timeout.connect(self.handle_inertia)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse press events.
        """
        if event.button() in (QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.MiddleButton):
            self.dragging = True
            self.last_pos = event.pos()
            self.last_time = time.time()
            self.velocity = 0
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse move events.
        """
        if self.dragging:
            current_time = time.time()
            new_pos = event.pos()
            delta = new_pos - self.last_pos
            delta_time = current_time - self.last_time
            if delta_time > 0:
                # new_velocity = delta.x() / delta_time
                new_velocity = delta.y() / delta_time
                self.velocity = max(min(new_velocity, self.max_velocity), -self.max_velocity)
            # self.horizontalScrollBar().setValue(
            #     self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self.last_pos = new_pos
            self.last_time = current_time
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse release events.
        """
        if event.button() in (QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.MiddleButton):
            self.dragging = False
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self.inertia_timer.start(self.timer_interval)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def handle_inertia(self):
        self.velocity *= self.deceleration_rate
        if abs(self.velocity) < 0.5:
            self.inertia_timer.stop()
            return

        # h_scroll_bar = self.horizontalScrollBar()
        v_scroll_bar = self.verticalScrollBar()
        v_scroll_bar.setValue(v_scroll_bar.value() - int(self.velocity))

        if (v_scroll_bar.value() == v_scroll_bar.maximum() or
            v_scroll_bar.value() == v_scroll_bar.minimum()):
            self.inertia_timer.stop()

class TagListView(InertiaScrollListView):

    tag_changed = QtCore.Signal()

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        self._proxy_model = FlatProxyModel(show_only_checked=True, show_only_leaves=True)
        self._proxy_model.set_show_checkbox(False)

        self._press_position = None
        super().setModel(self._proxy_model)
        self._proxy_model.layoutChanged.connect(self.tag_changed.emit)

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        """
        self.setEditTriggers(QtWidgets.QListView.EditTrigger.NoEditTriggers)
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)

        # self.setViewMode(QtWidgets.QListView.ViewMode.ListMode)
        # self.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        # self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        # self.setFixedHeight(28)

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
        """Retrieve all tags and from the model."""
        return [self.model().index(row, 0).data() for row in range(self.model().rowCount())]

    def get_tags_count(self):
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

# NOTE: Not use
class InertiaScrollArea(QtWidgets.QScrollArea):
    def __init__(self, parent=None, max_velocity=15, deceleration_rate=0.9, timer_interval=10):
        super().__init__(parent)
        self.max_velocity = max_velocity
        self.deceleration_rate = deceleration_rate
        self.timer_interval = timer_interval

        self.velocity = 0
        self.last_time = 0
        self.dragging = False

        self.inertia_timer = QtCore.QTimer()
        self.inertia_timer.timeout.connect(self.handle_inertia)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse press events.
        """
        if event.button() in (QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.MiddleButton):
            self.dragging = True
            self.last_pos = event.pos()
            self.last_time = time.time()
            self.velocity = 0
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse move events.
        """
        if self.dragging:
            current_time = time.time()
            new_pos = event.pos()
            delta = new_pos - self.last_pos
            delta_time = current_time - self.last_time
            if delta_time > 0:
                new_velocity = delta.x() / delta_time
                self.velocity = max(min(new_velocity, self.max_velocity), -self.max_velocity)
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.last_pos = new_pos
            self.last_time = current_time
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse release events.
        """
        if event.button() in (QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.MiddleButton):
            self.dragging = False
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self.inertia_timer.start(self.timer_interval)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def handle_inertia(self):
        self.velocity *= self.deceleration_rate
        if abs(self.velocity) < 0.5:
            self.inertia_timer.stop()
            return

        h_scroll_bar = self.horizontalScrollBar()
        h_scroll_bar.setValue(h_scroll_bar.value() - int(self.velocity))

        if (h_scroll_bar.value() == h_scroll_bar.maximum() or
            h_scroll_bar.value() == h_scroll_bar.minimum()):
            self.inertia_timer.stop()


# Example usage
if __name__ == "__main__":
    import sys
    ...
