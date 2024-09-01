# Type Checking Imports
# ---------------------
from typing import Any, Dict, Optional, List

# Standard Library Imports
# ------------------------
import os

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard.utils.application_utils import ApplicationUtil
from blackboard import widgets


# Class Definitions
# -----------------
class AssetViewWidget(widgets.DataViewWidget):

    LABEL = 'Asset View'
    FILE_PATH_COLUMN_NAME = 'file_path'

    def __init__(self, parent: QtWidgets.QWidget = None, identifier: Optional[str] = None):
        super().__init__(parent, identifier)

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.__init_context_menu()

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.drag_started.connect(self._drag_data)

        # Key Binds
        # ---------
        # Create a shortcut for the copy action and connect its activated signal
        bb.utils.KeyBinder.bind_key("Ctrl+Shift+C", self.tree_widget, self.copy_path)

    def __init_context_menu(self):
        self.menu = widgets.ContextMenu()
        self.menu.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        open_section = self.menu.addSection('Open')
        open_action = open_section.addAction("Open")
        open_with_action = open_section.addAction("Open with...")
        open_containing_folder_action = open_section.addAction("Open Containing Folder")
        open_in_terminal_action = open_section.addAction("Open in Terminal")
        copy_section = self.menu.addSection('Copy')
        copy_selected_cell_action = copy_section.addAction("Copy Cell")
        copy_selected_cell_action.setShortcut("Ctrl+C")
        copy_section.addSeparator()
        copy_path_action = copy_section.addAction("Copy Path")
        copy_path_action.setShortcut("Ctrl+Shift+C")
        copy_relative_path_action = copy_section.addAction("Copy Relative Path")
        copy_relative_path_action.setToolTip("This feature is not supported yet.")
        copy_relative_path_action.setEnabled(False)

        open_action.triggered.connect(self.open)
        open_with_action.triggered.connect(self.open_with)
        open_containing_folder_action.triggered.connect(self.open_containing_folder)
        open_in_terminal_action.triggered.connect(self.open_in_terminal)
        copy_path_action.triggered.connect(self.copy_path)
        copy_relative_path_action.triggered.connect(self.copy_relative_path)
        copy_selected_cell_action.triggered.connect(self.tree_widget.copy_selected_cells)

    # Public Methods
    # --------------
    def show_context_menu(self, _position: QtCore.QPoint = None):
        self.menu.exec_(QtGui.QCursor.pos())

    def get_selected_file_paths(self) -> List[str]:
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return

        column_index = self.tree_widget.get_column_index(self.FILE_PATH_COLUMN_NAME)
        if not column_index:
            return

        selected_file_paths = [item.text(column_index) for item in selected_items]

        return selected_file_paths

    @property
    def selected_file_paths(self) -> List[str]:
        return self.get_selected_file_paths()

    def open(self, file_paths: List[str] = []):
        file_paths = file_paths or self.selected_file_paths
        if not file_paths:
            return
        
        for file_path in file_paths:
            ApplicationUtil.open_file(file_path)

    def open_with(self, file_paths: List[str] = []):
        file_paths = file_paths or self.selected_file_paths
        if not file_paths:
            return

        file_path = file_paths[0]
        dialog = widgets.AppSelectionDialog(file_path)
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted and dialog.selected_application:
            try:
                ApplicationUtil.open_file_with_application(file_path, dialog.selected_application)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to launch application: {str(e)}")

    def open_containing_folder(self, file_paths: List[str] = []):
        file_paths = file_paths or self.selected_file_paths
        if not file_paths:
            return

        folders = {os.path.dirname(file_path) if os.path.isfile(file_path) else file_path for file_path in file_paths}
        for folder in folders:
            ApplicationUtil.open_containing_folder(folder)

    def open_in_terminal(self, file_paths: List[str] = []):
        file_paths = file_paths or self.selected_file_paths
        if not file_paths:
            return

        ApplicationUtil.open_directory_in_terminal(file_paths)

    def copy_path(self, file_paths: List[str] = []):
        file_paths = file_paths or self.selected_file_paths
        if not file_paths:
            return
        
        full_text = "\n".join(file_paths)

        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(full_text)

        # Show tooltip message
        self.tree_widget.show_tool_tip(f'Copied:\n{full_text}', 5000)

    def copy_relative_path(self, file_paths: List[str] = []):
        file_paths = file_paths or self.selected_file_paths
        if not file_paths:
            return

        base_path = os.getcwd()
        relative_paths = [os.path.relpath(file_path, base_path) for file_path in file_paths]
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText("\n".join(relative_paths))

    # Private Methods
    # ---------------
    def _drag_data(self, supported_actions: QtCore.Qt.DropActions):
        """Handle drag event of the tree widget.

        Args:
            supported_actions (QtCore.Qt.DropActions): The supported actions for the drag event.
        """
        items = self.tree_widget.selectedItems()

        if not items:
            return
        
        mime_data = QtCore.QMimeData()

        # Set mime data in format 'text/plain'
        texts = bb.utils.TreeUtil.get_column_values(items, self.tree_widget.get_column_index(self.FILE_PATH_COLUMN_NAME))
        text = '\n'.join(texts)
        mime_data.setText(text)

        # Set mime data in format 'text/uri-list'
        urls = [QtCore.QUrl.fromLocalFile(text) for text in texts]
        mime_data.setUrls(urls)

        # Create drag icon pixmap with badge
        drag_pixmap = widgets.DragPixmap(len(items))

        # Set up the drag operation with the semi-transparent pixmap
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(drag_pixmap)
        drag.exec_(supported_actions)


