from typing import Tuple, Optional, List, Dict, Union

import subprocess
import re
import os
import sys
import configparser

from PyQt5 import QtCore, QtGui, QtWidgets

from enum import Enum

class ApplicationSection(Enum):
    DEFAULT = 'default'
    REGISTERED = 'registered'
    RECOMMENDED = 'recommended'

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
    def get_associated_apps(mime_type: str, section: Union[ApplicationSection, str] = ApplicationSection.DEFAULT) -> List[str]:
        """List applications associated with a given MIME type.
        
        Args:
            mime_type (str): The MIME type to search for associated applications.
            section (Union[ApplicationSection, str]): The section of applications to return ('default', 'registered', 'recommended').
            
        Returns:
            List[str]: A list of paths to the .desktop files of the specified section.
        """
        if isinstance(section, str):
            try:
                section = ApplicationSection(section.lower())
            except ValueError:
                raise ValueError(f"Invalid section '{section}'. Choose from 'default', 'registered', 'recommended'.")
        
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

        if section.value not in parsed_data:
            raise ValueError(f"Invalid section '{section.value}'. Choose from 'default', 'registered', 'recommended'.")

        return parsed_data[section.value]

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
            applications = ApplicationUtils.get_associated_apps(mime_type, section=ApplicationSection.REGISTERED)
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
            index = indexes[0]
            menu = QtWidgets.QMenu()
            
            if QtCore.QFileInfo(self.model().filePath(index)).isFile():
                open_action = QtWidgets.QAction('Open', self)
                open_with_action = QtWidgets.QAction('Open with...', self)
                open_containing_folder_action = QtWidgets.QAction('Open Containing Folder', self)
                open_in_terminal_action = QtWidgets.QAction('Open in Terminal', self)
                copy_file_path_action = QtWidgets.QAction('Copy Path', self)
                copy_relative_path_action = QtWidgets.QAction('Copy Relative Path', self)

                open_action.triggered.connect(lambda: self.open_file(index))
                open_with_action.triggered.connect(lambda: self.open_file_with(indexes[0]))
                open_containing_folder_action.triggered.connect(lambda: self.open_containing_folder(index))
                open_in_terminal_action.triggered.connect(lambda: self.open_in_terminal(index))
                copy_file_path_action.triggered.connect(lambda: self.copy_file_path(index))
                copy_relative_path_action.triggered.connect(lambda: self.copy_relative_path(index))

                menu.addAction(open_action)
                menu.addAction(open_with_action)
                menu.addAction(open_containing_folder_action)
                menu.addAction(open_in_terminal_action)
                menu.addAction(copy_file_path_action)
                menu.addAction(copy_relative_path_action)
            else:
                new_file_action = QtWidgets.QAction('New File', self)
                new_folder_action = QtWidgets.QAction('New Folder', self)
                
                new_file_action.triggered.connect(lambda: self.new_file(index))
                new_folder_action.triggered.connect(lambda: self.new_folder(index))

                menu.addAction(new_file_action)
                menu.addAction(new_folder_action)

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

    def open_containing_folder(self, index):
        file_path = self.model().filePath(index)
        folder_path = os.path.dirname(file_path)
        subprocess.run(['xdg-open', folder_path])

    def open_in_terminal(self, index):
        file_path = self.model().filePath(index)
        folder_path = os.path.dirname(file_path)
        terminal_command = os.getenv('TERMINAL', 'gnome-terminal')
        subprocess.run([terminal_command, '--working-directory', folder_path])

    def copy_file_path(self, index):
        file_path = self.model().filePath(index)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(file_path)

    def copy_relative_path(self, index):
        file_path = self.model().filePath(index)
        relative_path = os.path.relpath(file_path, start=os.path.expanduser("~"))
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(relative_path)

    def rename_file(self, index):
        file_path = self.model().filePath(index)
        new_name, ok = QtWidgets.QInputDialog.getText(self, 'Rename File', 'New Name:')
        if ok:
            new_path = os.path.join(os.path.dirname(file_path), new_name)
            os.rename(file_path, new_path)
            self.model().setRootPath('')
            self.model().setRootPath('/')

    def delete_file(self, index):
        file_path = self.model().filePath(index)
        os.remove(file_path)
        self.model().remove(index)

    def duplicate_file(self, index):
        file_path = self.model().filePath(index)
        new_path = file_path + '_copy'
        with open(file_path, 'rb') as fsrc, open(new_path, 'wb') as fdst:
            fdst.write(fsrc.read())
        self.model().setRootPath('')
        self.model().setRootPath('/')

    def move_to_trash(self, index):
        file_path = self.model().filePath(index)
        trash_path = os.path.join(os.path.expanduser('~/.local/share/Trash/files/'), os.path.basename(file_path))
        os.rename(file_path, trash_path)
        self.model().remove(index)

    def show_properties(self, index):
        file_path = self.model().filePath(index)
        file_info = QtCore.QFileInfo(file_path)
        details = f"File: {file_info.fileName()}\nSize: {file_info.size()} bytes\nType: {file_info.suffix()}\nModified: {file_info.lastModified().toString()}"
        QtWidgets.QMessageBox.information(self, 'Properties', details)

    def new_file(self, index):
        directory = self.model().filePath(index)
        new_file_path, ok = QtWidgets.QInputDialog.getText(self, 'New File', 'File Name:')
        if ok:
            open(os.path.join(directory, new_file_path), 'a').close()
            self.model().setRootPath('')
            self.model().setRootPath('/')

    def new_folder(self, index):
        directory = self.model().filePath(index)
        new_folder_path, ok = QtWidgets.QInputDialog.getText(self, 'New Folder', 'Folder Name:')
        if ok:
            os.makedirs(os.path.join(directory, new_folder_path))
            self.model().setRootPath('')
            self.model().setRootPath('/')

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
