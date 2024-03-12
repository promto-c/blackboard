# Type Checking Imports
# ---------------------
from typing import Callable, Optional

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
        # Call the parent class constructor
        super().__init__(parent)

        # Store the arguments
        self.widget = widget

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Set up the initial values for the widget.
        """
        # Set the minimum and maximum scale values
        self.min_zoom_level = self.DEFAULT_MIN_ZOOM_LEVEL
        self.max_zoom_level = self.DEFAULT_MAX_ZOOM_LEVEL

        # Set the current zoom level to 1.0 (no zoom)
        self.current_zoom_level = self.DEFAULT_ZOOM_LEVEL

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets and layouts.
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

        # Set the horizontal scroll bar policy to always off
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Set the vertical scroll bar policy to always off
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect the wheel event signal to the scaling slot
        self.viewport().installEventFilter(self)
        self.viewport().wheelEvent = self.wheelEvent

        # Key Binds
        # ---------
        # Create a QShortcut for the F key to reset the scaling of the view.
        KeyBinder.bind_key('F', self, self.reset_scale, QtCore.Qt.ShortcutContext.WindowShortcut)

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

        # Update the size of the widget to fit the view window
        self.resizeEvent(None)

    def reset_scale(self) -> None:
        """Reset scaling of the view to default zoom level (1.0 or no zoom).
        """
        # Reset the scaling of the view
        self.resetTransform()
        # Reset the current zoom level to 1.0 (no zoom)
        self.current_zoom_level = 1.0

        # Update the size of the widget to fit the view window
        self.resizeEvent(None)

    def bind_key(self, key_sequence: str, function: Callable):
        """Binds a given key sequence to a function.
        Args:
            key_sequence (str): The key sequence as a string, e.g., "Ctrl+C".
            function (Callable): The function to be called when the key sequence is activated.
        """
        # Create a shortcut with the specified key sequence
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key_sequence), self)
        # Connect the activated signal of the shortcut to the given function
        shortcut.activated.connect(function)

    def save_state(self, settings: QtCore.QSettings, group_name='scalable_view'):
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

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Handle resize events to resize the widget to the full size of the view, reserved for scaling.
        """
        # Get the size of the view
        view_size = self.size()

        # Create a QRectF object with the size of the view reserved for scaling
        rect = QtCore.QRectF(
            0, 0,
            view_size.width() / self.current_zoom_level-2,
            view_size.height() / self.current_zoom_level-2)

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

def main():
    import sys
    import blackboard as bb
    from blackboard import widgets

    # Create the Qt application
    app = QtWidgets.QApplication(sys.argv)

    # Set theme of QApplication to the dark theme
    bb.theme.set_theme(app, 'dark')

    from blackboard.examples.example_data_dict import COLUMN_NAME_LIST, ID_TO_DATA_DICT

    # Create the tree widget with example data
    tree_widget = widgets.GroupableTreeWidget(column_name_list=COLUMN_NAME_LIST, id_to_data_dict=ID_TO_DATA_DICT)

    # Create the scalable view and set the tree widget as its central widget
    scalable_tree_widget_view = ScalableView(widget=tree_widget)

    # Set the size of the view and show it
    scalable_tree_widget_view.resize(800, 600)
    scalable_tree_widget_view.show()

    # Run the application loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
