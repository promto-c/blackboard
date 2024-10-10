from PyQt5 import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon
import os
import re

# Define a consistent color palette
PRIMARY_COLOR = "#222"
SECONDARY_COLOR = "#333"
ACCENT_COLOR = "#0A84FF"
TEXT_COLOR = "#FFF"
HOVER_COLOR = "#3A3A3C"
DISABLED_COLOR = "#555"
STATUS_COLOR = {
    "To Do": "#F90",        # Orange
    "In Progress": "#FC0",  # Yellow
    "Done": "#3C5",         # Green
}

# Define the order of statuses
STATUS_ORDER = ["To Do", "In Progress", "Done"]

def set_markdown_with_simple_line_breaks(content):
    """Set markdown content with line breaks replaced only for regular lines."""
    # Regular expression to find new lines not preceded by Markdown symbols (like lists or headers)
    # This pattern looks for a new line that is not preceded by list markers, headers, or other markdown constructs.
    content_with_line_breaks = re.sub(
        r'(?<![-*#>\d\.\s])\n(?![-*#>\d\.\s])',  # Negative lookbehind and lookahead to avoid Markdown symbols
        "<br />",  # Replace with HTML line break
        content
    )
    return content_with_line_breaks


class StatusNextStepWidget(QtWidgets.QWidget):
    status_changed = QtCore.pyqtSignal(str)  # Signal emitted when status changes

    def __init__(self, current_status="To Do", container: 'TransparentFloatingLayout' = None):
        super().__init__(container)


        self.container = container
        
        self.current_status = current_status
        self.clicked = False  # Track the clicked state

        # Setup parallel animation group for synchronized animations
        self.parallel_animation_group = QtCore.QParallelAnimationGroup()

        # Main layout
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        # Create the status combobox
        self.status_combobox = QtWidgets.QComboBox()
        self.status_combobox.addItems(STATUS_ORDER)
        self.status_combobox.setCurrentText(self.current_status)
        self.status_combobox.setFixedHeight(20)
        self.status_combobox.setStyleSheet(self.get_combobox_style(self.current_status))
        self.status_combobox.currentTextChanged.connect(self.on_status_changed)
        self.status_combobox.wheelEvent = self.wheelEvent
        self.main_layout.addWidget(self.status_combobox)

        # Spacer to push the button to the right
        self.main_layout.addStretch()

        # Create the next step button
        self.next_step_button = QtWidgets.QPushButton()
        self.next_step_button.setFixedHeight(20)
        self.next_step_button.setFixedWidth(30)
        self.next_step_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.next_step_button.setStyleSheet(self.get_button_style())
        self.next_step_button.clicked.connect(self.mark_as_next_status)
        self.main_layout.addWidget(self.next_step_button)

        # Set hover event handlers
        self.next_step_button.installEventFilter(self)

        # Active animations list to manage animation lifetimes
        self.active_animations = []
        self.update_button()  # Initialize button state

    def get_next_status(self):
        """Get the next status based on the current status."""
        current_index = STATUS_ORDER.index(self.current_status)
        if current_index < len(STATUS_ORDER) - 1:
            return STATUS_ORDER[current_index + 1]
        return None

    def get_combobox_style(self, status):
        """Return the stylesheet for the combobox based on the status."""
        return f"""
            QComboBox {{
                background-color: {STATUS_COLOR.get(status, SECONDARY_COLOR)};
                border: none;
                color: {TEXT_COLOR};
                border-radius: 10;
                padding-left: 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {SECONDARY_COLOR};
                selection-background-color: {HOVER_COLOR};
                color: {TEXT_COLOR};
            }}
        """

    def get_button_style(self):
        """Return the stylesheet for the button."""
        return f"""
            QPushButton {{
                background-color: #0AA;
                color: {TEXT_COLOR};
                border: none;
                border-radius: 10;
            }}
            QPushButton:disabled {{
                background-color: {DISABLED_COLOR};
                color: gray;
            }}
        """

    def update_button(self):
        """Update the button icon and tooltip."""
        next_status = self.get_next_status()
        if next_status:
            self.next_step_button.setEnabled(True)
            self.next_step_button.setToolTip(f"Mark as '{next_status}'")
            self.next_step_button.setIcon(TablerQIcon.chevron_right)
        else:
            self.next_step_button.setEnabled(False)
            self.next_step_button.setToolTip("No further status")
            self.next_step_button.setIcon(TablerQIcon.check)

    def on_status_changed(self, status_text):
        """Handle changes in the combobox selection."""
        self.current_status = status_text
        self.status_combobox.setStyleSheet(self.get_combobox_style(status_text))
        self.update_button()
        self.status_changed.emit(self.current_status)

    def mark_as_next_status(self):
        """Advance the task to the next status with a transition color animation."""
        self.clicked = True  # Set clicked state to True
        next_status = self.get_next_status()
        if next_status:
            # Check if the next status is in the currently visible statuses in the parent
            visible_statuses = self.container.get_visible_statuses()

            # Otherwise, animate the transition
            self.status_combobox.setCurrentText(next_status)

            if next_status in visible_statuses:
                self.animate_back()
            else:
                self.next_step_button.setText("")

            gradient_animation = QtCore.QVariantAnimation()
            gradient_animation.setDuration(300)
            gradient_animation.setStartValue(QtGui.QColor(STATUS_COLOR.get(self.current_status, SECONDARY_COLOR)))
            gradient_animation.setEndValue(QtGui.QColor(STATUS_COLOR.get(next_status, SECONDARY_COLOR)))
            gradient_animation.valueChanged.connect(self.apply_gradient_color)
            gradient_animation.start()

    def apply_gradient_color(self, color):
        """Apply the gradient color to the combobox background."""
        self.status_combobox.setStyleSheet(f"""
            QComboBox {{
                background-color: {color.name()};
                border: none;
                color: {TEXT_COLOR};
                border-radius: 10;
                padding-left: 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {SECONDARY_COLOR};
                selection-background-color: {HOVER_COLOR};
                color: {TEXT_COLOR};
            }}
        """)

    def animate_back(self):
        """Animate the button back to its original size and clear hover state.
        """
        self.next_step_button.setText("")
        self.parallel_animation_group.clear()  # Clear existing animations

        # Create animations to reset button size
        shrink_button_animation = QtCore.QPropertyAnimation(self.next_step_button, b"minimumWidth")
        shrink_button_animation.setDuration(300)
        shrink_button_animation.setStartValue(self.next_step_button.width())
        shrink_button_animation.setEndValue(30)
        shrink_button_animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.parallel_animation_group.addAnimation(shrink_button_animation)

        # Extend combobox animation back to original
        extend_combobox_animation = QtCore.QPropertyAnimation(self.status_combobox, b"minimumWidth")
        extend_combobox_animation.setDuration(300)
        extend_combobox_animation.setStartValue(self.status_combobox.width())
        extend_combobox_animation.setEndValue(150)
        self.parallel_animation_group.addAnimation(extend_combobox_animation)

        # Start the parallel animation group and reset click state
        self.parallel_animation_group.finished.connect(self.reset_hover_state)
        self.parallel_animation_group.start()

    def reset_hover_state(self):
        """Reset hover state to allow animations when hovering again."""
        self.clicked = False  # Reset the clicked state

    def eventFilter(self, obj, event):
        """Handle hover events for the next step button.
        """
        if obj == self.next_step_button and not self.clicked:  # Only handle hover if not clicked
            if event.type() == QtCore.QEvent.Enter and self.next_step_button.isEnabled():
                self.handle_hover_enter()
            elif event.type() == QtCore.QEvent.Leave:
                self.handle_hover_leave()
        return super().eventFilter(obj, event)

    def handle_hover_enter(self):
        """Handle hover enter event to expand the button and contract combobox."""
        self.next_step_button.setText(f"Mark as '{self.get_next_status()}'")
        self.parallel_animation_group.clear()  # Clear existing animations

        # Create animations for expanding button and contracting combobox
        expand_button_animation = QtCore.QPropertyAnimation(self.next_step_button, b"minimumWidth")
        expand_button_animation.setDuration(300)
        expand_button_animation.setStartValue(self.next_step_button.width())
        expand_button_animation.setEndValue(120)
        expand_button_animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.parallel_animation_group.addAnimation(expand_button_animation)

        shorten_combobox_animation = QtCore.QPropertyAnimation(self.status_combobox, b"minimumWidth")
        shorten_combobox_animation.setDuration(300)
        shorten_combobox_animation.setStartValue(self.status_combobox.width())
        shorten_combobox_animation.setEndValue(max(80, self.status_combobox.width() - 70))
        self.parallel_animation_group.addAnimation(shorten_combobox_animation)

        # Start the parallel animation group
        self.parallel_animation_group.start()

    def handle_hover_leave(self):
        """Handle hover leave event to shrink the button and expand combobox.
        """
        if self.clicked:
            return

        self.animate_back()

    def showEvent(self, event):
        self.animate_back()
        super().showEvent(event)

