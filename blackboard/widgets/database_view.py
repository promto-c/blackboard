# Type Checking Imports
# ---------------------
from typing import Any, Union, Callable, Dict, Iterable

# Standard Library Imports
# ------------------------
import sys

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.widgets.filter_widget import (
    FilterBarWidget, FilterWidget,
    DateRangeFilterWidget,
    MultiSelectFilterWidget,
    FileTypeFilterWidget,
    BooleanFilterWidget
)
from blackboard.widgets.simple_search_widget import SimpleSearchEdit
from blackboard.widgets.groupable_tree_widget import GroupableTreeWidget, TreeUtilityToolBar
from blackboard.widgets.scalable_view import ScalableView
from blackboard.theme import set_theme

# NOTE: Workaround
# ----------------
class CustomShortcut(QtWidgets.QShortcut):
    def __init__(self, key_sequence, parent_widget, callback, target_widget=None):
        super().__init__(QtGui.QKeySequence(key_sequence), parent_widget)
        self.target_widget = target_widget or parent_widget
        self.callback = callback
        self.activated.connect(self.check_focus_and_activate)

    def check_focus_and_activate(self):
        focused_widget = QtWidgets.QApplication.instance().focus_widget

        if focused_widget == self.target_widget:
            self.callback()
# ----------------

class DatabaseViewWidget(QtWidgets.QWidget):
    """
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: QtWidgets.QWidget = None):
        """Initialize the widget and set up the UI, signal connections.
        """
        # Initialize the super class
        super().__init__(parent)

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
            | - - - - - - - - - - - |[W4]: tree_utility_tool_bar|  |
            |                                                   |  |
            |                                                   |  |
            |               [[W3]: tree_widget]                 |  | -> [L2]: main_tree_layout
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

        # [L2]: Add main tree layout
        self.main_tree_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.main_tree_layout)
        self.main_layout.setSpacing(0)
        self.main_tree_layout.setSpacing(0)

        # Create Widgets
        # --------------
        # [W1]: Create top left filter bar
        self.filter_bar_widget = FilterBarWidget(self)

        # [W3]: Create asset tree widget
        self.tree_widget = GroupableTreeWidget(parent=self)
        self.tree_utility_tool_bar = TreeUtilityToolBar(self.tree_widget)

        # [W2]: Search field
        self.search_edit = SimpleSearchEdit(tree_widget=self.tree_widget, parent=self)
        self.search_edit.setMinimumWidth(200)

        # Add Widgets to Layouts
        # ----------------------
        # Add [W1], [W2] to [L1]
        # Add left filter bar and right search edit to top bar layout
        self.top_bar_area_layout.addWidget(self.filter_bar_widget)
        self.top_bar_area_layout.addStretch()
        self.top_bar_area_layout.addWidget(self.search_edit)

        # Add [W3], [W4] to [L2]
        # Add tree widget to main tree widget
        self.main_tree_layout.addWidget(self.tree_utility_tool_bar)
        self.main_tree_layout.addWidget(self.tree_widget)

    def __init_signal_connections(self):
        """Set up signal connections between widgets and slots.
        """
        # Connect signals to slots
        self.bind_key('Ctrl+F', self.search_edit.set_text_as_selection)

    def bind_key(self, key_sequence: Union[str, QtGui.QKeySequence], function: Callable, 
                 context: QtCore.Qt.ShortcutContext = QtCore.Qt.ShortcutContext.WidgetShortcut):
        """Binds a given key sequence to a function.
        
        Args:
            key_sequence (Union[str, QtGui.QKeySequence]): The key sequence as a string or QKeySequence, e.g., "Ctrl+F".
            function (Callable): The function to be called when the key sequence is activated.
            context (QtCore.Qt.ShortcutContext, optional): The context in which the shortcut is active.
        """
        # Create a shortcut with the specified key sequence
        # NOTE: Workaround
        # ----------------
        shortcut = CustomShortcut(QtGui.QKeySequence(key_sequence), self.tree_widget, function)
        # NOTE: Use CustomShortcut to handle context widget instead of old becuse when use with ScalableView
        #       ScalableView will handle as qapp.focusWidget
        # shortcut.setContext(context)
        # Connect the activated signal of the shortcut to the given function
        # shortcut.activated.connect(function)

    def add_filter_widget(self, filter_widget: 'FilterWidget'):
        self.filter_bar_widget.add_filter_widget(filter_widget)
        filter_widget.activated.connect(self.activate_filter)

    def save_state(self, settings: QtCore.QSettings, group_name: str = 'database_view'):
        self.tree_widget.save_state(settings, group_name)
    
    def load_state(self, settings: QtCore.QSettings, group_name: str = 'database_view'):
        self.tree_widget.load_state(settings, group_name)

    def activate_filter(self):
        # Logic to filter data then populate
        ...

    def populate(self, id_to_data_dict: Dict[Iterable, Dict[str, Any]]):
        # Clear old items
        self.tree_widget.clear()

        # Add items to tree
        self.tree_widget.add_items(id_to_data_dict)

        self.search_edit.update()

# NOTE: Workaround
# ----------------
class FocusEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.FocusIn and not isinstance(obj, QtWidgets.QCommonStyle):
            QtWidgets.QApplication.instance().focus_widget = obj
            # print(self.focus_widget)
            # print(f"{obj} has gained focus.")
        elif event.type() == QtCore.QEvent.Type.FocusOut:
            if QtWidgets.QApplication.instance().focus_widget == obj:
                QtWidgets.QApplication.instance().focus_widget = None
        return super().eventFilter(obj, event)
# ----------------

def main():
    """Create the application and main window, and show the widget.
    """
    # Create the application and the main window
    app = QtWidgets.QApplication(sys.argv)
    # app.focusChanged.connect(lambda old, new: print(f"Focus changed from {old} to {new}"))

    # NOTE: Workaround
    # ----------------
    # NOTE: Use FocusEventFilter to handle focused_widget instead of original focusWidget()
    #       because it will get only ScalableView that wrapped all inside widgets
    focus_event_filter = FocusEventFilter()
    app.focus_widget = None
    app.installEventFilter(focus_event_filter)
    # ----------------


    # Set theme of QApplication to the dark theme
    set_theme(app, 'dark')

    from blackboard.examples.example_data_dict import COLUMN_NAME_LIST, ID_TO_DATA_DICT

    # Create an instance of the widget
    database_view_widget = DatabaseViewWidget()
    database_view_widget.tree_widget.set_column_name_list(COLUMN_NAME_LIST)
    database_view_widget.populate(ID_TO_DATA_DICT)

    # Date Filter Setup
    date_filter_widget = DateRangeFilterWidget(filter_name="Date")
    date_filter_widget.activated.connect(print)
    # Shot Filter Setup
    shot_filter_widget = MultiSelectFilterWidget(filter_name="Shot")
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
    file_type_filter_widget = FileTypeFilterWidget(filter_name="File Type")
    file_type_filter_widget.activated.connect(print)

    show_hidden_filter_widget = BooleanFilterWidget(filter_name='Show Hidden')
    show_hidden_filter_widget.activated.connect(print)

    # Filter bar
    database_view_widget.add_filter_widget(date_filter_widget)
    database_view_widget.add_filter_widget(shot_filter_widget)
    database_view_widget.add_filter_widget(file_type_filter_widget)
    database_view_widget.add_filter_widget(show_hidden_filter_widget)

    # Create the scalable view and set the tree widget as its central widget
    scalable_view = ScalableView(widget=database_view_widget)

    # database_view_widget.setFocusProxy(scalable_view)

    # Show the widget
    scalable_view.show()

    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()