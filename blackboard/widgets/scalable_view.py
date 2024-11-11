# Type Checking Imports
# ---------------------
from typing import Optional

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui

# Local Imports
# -------------
from blackboard.utils import KeyBinder


# Class Definitions
# -----------------
class ScalableView(QtWidgets.QGraphicsView):
    """A QGraphicsView subclass that allows the user to scale the contents of the view 
    using the mouse wheel and keyboard.

    Attributes:
        widget (QtWidgets.QWidget): The widget to be displayed in the view.
        min_zoom_level (float): The minimum zoom level allowed for the view.
        max_zoom_level (float): The maximum zoom level allowed for the view.
        current_zoom_level (float): The current zoom level of the view.
    """
    DEFAULT_MIN_ZOOM_LEVEL = 0.5
    DEFAULT_MAX_ZOOM_LEVEL = 4.0
    DEFAULT_ZOOM_LEVEL = 1.0

    # Initialization and Setup
    # ------------------------
    def __init__(self, widget: QtWidgets.QWidget, parent: Optional[QtWidgets.QWidget] = None):
        """Initialize the ScalableView widget.
        """
        # Initialize the super class
        super().__init__(parent)

        # Store the arguments
        self.widget = widget

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize attributes of the widget.
        """
        # Set the minimum and maximum scale values
        self.min_zoom_level = self.DEFAULT_MIN_ZOOM_LEVEL
        self.max_zoom_level = self.DEFAULT_MAX_ZOOM_LEVEL

        # Set the current zoom level to 1.0 (no zoom)
        self.current_zoom_level = self.DEFAULT_ZOOM_LEVEL

        # Get the reference to the QApplication instance
        if hasattr(QtWidgets.qApp, 'scalable_widgets'):
            QtWidgets.qApp.scalable_widgets.append(self.widget)
        else:
            QtWidgets.qApp.scalable_widgets = [self.widget]

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Set the scene
        self.setScene(QtWidgets.QGraphicsScene(self))
        # Set the widget as the central widget of the scene
        self.graphic_proxy_widget = self.scene().addWidget(self.widget)

        # Set the alignment of the widget to the top left corner
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        # Set the viewport update mode to full viewport update to ensure that the entire view is updated when scaling
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        # Set the rendering hints to smooth pixels to improve the quality of the rendering
        self.setRenderHints(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        # Set the scroll bars to be always off
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Set the initial minimum size to fit the widget's contents
        self.setMinimumSize(self.widget.sizeHint())

    def __init_signal_connections(self):
        """Initialize signal connections.
        """
        # Connect the wheel event signal to the scaling slot
        self.viewport().installEventFilter(self)
        self.viewport().wheelEvent = self.wheelEvent

        # Key Binds
        # ---------
        # Create a QShortcut for the F key to reset the scaling of the view.
        KeyBinder.bind_key('F', self, self.reset_scale, QtCore.Qt.ShortcutContext.WindowShortcut)

    # Utility Methods
    # ---------------
    @staticmethod
    def is_scalable(widget: QtWidgets.QWidget) -> bool:
        """Check if the given widget is a descendant of a ScalableView.

        Args:
            widget (QtWidgets.QWidget): The widget to check.

        Returns:
            bool: True if the widget is a descendant of a ScalableView, False otherwise.
        """
        if not hasattr(QtWidgets.qApp, 'scalable_widgets'):
            return False

        return any(scalable_widget.isAncestorOf(widget) for scalable_widget in QtWidgets.qApp.scalable_widgets)

    # Extended Methods
    # ----------------
    def set_scale(self, zoom_level: float = 1.0) -> None:
        """Set scale of the view to specified zoom level.
        """
        # Clamp the zoom level between the min and max zoom levels
        zoom_level = max(self.min_zoom_level, min(zoom_level, self.max_zoom_level))

        # Set the new zoom level
        self.setTransform(QtGui.QTransform().scale(zoom_level, zoom_level))
        # Update current zoom level
        self.current_zoom_level = zoom_level
        # Update the minimum size to fit the current zoom level
        self.setMinimumSize(self.widget.sizeHint() * self.current_zoom_level)

        # Update the size of the widget to fit the view window
        self.resizeEvent()

    def reset_scale(self) -> None:
        """Reset scaling of the view to default zoom level (1.0 or no zoom).
        """
        # Reset the scaling of the view
        self.resetTransform()
        # Reset the current zoom level to 1.0 (no zoom)
        self.current_zoom_level = 1.0
        # Update the minimum size to fit the current zoom level
        self.setMinimumSize(self.widget.sizeHint() * self.current_zoom_level)

        # Update the size of the widget to fit the view window
        self.resizeEvent()

    def save_state(self, settings: QtCore.QSettings, group_name: str = 'scalable_view'):
        settings.beginGroup(group_name)
        settings.setValue('zoom_level', self.current_zoom_level)
        settings.endGroup()

    def load_state(self, settings: QtCore.QSettings, group_name='scalable_view'):
        settings.beginGroup(group_name)
        zoom_level = float(settings.value('zoom_level', self.DEFAULT_ZOOM_LEVEL))
        settings.endGroup()

        self.set_scale(zoom_level)

    # Event Handling or Override Methods
    # ----------------------------------
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ContextMenu and obj is not None:
            # TODO: Modify the context menu to allow it to popup and overlap the ScalableView instead of being constrained within it.
            ...

            # Show the menu
            self.contextMenuEvent(event)

            # Return True indicating the event has been handled
            return True

        # Default case: Pass the event on to the parent class
        return super().eventFilter(obj, event)

    def resizeEvent(self, event: Optional[QtGui.QResizeEvent] = None) -> None:
        """Handle resize events to resize the widget to the full size of the view, reserved for scaling.
        """
        # Get the size of the view
        view_size = self.size()

        # Create a QRectF object with the size of the view reserved for scaling
        rect = QtCore.QRectF(
            0, 0,
            view_size.width() / self.current_zoom_level - 2,
            view_size.height() / self.current_zoom_level - 2
        )

        # Set the size of the widget to the size of the view
        self.graphic_proxy_widget.setGeometry(rect)
        self.scene().setSceneRect(rect)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Handle wheel events to allow the user to scale the contents of the view.
        """
        # Check if the Ctrl key is pressed
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            # Get the scroll delta
            scroll_delta = event.angleDelta().y()
            # Calculate the scaling factor based on the wheel delta
            scale_factor = 1 + (scroll_delta / 120) / 10
            # Get the current scaling of the view
            self.current_zoom_level = self.transform().m11()

            # Calculate the new zoom level
            new_zoom_level = self.current_zoom_level * scale_factor
            # Set scale of the view to new zoom level.
            self.set_scale(new_zoom_level)

        # If the Ctrl key is not pressed, pass the event on to the parent class
        else:
            super().wheelEvent(event)

    # NOTE: To handle when has multiple Scalable Views in same window
    # def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
    #     event.accept()

    # def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
    #     event.accept()

    # def dropEvent(self, event: QtGui.QDropEvent) -> None:
    #     # Map the event position to the scalable view's coordinate system
    #     scene_pos = self.mapToScene(event.pos()).toPoint()

    #     # forward the event to the contained widget
    #     try:
    #         target_widget = self.widget.childAt(scene_pos).parent()
    #         target_widget.dropEvent(event)
    #     except (AttributeError, RuntimeError):
    #         pass


# Example usages
if __name__ == '__main__':
    import sys
    import blackboard as bb
    from blackboard import widgets
    from blackboard.examples.example_data_dict import COLUMN_NAME_LIST, ID_TO_DATA_DICT

    # Create the Qt application
    app = QtWidgets.QApplication(sys.argv)

    # Set the theme of QApplication to the dark theme
    bb.theme.set_theme(app, 'dark')

    # Create the GroupableTreeWidget with example data
    tree_widget = widgets.GroupableTreeWidget()
    tree_widget.setHeaderLabels(COLUMN_NAME_LIST)
    tree_widget.add_items(ID_TO_DATA_DICT)

    # Check if the tree widget is within a ScalableView before wrapping it
    print(ScalableView.is_scalable(tree_widget))
    # Expected output: False

    # Wrap the tree widget in a ScalableView
    scalable_tree_widget_view = ScalableView(widget=tree_widget)

    # Check again if the tree widget is now within a ScalableView
    print(ScalableView.is_scalable(tree_widget))
    # Expected output: True

    # Set the size of the scalable view and show it
    scalable_tree_widget_view.resize(800, 600)
    scalable_tree_widget_view.show()

    # Run the application loop
    sys.exit(app.exec())
