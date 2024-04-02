from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon


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
        """Set up the initial values for the widget.
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
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
        """
        self.setIcon(self.default_icon)

        self.setFixedHeight(24)
        self.setProperty('widget-style', 'round')
        self.setStyleSheet(f'text-align: center;background-color: {self.default_color.name(QtGui.QColor.NameFormat.HexRgb)}')

        self.style().unpolish(self)  # Refresh the style
        self.style().polish(self)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.entered.connect(self.set_property_hover)
        self.leaved.connect(self.set_property_default)

    # Public Methods
    # --------------
    def set_animate_text(self, state: bool = True):
        self.is_animate_text = state

    def update_animated_text(self):
        """Update the button text to show animated ellipsis."""
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
        self.animate_width(self.collapse_width)
        self.setText('')

    def expand(self):
        self.animate_width(self.expand_width)
        self.setText(self.default_text)

    def set_property_default(self):
        if self.is_animate_text:
            self.start_text_animation()
        else:
            self.setText(self.default_text)
        self.animate_color(self.default_color)
        self.setIcon(self.default_icon)

    def set_property_hover(self):
        if self.is_animating_text:
            self.stop_text_animation()
        self.setText(self.hover_text)
        self.animate_color(self.hover_color)
        self.setIcon(self.hover_icon)

    def animate_color(self, end_color):
        self.color_anim.stop()
        self.color_anim.setEndValue(end_color)
        self.color_anim.start()

    def animate_width(self, width):
        self.width_anim.stop()  # Stop any ongoing animation
        self.width_anim.setEndValue(width)
        self.width_anim.start()
    
    # Class Properties
    # ----------------
    @QtCore.Property(int)
    def anim_width(self):
        return self._width

    @anim_width.setter
    def anim_width(self, width):
        self._width = width
        self.setFixedWidth(self._width)

    @QtCore.Property(QtGui.QColor)
    def color(self):
        return self._color

    @color.setter
    def color(self, color: QtGui.QColor):
        self._color = color
        # Format the color to a string
        self.setStyleSheet(f"text-align: center;background-color: {color.name(QtGui.QColor.NameFormat.HexRgb)};")

    # Overridden Methods
    # ------------------
    def enterEvent(self, event):
        super().enterEvent(event)
        self.entered.emit()

    def leaveEvent(self, event):
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
        """Set up the initial values for the widget.
        """
        self.tabler_icon = TablerQIcon(opacity=0.6)

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts, and setting the icons for the widgets.
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
        """Set up signal connections between widgets and slots.
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
        self.fetch_all_button.expand()
        self.fetch_more_button.collapse()

    def hide_fetch_all_button(self):
        self.fetch_all_button.collapse()
        self.fetch_more_button.expand()


if __name__ == "__main__":
    import sys
    import blackboard as bb
    app = QtWidgets.QApplication(sys.argv)
    bb.theme.set_theme(app, 'dark')
    widget = DataFetchingButtons()
    widget.show()
    sys.exit(app.exec_())
