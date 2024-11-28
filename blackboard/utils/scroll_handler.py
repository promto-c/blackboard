# Standard Library Imports
# ------------------------
import time
from collections import deque

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui


# Class Definitions
# -----------------
class MomentumScrollHandler(QtCore.QObject):
    """Handle momentum scrolling for a given widget.
    """

    STACK_VELOCITY_THRESHOLD = 32
    ANGLE_TO_PIXEL_RATIO = 8.0
    MIDDLE_MOUSE_STEP = 120.0
    MAX_TIME_DELTA = 0.2

    # Initialization and Setup
    # ------------------------
    def __init__(self, widget: QtWidgets.QScrollArea, friction: float = 0.95,
                 min_velocity: float = 0.4, velocity_scale: float = 0.02,
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
        self.stacked_x = 0.0
        self.stacked_y = 0.0
        self._time_deltas = deque(maxlen=3)
        self.horizontal_scroll_bar = self.widget.horizontalScrollBar()
        self.vertical_scroll_bar = self.widget.verticalScrollBar()
        self.timer = QtCore.QTimer(interval=self.frame_interval)

        # Initialize middle button pressed flag
        self._is_mouse_button_pressed = False
        self._prev_pos = QtCore.QPoint()
        self._start_pos = QtCore.QPoint()
        self._mouse_move_timestamp = float()

        self._last_wheel_event_time = 0.0

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
    #         elif event.type() == QtCore.QEvent.Type.Wheel:
    #             print('test')
    #             return self.handle_wheel_event(event)
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
        # NOTE: Override the app cursor as a workaround for some widgets wrapped by a graphic view
        # self.widget.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.SizeAllCursor)

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
        self.start(velocity)

        # Restore the cursor to default
        # NOTE: Override the app cursor as a workaround for some widgets wrapped by a graphic view
        # self.widget.unsetCursor()
        QtWidgets.QApplication.restoreOverrideCursor()

    # TODO: Refactor
    def handle_wheel_event(self, event: QtGui.QWheelEvent):
        """Handle wheel events for touchpad scrolling."""
        # # Check if the event is from a touchpad
        # if event.source() == QtCore.Qt.MouseEventSource.MouseEventNotSynthesized:
        #     # It's a regular mouse wheel event; let the default handler process it
        #     return False

        # TODO: Reset self._time_deltas when direction changed
        # Record the current time and calculate time delta from last event
        current_time = time.time()
        time_delta = max(current_time - self._last_wheel_event_time, 0.001)
        self._time_deltas.append(time_delta)
        self._last_wheel_event_time = current_time

        # Calculate the moving average of the last 3 time deltas
        filtered_time_deltas = [t for t in self._time_deltas if t < self.MAX_TIME_DELTA]
        avg_time_delta = sum(filtered_time_deltas) / len(filtered_time_deltas) if filtered_time_deltas else time_delta

        # Get the pixel delta (high-resolution scrolling)
        pixel_delta = event.pixelDelta()

        if pixel_delta.isNull():
            # Some touchpads might not provide pixelDelta, use angleDelta instead
            angle_delta = event.angleDelta()
            is_stepping_wheel_event = self.is_stepping_wheel_event(event)
            # Convert from degrees (1/8th of a degree per unit) to pixels
            pixel_delta = angle_delta / self.ANGLE_TO_PIXEL_RATIO
        else:
            is_stepping_wheel_event = False

        if not is_stepping_wheel_event:
            # Update the scroll bars immediately
            self.horizontal_scroll_bar.setValue(int(self.horizontal_scroll_bar.value() - (pixel_delta.x())))
            self.vertical_scroll_bar.setValue(int(self.vertical_scroll_bar.value() - (pixel_delta.y())))

        # Update the velocity
        velocity = QtCore.QPointF(pixel_delta) / avg_time_delta

        if is_stepping_wheel_event:
            velocity = self._adjust_velocity_for_stepping_wheel(velocity)

        self.start(velocity)

    def _adjust_velocity_for_stepping_wheel(self, velocity: QtCore.QPointF) -> QtCore.QPointF:
        """Adjust velocity for middle mouse events, ensuring a minimum threshold."""
        if velocity.x():
            velocity.setX(max(self.MIDDLE_MOUSE_STEP, abs(velocity.x())) * (1 if velocity.x() >= 0 else -1))
        if velocity.y():
            velocity.setY(max(self.MIDDLE_MOUSE_STEP, abs(velocity.y())) * (1 if velocity.y() >= 0 else -1))
        return velocity * 2

    def is_stepping_wheel_event(self, event: QtGui.QWheelEvent):
        return abs(event.angleDelta().y()) == 120

    def start(self, initial_velocity: QtCore.QPointF):
        """Start the momentum scrolling with the given initial velocity.

        Args:
            initial_velocity: The initial velocity of the scrolling.
        """
        if not isinstance(initial_velocity, QtCore.QPointF):
            initial_velocity = QtCore.QPointF(initial_velocity)

        initial_velocity *= self.velocity_scale

        # NOTE: Stack when velocities are in the same direction and over threshole
        # Handle X component
        if (
            self.velocity.x() * initial_velocity.x() >= 0 and 
            abs(initial_velocity.x()) > self.STACK_VELOCITY_THRESHOLD
        ):
            new_velocity_x = initial_velocity.x() + self.velocity.x()
        else:
            new_velocity_x = initial_velocity.x()

        # Handle Y component
        if (
            self.velocity.y() * initial_velocity.y() >= 0 and 
            abs(initial_velocity.y()) > self.STACK_VELOCITY_THRESHOLD
        ):
            new_velocity_y = initial_velocity.y() + self.velocity.y()
        else:
            new_velocity_y = initial_velocity.y()
        # ---

        self.velocity.setX(new_velocity_x)
        self.velocity.setY(new_velocity_y)

        self.timer.start()

    def stop(self):
        """Stop the momentum scrolling.
        """
        self.timer.stop()

    # Private Methods
    # ---------------
    def _update_scroll_position(self):
        """Update the scrolling based on the current velocity.
        """
        if self.velocity.manhattanLength() < self.min_velocity:
            self.stop()
            return

        # NOTE: Stacked when lower than 1.0
        # ---
        # Handle horizontal velocity
        if abs(self.velocity.x()) < 1:
            self.stacked_x += self.velocity.x()
            if abs(self.stacked_x) < 1:
                diff_x = 0
            else:
                diff_x = self.stacked_x
                self.stacked_x = 0.0
        else:
            diff_x = self.velocity.x()

        # Handle vertical velocity
        if abs(self.velocity.y()) < 1:
            self.stacked_y += self.velocity.y()
            if abs(self.stacked_y) < 1:
                diff_y = 0
            else:
                diff_y = self.stacked_y
                self.stacked_y = 0.0
        else:
            diff_y = self.velocity.y()
        # ---

        # Apply the velocity updates to the scroll bars
        if diff_x != 0:
            self.horizontal_scroll_bar.setValue(self.horizontal_scroll_bar.value() - int(diff_x))
        if diff_y != 0:
            self.vertical_scroll_bar.setValue(self.vertical_scroll_bar.value() - int(diff_y))

        # Apply friction to the velocity
        self.velocity *= self.friction