# Define a utility class for UI-related common methods
class UIUtil:
    """Utility class for common UI methods."""

    @staticmethod
    def create_shadow_effect(blur_radius=15, x_offset=0, y_offset=5, color=QtGui.QColor(0, 0, 0, 150)):
        """Create and return a shadow effect for the floating card or any widget.

        Args:
            blur_radius (int): The blur radius of the shadow.
            x_offset (int): The horizontal offset of the shadow.
            y_offset (int): The vertical offset of the shadow.
            color (QColor): The color of the shadow effect.

        Returns:
            QGraphicsDropShadowEffect: Configured shadow effect.
        """
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setXOffset(x_offset)
        shadow.setYOffset(y_offset)
        shadow.setColor(color)
        return shadow

    @staticmethod
    def apply_animation(widget, property_name, start_value, end_value, duration=300):
        """Apply a simple property animation to a widget."""
        animation = QtCore.QPropertyAnimation(widget, property_name.encode())
        animation.setDuration(duration)
        animation.setStartValue(start_value)
        animation.setEndValue(end_value)
        animation.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        animation.start()
        # Keep a reference to prevent garbage collection
        widget.animation = animation

class AutoResizingTextBrowser(QtWidgets.QTextBrowser):

    MAX_HEIGHT = 300  # Set the maximum height as a class attribute

    def __init__(self, parent=None):
        """Initialize the auto-resizing text browser.

        Args:
            parent (Optional[QWidget]): The parent widget.
        """
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.document().contentsChanged.connect(self.adjust_height_to_content)

        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {SECONDARY_COLOR};
                border: 1px solid gray;
                color: {TEXT_COLOR};
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
                padding: 10px;
            }}
        """)
        self.setOpenLinks(False)

    def sizeHint(self):
        """Override sizeHint to provide the height based on the document content.
        """
        document_height = self._calculate_content_height()
        return QtCore.QSize(self.viewport().width(), document_height)

    def adjust_height_to_content(self):
        """Adjust the height of the widget to fit the document content, respecting the maximum height.
        """
        height = self._calculate_content_height()
        # Use min() to ensure the height does not exceed MAX_HEIGHT
        self.setFixedHeight(min(height, self.MAX_HEIGHT))

    def _calculate_content_height(self):
        """Calculate the total height needed to display the document content.
        """
        # Get the document height, considering the current width of the QTextBrowser
        document_width = self.viewport().width()
        self.document().setTextWidth(document_width)  # Set text width to match the widget's width
        document_height = int(self.document().size().height())  # Convert to integer
        # Calculate additional margins if necessary
        vertical_margins = self.contentsMargins().top() + self.contentsMargins().bottom()
        return document_height + vertical_margins

    def resizeEvent(self, event):
        """Handle the widget's resize event.
        """
        super().resizeEvent(event)
        # Adjust height when the width changes
        self.adjust_height_to_content()

class FloatingCard(QtWidgets.QWidget):
    """Custom floating card widget designed for feedback or comments.
    """

    # Initialization and Setup
    # ------------------------

    # Signal emitted when the card's status changes
    status_changed = QtCore.pyqtSignal(object, str, str)  # Emits self, previous_status, new_status

    def __init__(self, parent=None, content="", attached_image_path=None):
        super().__init__(parent)

        # Store the arguments
        self.attached_image_path = attached_image_path
        self.content = content
        self.current_status = "To Do"  # Initialize current status

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Set size policy to expand to the available width
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        # Apply shadow effect using utility method
        self.setGraphicsEffect(UIUtil.create_shadow_effect())

        # Set size policy to expand to the available width
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        # Create Layouts
        # --------------
        # Main layout of the card
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 0, 5, 20)
        self.main_layout.setSpacing(0)

        # Header layout containing the title, status/next step widget, and close button
        header_widget = QtWidgets.QWidget(self)
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_widget.setFixedHeight(40)
        header_widget.setStyleSheet(f"""
            background-color: {PRIMARY_COLOR}; 
            border-top-left-radius: 15px; 
            border-top-right-radius: 15px; 
            color: {TEXT_COLOR};
        """)

        # Title label
        card_label = QtWidgets.QLabel("Task Note", header_widget)
        card_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        header_layout.addWidget(card_label)

        # Spacer
        header_layout.addStretch()

        # Status and next step widget
        self.status_widget = StatusNextStepWidget(current_status=self.current_status, container=self.parent())
        header_layout.addWidget(self.status_widget)

        # Add header to main layout
        self.main_layout.addWidget(header_widget)

        # Comment Text Area with markdown support
        self.comment_area = AutoResizingTextBrowser(self)

        # Add attached image if present
        if self.attached_image_path:
            self.image_label = QtWidgets.QLabel(self)
            self.image_label.setAlignment(QtCore.Qt.AlignCenter)
            self.main_layout.addWidget(self.image_label)
            self.update_image(self.attached_image_path)

        content = set_markdown_with_simple_line_breaks(self.content)
        self.comment_area.setMarkdown(content)

        self.main_layout.addWidget(self.comment_area)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        # Connect the anchorClicked signal to handle user mentions
        self.comment_area.anchorClicked.connect(self._handle_user_mentions)

        # Connect the status_changed signal
        self.status_widget.status_changed.connect(self.on_status_changed)

    def on_status_changed(self, new_status):
        """Handle when status is changed."""
        previous_status = self.current_status
        self.current_status = new_status
        self.status_changed.emit(self, previous_status, new_status)

    def update_image(self, image_path):
        """Update the image label with a scaled version of the image to fit the card width."""
        pixmap = QtGui.QPixmap(image_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                # TODO: Set to appropriate size
                340, 
                pixmap.height(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def _handle_user_mentions(self, url):
        """Handle clicks on user mentions."""
        user = url.toString().lstrip("user:")
        QtWidgets.QMessageBox.information(self, "User Mention", f"You clicked on @{user}")

    def animate_out(self, direction='right'):
        """Animate the card sliding out in the specified direction and remove it from the layout.

        Args:
            direction (str): Direction to animate the card ('left' or 'right').
        """
        # Disable the card during animation
        self.setEnabled(False)

        if self.status_widget.parallel_animation_group.state() == QtCore.QAbstractAnimation.Running:
            # Stop the current animation and re-calculate based on new size
            self.status_widget.parallel_animation_group.stop()

        # Animation to slide the card out to the specified direction
        self.animation = QtCore.QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        start_pos = self.pos()

        # Determine the end position based on the direction
        offset = 500 if direction == 'right' else -500  # Move 500 pixels left or right
        end_pos = self.pos() + QtCore.QPoint(offset, 0)  # Slide left or right

        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)
        self.animation.finished.connect(self.on_animation_finished)
        self.animation.start()

    def on_animation_finished(self):
        """Handle the cleanup after the animation finishes."""
        # Remove the card from its parent layout
        self.hide()
        self.setEnabled(True)

class TransparentFloatingLayout(QtWidgets.QWidget):
    """Main widget holding a transparent scrollable layout with feedback cards, drag functionality, and filter buttons."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Feedback and Comment System")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {PRIMARY_COLOR};
                color: {TEXT_COLOR};
            }}
        """)

        # Enable dragging and closing on the entire layout
        self.is_dragging = False
        self.offset = None

        # Main layout for the entire widget
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Header widget with drag area and close button for the entire layout
        header_widget = QtWidgets.QWidget(self)
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_widget.setFixedHeight(40)
        header_widget.setStyleSheet(f"""
            background-color: {PRIMARY_COLOR}; 
            border-radius: 15px;
            color: {TEXT_COLOR};
        """)

        # Header widget with application title
        self.app_title = QtWidgets.QLabel("Feedback & Comments", header_widget)
        self.app_title.setStyleSheet("font-size: 16px; color: #FFFFFF;")
        header_layout.addWidget(self.app_title)

        # Spacer to push buttons to the right
        header_layout.addStretch()

        # Toggle background button
        self.toggle_bg_button = QtWidgets.QPushButton(TablerQIcon.background, '', header_widget)
        self.toggle_bg_button.setFixedSize(20, 20)
        self.toggle_bg_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: {TEXT_COLOR};
            }}
            QPushButton:hover {{
                color: cyan;
            }}
        """)

        # Collapse/Expand button
        self.collapse_button = QtWidgets.QPushButton("−", header_widget)
        self.collapse_button.setFixedSize(20, 20)
        self.collapse_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: {TEXT_COLOR};
            }}
            QPushButton:hover {{
                color: cyan;
            }}
        """)

        # Close button for the entire layout
        self.layout_close_button = QtWidgets.QPushButton("✕", header_widget)
        self.layout_close_button.setFixedSize(20, 20)
        self.layout_close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: {TEXT_COLOR};
            }}
            QPushButton:hover {{
                color: red;
            }}
        """)

        # Create a second line for the filter buttons
        self.filter_widget = QtWidgets.QWidget(self)
        filter_layout = QtWidgets.QHBoxLayout(self.filter_widget)
        filter_layout.setContentsMargins(10, 5, 10, 5)
        self.filter_widget.setFixedHeight(40)
        self.filter_widget.setStyleSheet(f"""
            background-color: rgba(60, 60, 60, 200);
            border-radius: 10px;
            color: {TEXT_COLOR};
        """)

        # Filter buttons (e.g., show "To Do", "In Progress", or "Done" cards)
        self.filter_group = QtWidgets.QButtonGroup()
        self.filter_buttons = {}
        for status in ["All"] + STATUS_ORDER:
            button = QtWidgets.QPushButton(status, self.filter_widget)
            button.setCheckable(True)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(70, 70, 70, 200);
                    border: 1px solid gray;
                    color: {TEXT_COLOR};
                }}
                QPushButton:hover {{
                    background-color: rgba(90, 90, 90, 200);
                }}
                QPushButton:checked {{
                    background-color: rgba(100, 100, 100, 200);
                    border: 1px solid cyan;
                }}
            """)
            button.clicked.connect(self.on_filter_button_clicked)
            filter_layout.addWidget(button)
            self.filter_buttons[status] = button
            self.filter_group.addButton(button)
        self.filter_buttons["All"].setChecked(True)  # Default to show all cards

        # Make filter buttons single-select by default
        self.filter_group.setExclusive(True)

        # Add Widgets to Layouts
        # ----------------------
        header_layout.addWidget(self.toggle_bg_button)
        header_layout.addWidget(self.collapse_button)
        header_layout.addWidget(self.layout_close_button)

        # Add header to the main layout
        self.main_layout.addWidget(header_widget)

        # Add the filter widget to the main layout
        self.main_layout.addWidget(self.filter_widget)

        # Scrollable area for feedback cards
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")  # Transparent scroll area background

        # Container for scrollable area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(QtCore.Qt.AlignTop)  # Align cards to the top
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Set transparent background for scroll content
        self.scroll_content.setStyleSheet("background: transparent;")

        # NOTE: Example: Add a few floating cards below the header inside the scrollable area
        card_count = 4
        for i in range(card_count):
            content = f"This is a comment or feedback. Mentioning @user{i}."
            card = FloatingCard(self, content=content)
            self.add_card(card)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # Sticky bar at the bottom for new task and attachment
        sticky_bar = QtWidgets.QWidget(self)
        sticky_layout = QtWidgets.QHBoxLayout(sticky_bar)
        sticky_layout.setContentsMargins(10, 5, 10, 5)
        sticky_bar.setStyleSheet(f"""
            background-color: {PRIMARY_COLOR};
            border-radius: 10px;
            color: {TEXT_COLOR};
        """)

        # Attach image button
        self.attach_button = QtWidgets.QToolButton(sticky_bar)
        self.attach_button.setIcon(TablerQIcon.image_in_picture)
        self.attach_button.setToolTip("Attach Image")
        self.attach_button.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
            }}
        """)

        sticky_layout.addWidget(self.attach_button)

        # Input field for new task or comment
        self.new_task_input = QtWidgets.QPlainTextEdit(sticky_bar)
        self.new_task_input.setPlaceholderText("Add a new task or comment... Use @username to mention someone.")
        self.new_task_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.new_task_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {SECONDARY_COLOR};
                border: 1px solid gray;
                color: {TEXT_COLOR};
                padding: 5px;
            }}
        """)

        sticky_layout.addWidget(self.new_task_input)

        # Add button for adding new task or comment with icon
        self.add_button = QtWidgets.QToolButton(sticky_bar)
        self.add_button.setIcon(TablerQIcon.plus)
        self.add_button.setToolTip("Add Task")
        self.add_button.setEnabled(False)  # Disable add button initially
        self.add_button.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                color: {TEXT_COLOR};
                font-size: 16px;
            }}
            QToolButton:enabled:hover {{
                color: cyan;
            }}
            QToolButton:disabled {{
                color: {DISABLED_COLOR};
            }}
        """)

        sticky_layout.addWidget(self.add_button)

        self.main_layout.addWidget(sticky_bar)

        self.resize(400, 800)

        # Apply shadow effect using utility method
        self.setGraphicsEffect(UIUtil.create_shadow_effect())
        self.adjust_input_height()

        self.collapse_button.clicked.connect(self.toggle_card_area)
        self.layout_close_button.clicked.connect(self.close)

        self.attach_button.clicked.connect(self.attach_screenshot)
        self.new_task_input.textChanged.connect(self.adjust_input_height)
        self.new_task_input.textChanged.connect(self.toggle_add_button_state)
        self.add_button.clicked.connect(self.add_new_task)

        # Add keyboard shortcuts for common actions
        self.add_task_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self)
        self.add_task_shortcut.activated.connect(self.add_new_task)

    def on_filter_button_clicked(self):
        """Handle filter button click to clear other selections if not in multi-select mode."""
        if self.filter_group.exclusive():
            for status, button in self.filter_buttons.items():
                if button != self.sender():
                    button.setChecked(False)
        self.filter_cards()

    def keyPressEvent(self, event):
        """Handle Shift key press to enable multi-selection for filters."""
        if event.key() == QtCore.Qt.Key_Shift:
            self.filter_group.setExclusive(False)

    def keyReleaseEvent(self, event):
        """Handle Shift key release to revert to single-selection for filters."""
        if event.key() == QtCore.Qt.Key_Shift:
            self.filter_group.setExclusive(True)

    def toggle_add_button_state(self):
        """Enable or disable the Add button based on whether the input field is empty."""
        if self.new_task_input.toPlainText().strip():
            self.add_button.setEnabled(True)
        else:
            self.add_button.setEnabled(False)

    def adjust_input_height(self):
        """Adjust the height of the input field based on content."""
        document_height = self.new_task_input.document().blockCount()
        # Get line height using font metrics
        line_height = QtGui.QFontMetrics(self.new_task_input.font()).height()
        # Calculate the new height and set it
        new_height = int(min(100, document_height * line_height + 20))
        self.new_task_input.setFixedHeight(new_height)

    def attach_screenshot(self):
        """Open a file dialog to select a screenshot file."""
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Attach Screenshot", "", "Images (*.png *.jpg *.bmp)")
        if file_path:
            # Append the screenshot information to the new task input field
            self.attached_image_path = file_path
            self.new_task_input.setPlainText(f"Attached Screenshot: {os.path.basename(file_path)}\n{self.new_task_input.toPlainText()}")

    def add_new_task(self):
        """Add a new task or comment as a floating card."""
        new_task_text = self.new_task_input.toPlainText().strip()

        if not new_task_text:
            return

        # Ensure "To Do" status is visible in the filter
        self.ensure_status_visible("To Do")

        # Handle user mentions by converting @username to clickable links
        formatted_text = self.format_user_mentions(new_task_text)
        new_card = FloatingCard(self, content=formatted_text, attached_image_path=getattr(self, 'attached_image_path', None))
        self.add_card(new_card)
        self.new_task_input.clear()  # Clear the input field after adding
        self.attached_image_path = None  # Reset the attached image path

        # Scroll to the bottom of the scroll area
        QtCore.QTimer.singleShot(0, self.scroll_to_bottom)

    def ensure_status_visible(self, status):
        """Ensure that the given status is visible by modifying the filter if necessary.

        Args:
            status (str): The status to ensure visibility.
        """
        visible_statuses = self.get_visible_statuses()
        if status not in visible_statuses:
            self.filter_group.setExclusive(False)
            # Automatically select the given status if not currently visible
            if status in self.filter_buttons:
                self.filter_buttons[status].setChecked(True)
                self.filter_cards()  # Refresh the filter to display cards with the new status
            self.filter_group.setExclusive(True)

    def scroll_to_bottom(self):
        """Smoothly scroll to the bottom of the scroll area."""
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_animation = QtCore.QPropertyAnimation(scroll_bar, b"value")
        scroll_animation.setDuration(500)
        scroll_animation.setStartValue(scroll_bar.value())
        scroll_animation.setEndValue(scroll_bar.maximum())
        scroll_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        scroll_animation.start()
        self.scroll_animation = scroll_animation  # Keep a reference to prevent garbage collection

    def format_user_mentions(self, text):
        """Convert @username mentions to clickable links in markdown."""
        def replace_mention(match):
            username = match.group(1)
            return f"[ @{username} ](user:{username})"
        return re.sub(r'@(\w+)', replace_mention, text)

    def filter_cards(self):
        """Filter cards based on the selected filter button."""
        selected_status = [status for status, button in self.filter_buttons.items() if button.isChecked()]
        if "All" in selected_status or not selected_status:
            selected_status = STATUS_ORDER  # Show all cards if 'All' is selected or none selected
        for i in range(self.scroll_layout.count()):
            card = self.scroll_layout.itemAt(i).widget()
            card_status = card.status_widget.status_combobox.currentText()
            card.setVisible(card_status in selected_status)

    def toggle_card_area(self):
        """Toggle the visibility of the card area (expand/collapse)."""
        if self.scroll_area.isVisible():
            UIUtil.apply_animation(self.scroll_area, "maximumHeight", self.scroll_area.height(), 0)
            self.filter_widget.setVisible(False)
            self.scroll_area.setVisible(False)
            self.collapse_button.setText("+")  # Change button to show expand icon
        else:
            self.filter_widget.setVisible(True)
            self.scroll_area.setVisible(True)
            UIUtil.apply_animation(self.scroll_area, "maximumHeight", 0, 800)
            self.collapse_button.setText("−")  # Change button to show collapse icon

    def add_card(self, card: 'FloatingCard'):
        """Add a card to the layout with a fade-in animation."""
        card.setGraphicsEffect(UIUtil.create_shadow_effect())
        card.setVisible(False)
        self.scroll_layout.addWidget(card)
        card.setVisible(True)
        # Connect to card's status_changed signal
        card.status_changed.connect(self.on_card_status_changed)

    def get_visible_statuses(self):
        """Return a list of statuses that are currently visible based on the filter."""
        selected_status = [status for status, button in self.filter_buttons.items() if button.isChecked()]
        if "All" in selected_status or not selected_status:
            return STATUS_ORDER  # Return all statuses if 'All' is selected or none is selected
        return selected_status

    def on_card_status_changed(self, card: 'FloatingCard', previous_status, new_status):
        """Handle when a card's status is changed.
        """
        selected_status = self.get_visible_statuses()

        is_currently_visible = card.isVisible()
        should_be_visible = new_status in selected_status

        if is_currently_visible and not should_be_visible:
            # Card should be hidden, animate it out to left or right
            direction = "right" if STATUS_ORDER.index(new_status) > STATUS_ORDER.index(previous_status) else "left"
            card.animate_out(direction)
        else:
            # No change in visibility
            pass

    def mousePressEvent(self, event):
        """Start dragging the entire layout when the mouse is pressed on the layout drag area."""
        if event.button() == QtCore.Qt.LeftButton and self.app_title.geometry().contains(event.pos()):
            self.is_dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        """Handle dragging of the entire layout."""
        if self.is_dragging:
            self.move(self.mapToParent(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        """End dragging when the mouse is released."""
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = False
            self.offset = None

if __name__ == "__main__":
    from blackboard.theme import set_theme
    app = QtWidgets.QApplication([])
    set_theme(app)
    window = TransparentFloatingLayout()
    window.show()
    app.exec_()
