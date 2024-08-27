from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon

from blackboard.utils.tree_utils import ItemOverlay

class AnimatedButton(QtWidgets.QPushButton):
    entered = QtCore.Signal()
    leaved = QtCore.Signal()

    def __init__(self, icon: QtGui.QIcon, text: str, hover_icon: QtGui.QIcon = None, hover_text: str = None, 
                 hover_color: QtGui.QColor = QtGui.QColor(QtCore.Qt.GlobalColor.blue), duration: int = 200, parent=None):
        super().__init__(icon, text, parent)
        # Store the arguments
        self.default_icon = icon
        self.hover_icon = hover_icon or icon
        self.default_text = text
        self.hover_text = hover_text or text
        self.animation_duration = duration  # Milliseconds
        self.default_color = QtGui.QColor(33, 33, 33)
        self.hover_color = hover_color
        self._color = self.default_color  # Initialize the color property

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.collapse_width = 24
        self.expand_width = 140
        self.color_anim = QtCore.QPropertyAnimation(self, b'color')
        self.color_anim.setDuration(self.animation_duration)
        self.color_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

        self._width = self.width()
        self.width_anim = QtCore.QPropertyAnimation(self, b"anim_width", self)
        self.width_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.width_anim.setDuration(self.animation_duration)  # Animation duration in milliseconds

        # Additional attributes for text animation
        self.text_timer = QtCore.QTimer(self)  # Timer for updating text
        self.text_timer.timeout.connect(self.update_animated_text)
        self.animated_text = ""  # Holds the current state of animated text
        self.is_animate_text = False
        self.is_animating_text = False  # Flag to indicate if text animation is active

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setIcon(self.default_icon)

        self.setFixedHeight(24)
        self.setProperty('widget-style', 'round')
        self.setStyleSheet(f'text-align: center;background-color: {self.default_color.name(QtGui.QColor.NameFormat.HexRgb)}')

        self.style().unpolish(self)  # Refresh the style
        self.style().polish(self)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect signals to slots
        self.entered.connect(self.set_property_hover)
        self.leaved.connect(self.set_property_default)

    # Public Methods
    # --------------
    def set_animate_text(self, state: bool = True):
        """Set whether the text should be animated.
        """
        self.is_animate_text = state

    def update_animated_text(self):
        """Update the button text to show animated ellipsis.
        """
        if not self.is_animating_text:
            return  # Exit if animation was stopped

        max_dots = 3  # Maximum number of dots in animation
        dot_count = (self.animated_text.count('.') + 1) % (max_dots + 1)  # Cycle dots
        self.animated_text = self.default_text + '.' * dot_count + ' '*(3-dot_count)
        self.setText(self.animated_text)

    def start_text_animation(self):
        """Start the text animation."""
        self.is_animating_text = True
        self.animated_text = self.default_text
        self.text_timer.start(self.animation_duration)
        self.update_animated_text()  # Initial update to set text

    def stop_text_animation(self):
        """Stop the text animation and reset text."""
        self.is_animating_text = False
        self.text_timer.stop()
        self.setText(self.default_text)  # Reset to default text

    def collapse(self):
        """Collapse the button width.
        """
        self.animate_width(self.collapse_width)
        self.setText('')

    def expand(self):
        """Expand the button width.
        """
        self.animate_width(self.expand_width)
        self.setText(self.default_text)

    def set_property_default(self):
        """Set properties to their default values.
        """
        if self.is_animate_text:
            self.start_text_animation()
        else:
            self.setText(self.default_text)
        self.animate_color(self.default_color)
        self.setIcon(self.default_icon)

    def set_property_hover(self):
        """Set properties to their hover values.
        """
        if self.is_animating_text:
            self.stop_text_animation()
        self.setText(self.hover_text)
        self.animate_color(self.hover_color)
        self.setIcon(self.hover_icon)

    def animate_color(self, end_color):
        """Animate the color of the button.
        """
        self.color_anim.stop()
        self.color_anim.setEndValue(end_color)
        self.color_anim.start()

    def animate_width(self, width):
        """Animate the width of the button.
        """
        self.width_anim.stop()  # Stop any ongoing animation
        self.width_anim.setEndValue(width)
        self.width_anim.start()
    
    # Class Properties
    # ----------------
    @QtCore.Property(int)
    def anim_width(self):
        """Get or set the animated width of the button.
        """
        return self._width

    @anim_width.setter
    def anim_width(self, width):
        self._width = width
        self.setFixedWidth(self._width)

    @QtCore.Property(QtGui.QColor)
    def color(self):
        """Get or set the color of the button.
        """
        return self._color

    @color.setter
    def color(self, color: QtGui.QColor):
        self._color = color
        # Format the color to a string
        self.setStyleSheet(f"text-align: center;background-color: {color.name(QtGui.QColor.NameFormat.HexRgb)};")

    # Overridden Methods
    # ------------------
    def enterEvent(self, event):
        """Handle the enter event.
        """
        super().enterEvent(event)
        self.entered.emit()

    def leaveEvent(self, event):
        """Handle the leave event.
        """
        super().leaveEvent(event)
        self.leaved.emit()

