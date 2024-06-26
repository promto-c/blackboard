# Type Checking Imports
# ---------------------
from typing import List

# Standard Library Imports
# ------------------------
import subprocess

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets

# Local Imports
# -------------
from blackboard.utils.application_utils import ApplicationUtil, ApplicationSection


# Class Definitions
# -----------------
class AppSelectionDialog(QtWidgets.QDialog):
    """Dialog for selecting an application based on the file's MIME type.
    """

    WINDOW_TITLE = 'Select Application'

    # Initialization and Setup
    # ------------------------
    def __init__(self, file_path: str, parent: QtWidgets.QWidget = None):
        """Initialize the dialog with a list of applications associated with the file's MIME type.

        Args:
            file_path: The path of the file to check for associated applications.
            parent: The parent widget, if any.
        """
        super().__init__(parent)

        # Store the arguments
        self.file_path = file_path

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.selected_application = None

    def __init_ui(self):
        """Initialize the UI of the dialog.
        """
        self.setWindowTitle(self.WINDOW_TITLE)
        
        # Set the layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create and add the list widget
        self.app_list_widget = QtWidgets.QListWidget(self)
        layout.addWidget(self.app_list_widget)

        # Get applications associated with the file's MIME type
        applications = self._get_applications_for_mime_type(self.file_path)
        if not applications:
            self.app_list_widget.addItem(QtWidgets.QListWidgetItem("No applications found"))
        
        # Populate the list widget with application names and icons
        for desktop_file in applications:
            name, icon_path = ApplicationUtil.parse_desktop_file(desktop_file)
            if not name:
                continue
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, desktop_file)  # Embed the desktop file path
            if icon_path:
                icon = QtGui.QIcon.fromTheme(icon_path)
                if not icon.isNull():
                    item.setIcon(icon)
            self.app_list_widget.addItem(item)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.app_list_widget.itemDoubleClicked.connect(self._accept_selection)

    # Private Methods
    # ---------------
    def _accept_selection(self, item: QtWidgets.QListWidgetItem):
        """Handle the item double-click event and accept the selection.

        Args:
            item: The item that was double-clicked.
        """
        self.selected_application = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    def _get_applications_for_mime_type(self, file_path: str) -> List[str]:
        """Retrieve a list of applications associated with the file's MIME type.

        Args:
            file_path: The path of the file to check for associated applications.

        Returns:
            A list of desktop file paths for the associated applications.
        """
        try:
            mime_type = ApplicationUtil.get_mime_type(file_path)
            applications = ApplicationUtil.get_associated_apps(mime_type, section=ApplicationSection.REGISTERED)
            return applications
        except subprocess.CalledProcessError:
            return []
