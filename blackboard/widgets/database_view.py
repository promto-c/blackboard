# Type Checking Imports
# ---------------------
from typing import Any, Dict, Iterable, Optional

# Standard Library Imports
# ------------------------
import uuid

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
import blackboard as bb
from blackboard import widgets


# Class Definitions
# -----------------
class DatabaseViewWidget(QtWidgets.QWidget):
    """
    """
    LABEL: str = 'Database View'

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None, identifier: Optional[str] = None):
        """Initialize the widget and set up the UI, signal connections.
        """
        # Initialize the super class
        super().__init__(parent)

        # Generate a unique identifier if none is provided
        self.identifier = identifier or str(uuid.uuid4())

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Set up the UI for the widget, including creating widgets, layouts.

        UI Wireframe:

            |--[W1]: filter_bar_widget--|

            +---------------------------------------------------+ -+
            | [Filter 1][Filter 2][+]       [[W2]: search_edit] |  | -> [L1]: top_bar_area_layout
            +---------------------------------------------------+ -+
            | [W3]: general_tool_bar| - - | [W4]: view_tool_bar |  | -> [L2]: utility_area_layout
            |                                                   |  |
            |                                                   |  |
            |               [[W5]: tree_widget]                 |  | -> [L3]: main_view_layout
            |                                                   |  |
            |                                                   |  |
            +---------------------------------------------------+ -+
        """
        # Create Layouts
        # --------------
        # [L0]: Set main layout as vertical layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # [L1]: Add top bar layout as horizontal layout
        self.top_bar_area_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.top_bar_area_layout)

        # [L2]: Add utility layout
        self.utility_area_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.utility_area_layout)

        # [L3]: Add main tree layout
        self.main_view_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.main_view_layout)
        self.main_layout.setSpacing(0)
        self.main_view_layout.setSpacing(0)

        # Create Widgets
        # --------------
        # [W1]: Create top left filter bar
        self.filter_bar_widget = widgets.FilterBarWidget(self)

        # [W5]: Create asset tree widget
        self.tree_widget = widgets.GroupableTreeWidget(parent=self)

        # [W2]: Search field
        self.search_edit = widgets.SimpleSearchEdit(tree_widget=self.tree_widget, parent=self)
        self.search_edit.setMinimumWidth(200)

        # [W3], [W4]: General tool bar and view utility bar
        self.general_tool_bar = QtWidgets.QToolBar(self)
        self.view_tool_bar = widgets.TreeUtilityToolBar(self.tree_widget)

        # Add Widgets to Layouts
        # ----------------------
        # Add [W1], [W2] to [L1]
        # Add left filter bar and right search edit to top bar layout
        self.top_bar_area_layout.addWidget(self.filter_bar_widget)
        self.top_bar_area_layout.addStretch()
        self.top_bar_area_layout.addWidget(self.search_edit)

        # Add [W3], [W4] to [L2]
        # Add left general tool bar and right view tool bar
        self.utility_area_layout.addWidget(self.general_tool_bar)
        self.utility_area_layout.addStretch()
        self.utility_area_layout.addWidget(self.view_tool_bar)

        # Add [W5] to [L3]
        # Add tree widget to main tree widget
        self.main_view_layout.addWidget(self.tree_widget)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.view_tool_bar.refresh_button.clicked.connect(self.activate_filter)
        bb.utils.KeyBinder.bind_key('Ctrl+F', self.tree_widget, self.search_edit.set_text_as_selection)

    # Public Methods
    # --------------
    def add_filter_widget(self, filter_widget: 'widgets.FilterWidget'):
        self.filter_bar_widget.add_filter_widget(filter_widget)
        filter_widget.activated.connect(self.activate_filter)

    def save_state(self, settings: QtCore.QSettings, group_name: str = 'database_view'):
        self.tree_widget.save_state(settings, group_name)
    
    def load_state(self, settings: QtCore.QSettings, group_name: str = 'database_view'):
        self.tree_widget.load_state(settings, group_name)

    def activate_filter(self):
        # Logic to filter data then populate
        ...
        # Example Implementation:
        # ---
        # id_to_data_dict = ...
        # self.populate(id_to_data_dict)

        raise NotImplementedError(f"{self.__class__.__name__}.activate_filter must be implemented by subclasses.")

    def populate(self, id_to_data_dict: Dict[Iterable, Dict[str, Any]]):
        # Clear old items
        self.tree_widget.clear()

        # Add items to tree
        self.tree_widget.add_items(id_to_data_dict)

        self.search_edit.update()

    # Special Methods
    # ---------------
    def __hash__(self):
        return hash(self.identifier)


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
    pattern = "blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/{asset_type}"
    work_file_query = FilePatternQuery(pattern)
    filters = {
        'project_name': ['ProjectA'],
        'shot_name': ['shot01', 'shot02'],
    }
    generator = work_file_query.query_files(filters)

    # Create an instance of the widget
    database_view_widget = DatabaseViewWidget()
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
