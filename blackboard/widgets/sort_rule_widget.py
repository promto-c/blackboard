# Type Checking Imports
# ---------------------
from typing import List, Optional, Tuple, Callable, Dict

# Standard Library Imports
# ------------------------
from enum import Enum
from dataclasses import dataclass

# Third-Party Imports
# -------------------
from qtpy import QtCore, QtWidgets
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.utils.list_utils import ListUtil


# Class Definitions
# -----------------
class SortOrder(Enum):
    """Enumeration for sort order.
    """
    ASCENDING = 'ASC'
    DESCENDING = 'DESC'

@dataclass
class SortRule:
    field: str
    order: SortOrder

    @property
    def __dict__(self) -> Dict[str, str]:
        return {
            'field': self.field,
            'order': self.order.name
        }

    def to_dict(self) -> Dict[str, str]:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            field=data['field'],
            order=SortOrder[data['order']]
        )

    def __post_init__(self):
        if not isinstance(self.field, str):
            raise TypeError("field must be a string")
        if not isinstance(self.order, SortOrder):
            raise TypeError("order must be a SortOrder instance")

class SortRuleWidgetItem(QtWidgets.QListWidgetItem):
    """Widget representing a single sort rule.

    UI Wireframe:

        +--------------------------------------+
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        +--------------------------------------+
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, rule_widget: 'SortRuleListWidget', field: str):
        """Initialize a SortRuleWidgetItem.

        Args:
            rule_widget (SortRuleListWidget): The parent SortRuleListWidget.
        """
        super().__init__(rule_widget)

        # Store the arguments
        self.rule_widget = rule_widget
        self._current_field = field

        # Initialize UI and connections
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        self.widget = QtWidgets.QWidget(self.rule_widget)
        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.setContentsMargins(4, 4, 4, 4)

        # Create Widgets
        # --------------
        # Drag handle icon
        self.drag_handle = QtWidgets.QLabel(
            self.widget, maximumWidth=20,
            pixmap=TablerQIcon.grip_vertical.pixmap(20, 20),
            cursor=QtCore.Qt.CursorShape.SizeAllCursor
        )

        # Field Dropdown
        self.field_dropdown = QtWidgets.QComboBox(
            self.widget, toolTip="Select a field to sort by", cursor=QtCore.Qt.CursorShape.PointingHandCursor,
        )

        # Ascending/Descending toggle buttons
        self.asc_button = QtWidgets.QToolButton(
            self.widget, icon=TablerQIcon.sort_ascending_letters, toolTip="Sort in ascending order",
            cursor=QtCore.Qt.CursorShape.PointingHandCursor, checkable=True, checked=True,
        )
        self.desc_button = QtWidgets.QToolButton(
            self.widget, icon=TablerQIcon.sort_descending_letters, toolTip="Sort in descending order",
            cursor=QtCore.Qt.CursorShape.PointingHandCursor, checkable=True,
        )

        # Toggle group behavior
        self.ordering_button_group = QtWidgets.QButtonGroup(self.widget, exclusive=True)
        self.ordering_button_group.addButton(self.asc_button)
        self.ordering_button_group.addButton(self.desc_button)

        # Delete button
        self.delete_button = QtWidgets.QToolButton(
            self.widget, icon=TablerQIcon.trash, toolTip="Delete this sort rule",
            cursor=QtCore.Qt.CursorShape.PointingHandCursor,
        )

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.drag_handle)
        layout.addWidget(self.field_dropdown)
        layout.addWidget(self.asc_button)
        layout.addWidget(self.desc_button)
        layout.addWidget(self.delete_button)

        self.setSizeHint(self.widget.sizeHint())
        self.rule_widget.setItemWidget(self, self.widget)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.field_dropdown.currentTextChanged.connect(self._update_used_field)
        self.delete_button.clicked.connect(lambda: self.rule_widget.remove_rule(self))

    # Public Methods
    # --------------
    def set_available_fields(self, fields: List[str]):
        """Update the field dropdown with unused fields.
        """
        self.field_dropdown.blockSignals(True)
        self.field_dropdown.clear()
        self.field_dropdown.addItems([self._current_field] + fields)
        self.field_dropdown.blockSignals(False)

    def get_rule(self) -> 'SortRule':
        """Return the current sort rule as a SortRule dataclass instance.

        Returns:
            SortRule: An instance containing the field and sort order.
        """
        return SortRule(
            field=self._current_field,
            order=SortOrder.ASCENDING if self.asc_button.isChecked() else SortOrder.DESCENDING,
        )

    # Class Properties
    # ----------------
    @property
    def current_field(self) -> str:
        return self._current_field

    @current_field.setter
    def current_field(self, field: str):
        self.field_dropdown.setCurrentText(field)

    # Private Methods
    # ---------------
    def _update_used_field(self, new_field: str):
        """Handle field selection changes.

        Args:
            new_field (str): The selected field name in the dropdown.
        """
        old_field = self._current_field
        self._current_field = new_field
        # Update the used_fields in rule_widget
        self.rule_widget._update_used_fields(old_field, new_field)

class SortRuleListWidget(QtWidgets.QListWidget):
    """Widget for managing sort rules.

    UI Wireframe:

        +--------------------------------------+
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        +--------------------------------------+
    """

    # Signals
    rule_added = QtCore.Signal()
    rule_removed = QtCore.Signal()
    rules_cleared = QtCore.Signal()

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """Initialize the SortRuleListWidget.

        Args:
            parent (Optional[QtWidgets.QWidget]): The parent widget.
            fields (Optional[List[str]]): The list of available fields for sorting.
        """
        super().__init__(parent, dragDropMode=QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        # Initialize setup
        self.__init_attributes()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._fields: List[str] = []
        self._available_fields: List[str] = []

    # Public Methods
    # --------------
    def get_items(self, is_only_checked: bool = False, filter_func: Optional[Callable[['QtWidgets.QListWidgetItem'], bool]] = None) -> List['SortRuleWidgetItem']:
        return ListUtil.get_items(self, is_only_checked, filter_func)

    def set_fields(self, fields: List[str]):
        """Set the available fields for sorting.

        Args:
            fields (List[str]): The list of fields.
        """
        self._fields = fields
        self.clear_rules()

    def add_rule(self, field: Optional[str] = None):
        """Add a new sort rule.
        """
        if not self._fields:
            return

        if field is None:
            field = self._available_fields.pop(0)
        else:
            self._available_fields.remove(field)

        _rule_item = SortRuleWidgetItem(self, field=field)

        # Update field_dropdowns in other items
        self._set_available_fields()
        self.rule_added.emit()

    def remove_rule(self, rule_item: 'SortRuleWidgetItem'):
        """Remove a sort rule item.

        Args:
            item_widget (SortRuleWidgetItem): The sort rule item to remove.
        """
        # Remove selected field and remove item
        self._available_fields.append(rule_item.current_field)
        self.takeItem(self.row(rule_item))

        # Update field_dropdowns in other items
        self._set_available_fields()
        self.rule_removed.emit()

    def clear_rules(self):
        """Clear all sort rules.
        """
        self.clear()
        self._available_fields = self._fields.copy()
        self.rules_cleared.emit()

    def get_rules(self) -> List['SortRule']:
        """Return the current sorting rules.

        Returns:
            List[Tuple[str, SortOrder]]: A list of tuples containing field names and sort orders.
        """
        return [item.get_rule() for item in self.get_items()]

    # Class Properties
    # ----------------
    @property
    def fields(self) -> List[str]:
        return self._fields

    @fields.setter
    def fields(self, fields: List[str]):
        self.set_fields(fields)

    @property
    def available_fields(self) -> List[str]:
        return self._available_fields

    # Private Methods
    # ---------------
    def _set_available_fields(self):
        """Update field_dropdowns in SortRuleItems.
        """
        for item in self.get_items():
            item.set_available_fields(self._available_fields)

    def _update_used_fields(self, old_field: Optional[str], new_field: str):
        """Handle changes to a sort rule's field selection.

        Args:
            old_field (Optional[str]): The previously selected field.
            new_field (str): The newly selected field.
        """
        self._available_fields.append(old_field)
        self._available_fields.remove(new_field)

        # Update field_dropdowns in SortRuleItems
        self._set_available_fields()

class SortRuleWidget(QtWidgets.QWidget):
    """Widget containing sort rules with a list and control buttons.

    UI Layout:
        +--------------------------------------+
        | Sort By:                             |
        |                                      |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        |                                      |
        | [(+) Add][Clear]        [Apply]      |
        +--------------------------------------+
    """

    LABEL = 'Sort By'

    # Signal emitted when rules are applied
    rules_applied = QtCore.Signal(list)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """Initialize the SortRuleWidget.

        Args:
            fields (List[str]): List of available fields for sorting.
            parent: Parent widget.
        """
        super().__init__(parent)

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        main_layout = QtWidgets.QVBoxLayout(self)
        button_layout = QtWidgets.QHBoxLayout()

        # Create Widgets
        # --------------
        # Label for the widget
        self.label = QtWidgets.QLabel(self.LABEL, self)

        # SortRuleListWidget for managing sort rules
        self.sort_rule_list_widget = SortRuleListWidget(self)

        # Buttons for adding, clearing, and applying rules
        self.add_button = QtWidgets.QPushButton(TablerQIcon.plus, "Add", self, enabled=bool(self.fields))
        self.clear_button = QtWidgets.QPushButton(TablerQIcon.clear_all, '', self, toolTip="Clear All")
        self.apply_button = QtWidgets.QPushButton("Apply", self)

        # Add Widgets to Layouts
        # ----------------------
        # Add buttons to the layout
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.clear_button, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        button_layout.addWidget(self.apply_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # Add components to the main layout
        main_layout.addWidget(self.label)
        main_layout.addWidget(self.sort_rule_list_widget)
        main_layout.addLayout(button_layout)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.sort_rule_list_widget.rule_added.connect(lambda: self.add_button.setEnabled(bool(self.sort_rule_list_widget.available_fields)))
        self.sort_rule_list_widget.rule_removed.connect(lambda: self.add_button.setEnabled(True))
        self.sort_rule_list_widget.rules_cleared.connect(lambda: self.add_button.setEnabled(bool(self.fields)))

        self.add_button.clicked.connect(lambda: self.sort_rule_list_widget.add_rule())
        self.clear_button.clicked.connect(self.sort_rule_list_widget.clear_rules)
        self.apply_button.clicked.connect(lambda: self.rules_applied.emit(self.sort_rule_list_widget.get_rules()))

    # Public Methods
    # --------------
    def set_fields(self, fields: List[str]):
        """Set the available fields for sorting.

        Args:
            fields (List[str]): The list of fields.
        """
        self.sort_rule_list_widget.set_fields(fields)

    # Class Properties
    # ----------------
    @property
    def fields(self) -> List[str]:
        return self.sort_rule_list_widget.fields

    @fields.setter
    def fields(self, fields: List[str]):
        self.set_fields(fields)


if __name__ == "__main__":
    import sys
    from blackboard import theme

    class MainWindow(QtWidgets.QMainWindow):

        FIELDS = ["Name", "Date", "Size", "Type"]
        def __init__(self):
            """Initialize the main window."""
            super().__init__()

            # Create SortRuleWidget with fields
            self.sort_rule_widget = SortRuleWidget(self)
            self.sort_rule_widget.set_fields(self.FIELDS)

            # Connect sortingChanged signal
            self.sort_rule_widget.rules_applied.connect(self.on_rules_applied)

            # Set up the main window
            self.setCentralWidget(self.sort_rule_widget)
            self.setWindowTitle("Sort Rule Widget Example with Apply Button")
            self.resize(400, 300)

        def on_rules_applied(self, sorting_rules: List['SortRule']) -> None:
            """Handle the sortingChanged signal.

            Args:
                sorting_rules (List[Tuple[str, SortOrder]]): The list of sorting rules.
            """
            # Handle the sorting logic here
            print("Sorting rules applied:")
            for sorting_rule in sorting_rules:
                print(sorting_rule)

    app = QtWidgets.QApplication(sys.argv)
    theme.set_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