class DataFetchingButtons(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.tabler_icon = TablerQIcon(opacity=0.6)

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setFixedWidth(170)
        self.setMaximumWidth(170)

        # Create Layouts
        # --------------
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create Widgets
        # --------------
        # Initialize the "Fetch More" button and "Fetch All" button
        self.fetch_more_button = AnimatedButton(
            icon=self.tabler_icon.chevron_down,
            text='Fetch More',
            hover_icon=self.tabler_icon.chevrons_down,
            hover_color=QtGui.QColor("#178"),
            parent=self)
        self.fetch_all_button = AnimatedButton(
            icon=self.tabler_icon.arrow_down_to_arc,
            text='Fetch All',
            hover_icon=self.tabler_icon.arrow_bar_to_down, 
            hover_color=QtGui.QColor("#187"),
            parent=self)
        self.stop_fetch_button = AnimatedButton(
            icon=self.tabler_icon.loader,
            text='Fetching',
            hover_icon=self.tabler_icon.x, 
            hover_text='Stop', 
            hover_color=QtGui.QColor("#A45"),
            parent=self)
        self.stop_fetch_button.set_animate_text()
        self.stop_fetch_button.hide()

        self.fetch_more_button.expand()
        self.fetch_all_button.collapse()

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.fetch_more_button)
        layout.addWidget(self.fetch_all_button)
        layout.addWidget(self.stop_fetch_button)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect the hover signal from fetch_more_button to show fetch_all_button
        self.fetch_all_button.entered.connect(self.show_fetch_all_button)
        self.fetch_all_button.leaved.connect(self.hide_fetch_all_button)

        # self.fetch_more_button.clicked.connect(self.fetch_more_button.hide)
        # self.fetch_more_button.clicked.connect(self.fetch_all_button.hide)
        # self.fetch_more_button.clicked.connect(self.stop_fetch_button.show)

        # self.fetch_all_button.clicked.connect(self.fetch_more_button.hide)
        # self.fetch_all_button.clicked.connect(self.fetch_all_button.hide)
        # self.fetch_all_button.clicked.connect(self.stop_fetch_button.show)

        # self.stop_fetch_button.clicked.connect(self.stop_fetch_button.hide)
        # self.stop_fetch_button.clicked.connect(self.fetch_more_button.show)
        # self.stop_fetch_button.clicked.connect(self.fetch_all_button.show)

    def show_fetch_all_button(self):
        """Show the 'Fetch All' button.
        """
        self.fetch_all_button.expand()
        self.fetch_more_button.collapse()

    def hide_fetch_all_button(self):
        """Hide the 'Fetch All' button.
        """
        self.fetch_all_button.collapse()
        self.fetch_more_button.expand()

class InlineConfirmButton(QtWidgets.QWidget):

    # Initialization and Setup
    # ------------------------
    def __init__(self, button_text: str = '⨉', confirm_button_text: str = 'Delete', cancel_button_text: str = 'Cancel', parent=None):
        super().__init__(parent)

        # Store the arguments
        self.button_text = button_text
        self.confirm_button_text = confirm_button_text
        self.cancel_button_text = cancel_button_text

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize attributes for the widget.
        """
        self._is_buttons_visible = False
        self._button_size = QtCore.QSize(0, 0)

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setStyleSheet('''
            QPushButton {
                background-color: #222;
                border: none;
            }
            QPushButton:hover {
                background-color: #444;
            }
        ''')

        # Create Layouts
        # --------------
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.addStretch()
        layout.setSpacing(4)

        # Create Widgets
        # --------------
        self.x_button = QtWidgets.QPushButton(self.button_text)
        self.confirm_button = QtWidgets.QPushButton(self.confirm_button_text)
        self.cancel_button = QtWidgets.QPushButton(self.cancel_button_text)

        self.confirm_button.setStyleSheet('''
            QPushButton {
                color: #D66;
                padding: 1 2 1 4;
            }
            QPushButton:hover {
                color: #E44;
            }
        ''')

        confirm_size = self.confirm_button.sizeHint()
        cancel_size = self.cancel_button.sizeHint()
        self._button_size = confirm_size + cancel_size
        self.confirm_button.setVisible(False)  # Initially hidden
        self.cancel_button.setVisible(False)  # Initially hidden

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.x_button)
        layout.addWidget(self.confirm_button)
        layout.addWidget(self.cancel_button)

    def __init_signal_connections(self):
        """Connect signals to slots.
        """
        self.x_button.clicked.connect(self.__toggle_buttons)
        self.cancel_button.clicked.connect(self.__toggle_buttons)

        self.installEventFilter(self)

    def __toggle_buttons(self):
        """Toggle the visibility of the confirm and cancel buttons.
        """
        self._is_buttons_visible = not self._is_buttons_visible
        self.x_button.setVisible(not self._is_buttons_visible)
        self.confirm_button.setVisible(self._is_buttons_visible)
        self.cancel_button.setVisible(self._is_buttons_visible)

    def sizeHint(self) -> QtCore.QSize:
        """Provide a size hint for the widget based on the visibility of buttons.
        """
        return self._button_size

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Event filter to detect movement or focus change.
        """
        if event.type() == QtCore.QEvent.WindowDeactivate or event.type() == QtCore.QEvent.Move:
            if self._is_buttons_visible:
                self.__toggle_buttons()
        
        return super().eventFilter(obj, event)

class ItemOverlayButton(ItemOverlay):

    triggered = QtCore.Signal(object)

    def __init__(self, button_text: str = '⨉', confirm_button_text: str = 'Delete', cancel_button_text: str = 'Cancel', parent=None):
        self.button = InlineConfirmButton(button_text=button_text, confirm_button_text=confirm_button_text, cancel_button_text=cancel_button_text, parent=parent)
        super().__init__(self.button)

        self.button.confirm_button.clicked.connect(lambda :self.triggered.emit(self.current_item))


if __name__ == "__main__":
    import sys
    import blackboard as bb
    app = QtWidgets.QApplication(sys.argv)
    bb.theme.set_theme(app, 'dark')
    widget = DataFetchingButtons()
    widget.show()
    sys.exit(app.exec_())
