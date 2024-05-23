from typing import Tuple, Optional, List, Dict

import subprocess
import re
import os
import sys
import configparser

from PyQt5 import QtCore, QtGui, QtWidgets

class ApplicationUtils:
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """Use the file command to get the MIME type of the file."""
        mime_type = subprocess.check_output(['file', '--mime-type', '-b', file_path]).decode().strip()
        return mime_type

    @staticmethod
    def parse_gio_mime_output(output: str) -> Dict[str, List[str]]:
        """Parse the output of the 'gio mime' command to extract application information.
        
        Args:
            output (str): The output string from the 'gio mime' command.
            
        Returns:
            Dict[str, List[str]]: A dictionary with default, registered, and recommended applications.
        """
        data = {}

        default_app_pattern = re.compile(r'Default application for “.+?”: (.+)')
        registered_apps_pattern = re.compile(r'Registered applications:\n((?:\s+.+\.desktop\n)+)')
        recommended_apps_pattern = re.compile(r'Recommended applications:\n((?:\s+.+\.desktop\n)+)')

        default_app_match = default_app_pattern.search(output)
        registered_apps_match = registered_apps_pattern.search(output)
        recommended_apps_match = recommended_apps_pattern.search(output)

        data['default'] = default_app_match.group(1).strip() if default_app_match else None

        if registered_apps_match:
            registered_apps = registered_apps_match.group(1).strip().split('\n')
            data['registered'] = [app.strip() for app in registered_apps]
        else:
            data['registered'] = []

        if recommended_apps_match:
            recommended_apps = recommended_apps_match.group(1).strip().split('\n')
            data['recommended'] = [app.strip() for app in recommended_apps]
        else:
            data['recommended'] = []

        return data

    @staticmethod
    def get_associated_apps(mime_type: str, section: str = 'registered') -> List[str]:
        """List applications associated with a given MIME type.
        
        Args:
            mime_type (str): The MIME type to search for associated applications.
            section (str): The section of applications to return ('default', 'registered', 'recommended').
            
        Returns:
            List[str]: A list of paths to the .desktop files of the specified section.
        """
        result = subprocess.check_output(['gio', 'mime', mime_type]).decode().strip()
        parsed_data = ApplicationUtils.parse_gio_mime_output(result)

        if parsed_data['default']:
            parsed_data['default'] = ApplicationUtils.find_desktop_file(parsed_data['default'])

        parsed_data['registered'] = [
            ApplicationUtils.find_desktop_file(app) for app in parsed_data['registered'] if ApplicationUtils.find_desktop_file(app) is not None
        ]

        parsed_data['recommended'] = [
            ApplicationUtils.find_desktop_file(app) for app in parsed_data['recommended'] if ApplicationUtils.find_desktop_file(app) is not None
        ]

        if section not in parsed_data:
            raise ValueError(f"Invalid section '{section}'. Choose from 'default', 'registered', 'recommended'.")

        return parsed_data[section]

    @staticmethod
    def parse_desktop_file(desktop_file: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse the .desktop file to extract the application name and icon path.
        
        Args:
            desktop_file (str): Path to the .desktop file.
            
        Returns:
            Tuple[Optional[str], Optional[str]]: The application name and icon path, or None if not found.
        """
        config = configparser.ConfigParser()
        config.read(desktop_file)

        name = config.get('Desktop Entry', 'Name', fallback=None)
        icon = config.get('Desktop Entry', 'Icon', fallback=None)

        return name, icon

    @staticmethod
    def find_desktop_file(app_name: str) -> Optional[str]:
        """Find the full path of the .desktop file for the specified application."""
        search_paths = ['/usr/share/applications/', os.path.expanduser('~/.local/share/applications/')]
        for path in search_paths:
            desktop_file = os.path.join(path, app_name)
            if os.path.isfile(desktop_file):
                return desktop_file
        return None

    @staticmethod
    def open_file_with_application(file_path: str, desktop_file: str):
        """Command to open the file with the specified application."""
        if desktop_file:
            subprocess.run(['gio', 'launch', desktop_file, file_path])
        else:
            print("No .desktop file found for the selected application.")

class AppSelectionDialog(QtWidgets.QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select Application')
        layout = QtWidgets.QVBoxLayout(self)
        self.listWidget = QtWidgets.QListWidget()
        layout.addWidget(self.listWidget)
        self.selected_application = None

        applications = self.get_applications_for_mime_type(file_path)
        if not applications:
            self.listWidget.addItem(QtWidgets.QListWidgetItem("No applications found"))
        for desktop_file in applications:
            name, icon_path = ApplicationUtils.parse_desktop_file(desktop_file)
            if not name:
                continue
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, desktop_file)  # Embed the desktop file path
            if icon_path:
                icon = QtGui.QIcon.fromTheme(icon_path)
                if not icon.isNull():
                    item.setIcon(icon)
            self.listWidget.addItem(item)

        self.listWidget.itemDoubleClicked.connect(self.item_double_clicked)

    def item_double_clicked(self, item):
        self.selected_application = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    def get_applications_for_mime_type(self, file_path: str) -> List[str]:
        try:
            mime_type = ApplicationUtils.get_mime_type(file_path)
            applications = ApplicationUtils.get_associated_apps(mime_type)
            return applications
        except subprocess.CalledProcessError:
            return []

class CustomTreeView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super(CustomTreeView, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)

        self.doubleClicked.connect(self.open_file_on_double_click)

    def open_menu(self, position):
        indexes = self.selectedIndexes()
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            while index.parent().isValid():
                index = index.parent()
                level += 1

            menu = QtWidgets.QMenu()
            if QtCore.QFileInfo(self.model().filePath(indexes[0])).isFile():
                open_action = QtWidgets.QAction('Open', self)
                open_with_action = QtWidgets.QAction('Open with...', self)
                menu.addAction(open_action)
                menu.addAction(open_with_action)
                open_action.triggered.connect(lambda: self.open_file(indexes[0]))
                open_with_action.triggered.connect(lambda: self.open_file_with(indexes[0]))
                menu.exec_(self.viewport().mapToGlobal(position))

    def open_file(self, index):
        file_path = self.model().filePath(index)
        subprocess.run(['xdg-open', file_path])

    def open_file_with(self, index):
        file_path = self.model().filePath(index)
        dialog = AppSelectionDialog(file_path, self)
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted and dialog.selected_application:
            try:
                ApplicationUtils.open_file_with_application(file_path, dialog.selected_application)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to launch application: {str(e)}")

    def open_file_on_double_click(self, index):
        if QtCore.QFileInfo(self.model().filePath(index)).isFile():
            self.open_file(index)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('File Model Tree View Example')
        self.setGeometry(100, 100, 800, 600)

        self.model = QtWidgets.QFileSystemModel()
        self.model.setRootPath('/')

        self.tree = CustomTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index('./'))

        self.setCentralWidget(self.tree)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
