# Standard Library Imports
# ------------------------
import time

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui


# Class Definitions
# -----------------
class MomentumScrollHandler(QtCore.QObject):
    """Handle momentum scrolling for a given widget.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, widget: QtWidgets.QScrollArea, friction: float = 0.95,
                 min_velocity: float = 0.1, velocity_scale: float = 0.02,
                 frame_interval: int = 16):
        """Initialize the MomentumScrollHandler.

        Args:
            widget: The widget to apply momentum scrolling to.
            friction: The friction applied to reduce the scrolling speed.
            min_velocity: The minimum velocity threshold to stop scrolling.
            velocity_scale: The scale factor for the initial velocity.
            frame_interval: The timer interval in milliseconds for updating the scroll position.
        """
        super().__init__(widget)

        # Store the arguments
        self.widget = widget
        self.friction = friction
        self.min_velocity = min_velocity
        self.velocity_scale = velocity_scale
        self.frame_interval = frame_interval

        # Initialize setup
        self.__init_attributes()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.velocity = QtCore.QPointF()
        self.horizontal_scroll_bar = self.widget.horizontalScrollBar()
        self.vertical_scroll_bar = self.widget.verticalScrollBar()
        self.timer = QtCore.QTimer()

        # Initialize middle button pressed flag
        self._is_mouse_button_pressed = False
        self._prev_pos = QtCore.QPoint()
        self._start_pos = QtCore.QPoint()
        self._mouse_move_timestamp = float()

    def __init_signal_connections(self):
        """Initialize signal connections between widgets and slots.
        """
        self.timer.timeout.connect(self._update_scroll_position)

    # TODO: Implement eventFilter
    #     self.widget.installEventFilter(self)

    # TODO: Implement eventFilter
    # def eventFilter(self, obj, event):
    #     if obj == self.widget:
    #         if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.MouseButton.MiddleButton:
    #             self.handle_mouse_press(event)
    #             return True
    #         elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.MouseButton.MiddleButton:
    #             self.handle_mouse_release(event)
    #             return True
    #         elif event.type() == QtCore.QEvent.MouseMove and self._is_mouse_button_pressed:
    #             self.handle_mouse_move(event)
    #             return True
    #     return super().eventFilter(obj, event)

    # Public Methods
    # --------------
    def handle_mouse_press(self, event: QtGui.QMouseEvent):
        """Handle mouse button press event.
        """
        # Set button press flag to True
        self._is_mouse_button_pressed = True
        self.stop()
        # Record the initial position where mouse button is pressed
        self._start_pos = event.pos()

        # Change the cursor to SizeAllCursor
        self.widget.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)

    def handle_mouse_move(self, event: QtGui.QMouseEvent) -> bool:
        """Handle mouse button move event.

        Returns:
            True if the event is handled, False otherwise.
        """
        # Check if the mouse button is pressed
        if not self._is_mouse_button_pressed:
            return False

        # Calculate the change in mouse position
        delta = event.pos() - self._start_pos

        # Adjust the scroll bar values according to mouse movement
        self.horizontal_scroll_bar.setValue(self.horizontal_scroll_bar.value() - int(delta.x()))
        self.vertical_scroll_bar.setValue(self.vertical_scroll_bar.value() - int(delta.y()))

        # Update the previous and start positions of the mouse button
        self._prev_pos = self._start_pos
        self._start_pos = event.pos()
        # Set the timestamp of the last mouse move event
        self._mouse_move_timestamp = time.time()

        return True

    def handle_mouse_release(self, event: QtGui.QMouseEvent):
        """Handle mouse button release event.
        """
        # Set button press flag to False
        self._is_mouse_button_pressed = False

        # Calculate the velocity based on the change in mouse position and the elapsed time
        # NOTE: The + 0.01 is added to avoid division by zero
        velocity = (event.pos() - self._prev_pos) / ((time.time() - self._mouse_move_timestamp + 0.01))
        # Apply momentum movement based on velocity
        self.start(QtCore.QPointF(velocity.x(), velocity.y()))

        # Restore the cursor to default
        self.widget.unsetCursor()

    def start(self, initial_velocity: QtCore.QPointF):
        """Start the momentum scrolling with the given initial velocity.

        Args:
            initial_velocity: The initial velocity of the scrolling.
        """
        self.velocity = initial_velocity * self.velocity_scale
        self.timer.start(self.frame_interval)

    def stop(self):
        """Stop the momentum scrolling.
        """
        self.timer.stop()

    # Private Methods
    # ---------------
    def _update_scroll_position(self):
        """Handle the timer timeout event to update the scrolling.
        """
        if self.velocity.manhattanLength() < self.min_velocity:
            self.stop()
            return

        self.horizontal_scroll_bar.setValue(int(self.horizontal_scroll_bar.value() - self.velocity.x()))
        self.vertical_scroll_bar.setValue(int(self.vertical_scroll_bar.value() - self.velocity.y()))

        self.velocity *= self.friction
