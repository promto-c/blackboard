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

    WINDOW_TITLE = 'Select Application'

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        layout = QtWidgets.QVBoxLayout(self)
        self.app_list_widget = QtWidgets.QListWidget(self)
        layout.addWidget(self.app_list_widget)
        self.selected_application = None

        applications = self.get_applications_for_mime_type(file_path)
        if not applications:
            self.app_list_widget.addItem(QtWidgets.QListWidgetItem("No applications found"))
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

        self.app_list_widget.itemDoubleClicked.connect(self.item_double_clicked)

    def item_double_clicked(self, item):
        self.selected_application = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    def get_applications_for_mime_type(self, file_path: str) -> List[str]:
        try:
            mime_type = ApplicationUtil.get_mime_type(file_path)
            applications = ApplicationUtil.get_associated_apps(mime_type, section=ApplicationSection.REGISTERED)
            return applications
        except subprocess.CalledProcessError:
            return []
