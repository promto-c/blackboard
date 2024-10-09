from PyQt5 import QtWidgets, QtCore, QtGui

# Mockup class for StatusNextStepWidget
class StatusNextStepWidget(QtWidgets.QWidget):
    def __init__(self, current_status, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        label = QtWidgets.QLabel(current_status, self)
        layout.addWidget(label)

# Mockup class for UIUtil to provide the create_shadow_effect method
class UIUtil:
    @staticmethod
    def create_shadow_effect():
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QtGui.QColor(0, 0, 0, 100))
        shadow.setOffset(3, 3)
        return shadow

# Function to convert a string with line breaks into Markdown compatible content
def set_markdown_with_simple_line_breaks(content):
    return content.replace('\n', '  \n')  # Markdown line breaks require two spaces before newline

class FloatingCard(QtWidgets.QWidget):
    """Custom floating card widget designed for feedback or comments.
    """

    def __init__(self, parent=None, content="", attached_image_paths=None):
        super().__init__(parent)
        self.attached_image_paths = attached_image_paths if attached_image_paths else []
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        # Apply shadow effect using utility method
        self.setGraphicsEffect(UIUtil.create_shadow_effect())

        # Set fixed width for the card
        self.fixed_width = 400  # You can adjust this value as needed
        self.setFixedWidth(self.fixed_width)

        # Main layout of the card
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header layout containing the drag area and the status/next step widget
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

        # Drag area
        self.card_label = QtWidgets.QLabel("Task Note", header_widget)
        self.card_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        header_layout.addWidget(self.card_label)

        # Status and next step widget
        self.status_widget = StatusNextStepWidget(current_status="To Do", parent=header_widget)
        
        header_layout.addStretch()
        header_layout.addWidget(self.status_widget)

        # Add header to main layout
        self.main_layout.addWidget(header_widget)

        # Comment Text Area with markdown support
        self.comment_area = QtWidgets.QTextBrowser(self)
        content = set_markdown_with_simple_line_breaks(content)
        self.comment_area.setMarkdown(content)
        self.comment_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.comment_area.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {SECONDARY_COLOR};
                border: none;
                color: {TEXT_COLOR};
                padding: 10px;
            }}
        """)
        self.comment_area.setOpenLinks(False)
        self.comment_area.document().contentsChanged.connect(self.adjust_comment_area_size)
        self.main_layout.addWidget(self.comment_area)

        # Connect the anchorClicked signal to handle user mentions
        self.comment_area.anchorClicked.connect(self.handle_user_mentions)

        # Add attached images if present
        if self.attached_image_paths:
            self.images_widget = QtWidgets.QWidget(self)
            self.images_layout = QtWidgets.QGridLayout(self.images_widget)
            self.images_layout.setContentsMargins(10, 10, 10, 10)
            self.images_layout.setSpacing(5)
            self.main_layout.addWidget(self.images_widget)
            self.update_images(self.attached_image_paths)

        # Adjust card size based on content
        self.adjust_card_size()

        # Set style for the card
        self.setStyleSheet(f"""
            FloatingCard {{
                background-color: {SECONDARY_COLOR};
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
            }}
        """)

    def update_images(self, image_paths):
        """Update the images displayed on the card."""
        max_display_images = 4  # Maximum number of images to display
        num_images = len(image_paths)
        images_to_display = image_paths[:max_display_images]

        row = 0
        col = 0
        max_columns = 2  # Number of columns in the grid
        for idx, image_path in enumerate(images_to_display):
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                # Create a label for each image
                image_label = QtWidgets.QLabel(self)
                image_label.setAlignment(QtCore.Qt.AlignCenter)
                # Make images clickable
                image_label.mousePressEvent = lambda event, path=image_path: self.open_image(path)

                # Scale the image to fit within the grid cell
                cell_width = (self.fixed_width - 30) / max_columns  # Adjust for margins and spacing
                scaled_pixmap = pixmap.scaled(
                    cell_width,
                    cell_width,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
                image_label.setPixmap(scaled_pixmap)
                self.images_layout.addWidget(image_label, row, col)

                col += 1
                if col >= max_columns:
                    col = 0
                    row += 1

        # If there are more images than the max to display, add an overlay
        if num_images > max_display_images:
            overlay_label = QtWidgets.QLabel(f"+{num_images - max_display_images} more", self)
            overlay_label.setAlignment(QtCore.Qt.AlignCenter)
            overlay_label.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.6);
                color: white;
                font-size: 18px;
            """)
            # Position the overlay on the last image
            self.images_layout.addWidget(overlay_label, row, col - 1)

        self.adjust_card_size()

    def open_image(self, image_path):
        """Open the image in a new window or perform any desired action."""
        # For simplicity, we'll just show a message box
        QtWidgets.QMessageBox.information(self, "Image Clicked", f"You clicked on {image_path}")

    def adjust_card_size(self):
        """Adjust the card size based on its content."""
        # Calculate the height of the text area based on the content
        document_height = self.comment_area.document().size().height()

        # Calculate additional height for images
        images_height = 0
        if self.attached_image_paths and hasattr(self, 'images_layout'):
            rows = (min(len(self.attached_image_paths), 4) + 1) // 2
            cell_width = (self.fixed_width - 30) / 2
            images_height = rows * cell_width + (rows - 1) * self.images_layout.spacing() + 20  # Adjust for padding

        # Calculate the total height required for the card
        total_height = 40 + int(document_height) + images_height + 20  # Add additional margins and header height
        self.setMinimumHeight(total_height)

    def adjust_comment_area_size(self):
        """Adjust the height of the comment area based on its content."""
        document_height = self.comment_area.document().size().height()
        self.comment_area.setFixedHeight(int(document_height) + 20)
        self.adjust_card_size()

    def handle_user_mentions(self, url):
        """Handle clicks on user mentions."""
        user = url.toString().lstrip("user:")
        QtWidgets.QMessageBox.information(self, "User Mention", f"You clicked on @{user}")

# Colors (Replace with your theme colors)
PRIMARY_COLOR = "#3498db"
SECONDARY_COLOR = "#ffffff"
TEXT_COLOR = "#2c3e50"

# Main application
def main():
    app = QtWidgets.QApplication([])

    # Create the floating card widget
    card_content = "This is a test content with a user mention @user123. Feel free to add comments or feedback."
    card_image_paths = [
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/panosunset2.jpg",
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/panosunset2.jpg",
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/a.jpg",
        "C:/Users/promm/Downloads/a.jpg",
    ]
    
    floating_card = FloatingCard(
        content=card_content, 
        attached_image_paths=card_image_paths
    )
    
    # Create a main window to display the floating card
    main_window = QtWidgets.QMainWindow()
    main_window.setCentralWidget(floating_card)
    main_window.resize(600, 400)
    main_window.show()

    # Execute the application
    app.exec()

if __name__ == "__main__":
    main()
