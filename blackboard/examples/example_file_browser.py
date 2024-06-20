# Type Checking Imports
# ---------------------
from typing import Tuple, Optional, List, Dict, Union

# Standard Library Imports
# ------------------------
import subprocess
import re
import os
import sys
import configparser
from enum import Enum

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets

# Local Imports
# -------------
from blackboard.utils.application_utils import ApplicationUtils, ApplicationSection


# Class Definitions
# -----------------
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
        if not indexes:
            return

        index = indexes[0]
        menu = QtWidgets.QMenu()
        
        if QtCore.QFileInfo(self.model().filePath(index)).isFile():
            open_action = QtWidgets.QAction('Open', self)
            open_with_action = QtWidgets.QAction('Open with...', self)
            open_containing_folder_action = QtWidgets.QAction('Open Containing Folder', self)
            open_in_terminal_action = QtWidgets.QAction('Open in Terminal', self)
            copy_path_action = QtWidgets.QAction('Copy Path', self)
            copy_relative_path_action = QtWidgets.QAction('Copy Relative Path', self)

            open_action.triggered.connect(lambda: self.open_file(index))
            open_with_action.triggered.connect(lambda: self.open_file_with(indexes[0]))
            open_containing_folder_action.triggered.connect(lambda: self.open_containing_folder(index))
            open_in_terminal_action.triggered.connect(lambda: self.open_in_terminal(index))
            copy_path_action.triggered.connect(lambda: self.copy_file_path(index))
            copy_relative_path_action.triggered.connect(lambda: self.copy_relative_path(index))

            menu.addAction(open_action)
            menu.addAction(open_with_action)
            menu.addAction(open_containing_folder_action)
            menu.addAction(open_in_terminal_action)
            menu.addAction(copy_path_action)
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

        self.show_properties(index)

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
        print(file_info.owner())
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