# Main Function
# -------------
def main():
    """Create the application and main window, and show the widget.
    """
    import sys
    from blackboard.utils.file_path_utils import FilePatternQuery

    # Create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    # Set theme of QApplication to the dark theme
    bb.theme.set_theme(app, 'dark')

    # Mock up data
    pattern = "/home/prom/Downloads/"
    work_file_query = FilePatternQuery(pattern)
    filters = {
        'project_name': ['ProjectA'],
        'shot_name': ['shot01', 'shot02'],
    }
    generator = work_file_query.query_files()

    # Create an instance of the widget
    database_view_widget = AssetViewWidget()
    database_view_widget.tree_widget.setHeaderLabels(['id'] + work_file_query.fields)
    database_view_widget.search_edit.skip_columns.add(database_view_widget.tree_widget.get_column_index('id'))
    database_view_widget.tree_widget.create_thumbnail_column('file_path')
    database_view_widget.tree_widget.set_generator(generator)

    # Date Filter Setup
    date_filter_widget = widgets.DateRangeFilterWidget(filter_name="Date")
    date_filter_widget.activated.connect(print)
    # Shot Filter Setup
    shot_filter_widget = widgets.MultiSelectFilterWidget(filter_name="Shot")
    sequence_to_shots = {
        "100": [
            "100_010_001", 
            "100_020_050",
        ],
        "101": [
            "101_022_232", 
            "101_023_200",
        ],
    }
    shot_filter_widget.add_items(sequence_to_shots)
    shot_filter_widget.activated.connect(print)

    # File Type Filter Setup
    file_type_filter_widget = widgets.FileTypeFilterWidget(filter_name="File Type")
    file_type_filter_widget.activated.connect(print)

    show_hidden_filter_widget = widgets.BooleanFilterWidget(filter_name='Show Hidden')
    show_hidden_filter_widget.activated.connect(print)

    # Filter bar
    database_view_widget.add_filter_widget(date_filter_widget)
    database_view_widget.add_filter_widget(shot_filter_widget)
    database_view_widget.add_filter_widget(file_type_filter_widget)
    database_view_widget.add_filter_widget(show_hidden_filter_widget)

    # Create the scalable view and set the tree widget as its central widget
    scalable_view = widgets.ScalableView(widget=database_view_widget)

    # Show the widget
    scalable_view.show()

    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()