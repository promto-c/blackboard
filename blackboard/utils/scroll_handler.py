# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore


# Class Definitions
# -----------------
class MomentumScrollHandler(QtCore.QObject):
    """Handles momentum scrolling for a given widget.
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, widget: QtWidgets.QScrollArea, friction: float = 0.95,
                 min_velocity: float = 0.1, velocity_scale: float = 0.05,
                 frame_interval: int = 16):
        """Initializes the MomentumScrollHandler.

        Args:
            widget: The widget to apply momentum scrolling to.
            friction: The friction applied to reduce the scrolling speed.
            min_velocity: The minimum velocity threshold to stop scrolling.
            velocity_scale: The scale factor for the initial velocity.
            frame_interval: The timer interval in milliseconds for updating the scroll position.
        """
        super().__init__()

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
        """Initializes the attributes.
        """
        self.velocity = QtCore.QPointF()
        self.horizontal_scrollbar = self.widget.horizontalScrollBar()
        self.vertical_scrollbar = self.widget.verticalScrollBar()
        self.timer = QtCore.QTimer()

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        self.timer.timeout.connect(self._on_timeout)

    # Public Methods
    # --------------
    def start(self, initial_velocity: QtCore.QPointF):
        """Starts the momentum scrolling with the given initial velocity.

        Args:
            initial_velocity: The initial velocity of the scrolling.
        """
        self.velocity = initial_velocity * self.velocity_scale
        self.timer.start(self.frame_interval)

    def stop(self):
        """Stops the momentum scrolling.
        """
        self.timer.stop()

    # Private Methods
    # ---------------
    def _on_timeout(self):
        """Handles the timer timeout event to update the scrolling.
        """
        if self.velocity.manhattanLength() < self.min_velocity:
            self.stop()
            return

        self.horizontal_scrollbar.setValue(self.horizontal_scrollbar.value() - self.velocity.x())
        self.vertical_scrollbar.setValue(self.vertical_scrollbar.value() - self.velocity.y())

        self.velocity *= self.friction
