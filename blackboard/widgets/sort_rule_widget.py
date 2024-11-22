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

    def __str__(self):
        return f"SortRule(field='{self.field}', order='{self.order.name}')"

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
    def __init__(self, sort_rule_widget: 'SortRuleWidget', field: str):
        """Initialize a SortRuleWidgetItem.

        Args:
            sort_rule_widget (SortRuleWidget): The parent SortRuleWidget.
        """
        super().__init__(sort_rule_widget)

        # Store the arguments
        self.sort_rule_widget = sort_rule_widget
        self._current_field = field

        # Initialize UI and connections
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        self.widget = QtWidgets.QWidget(self.sort_rule_widget)
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
        self.sort_rule_widget.setItemWidget(self, self.widget)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.field_dropdown.currentTextChanged.connect(self._update_used_field)
        self.delete_button.clicked.connect(lambda: self.sort_rule_widget.remove_rule(self))

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
        # Update the used_fields in sort_rule_widget
        self.sort_rule_widget._update_used_fields(old_field, new_field)

class SortRuleWidget(QtWidgets.QListWidget):
    """Widget for managing sort rules.

    UI Wireframe:

        +--------------------------------------+
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        |                                      |
        | [(+) Add Sort][Clear]        [Apply] |
        +--------------------------------------+
    """

    # Signal emitted when rules are applied
    rules_applied = QtCore.Signal(list)

    # Initialization and Setup
    # ------------------------
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, fields: Optional[List[str]] = None):
        """Initialize the SortRuleWidget.

        Args:
            parent (Optional[QtWidgets.QWidget]): The parent widget.
            fields (Optional[List[str]]): The list of available fields for sorting.
        """
        super().__init__(parent, dragDropMode=QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        # Store the arguments
        self._fields = fields or []

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._available_fields = self._fields.copy()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        self.overlay_layout = QtWidgets.QHBoxLayout(self)
        self.overlay_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)

        # Create Widgets
        # --------------
        self.add_button = QtWidgets.QPushButton(TablerQIcon.plus, "Add", self, enabled=bool(self._fields))
        self.clear_button = QtWidgets.QPushButton(TablerQIcon.clear_all, '', self, toolTip="Clear All")
        self.apply_button = QtWidgets.QPushButton("Apply", self)

        # Add Widgets to Layouts
        # ----------------------
        self.overlay_layout.addWidget(self.add_button)
        self.overlay_layout.addWidget(self.clear_button, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.overlay_layout.addWidget(self.apply_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.add_button.clicked.connect(lambda: self.add_rule())
        self.clear_button.clicked.connect(self.clear_all_rules)
        self.apply_button.clicked.connect(self.apply)

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
        self.clear_all_rules()

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

        # Disable add_button if all fields are used
        if not self._available_fields:
            self.add_button.setDisabled(True)

    def remove_rule(self, rule_item: 'SortRuleWidgetItem'):
        """Remove a sort rule item.

        Args:
            item_widget (SortRuleWidgetItem): The sort rule item to remove.
        """
        # Remove selected field
        self._available_fields.append(rule_item.current_field)
        # Remove item
        self.takeItem(self.row(rule_item))

        # Update field_dropdowns in other items
        self._set_available_fields()

        # Enable add_button if necessary
        self.add_button.setEnabled(True)

    def clear_all_rules(self):
        """Clear all sort rules.
        """
        self.clear()
        self._available_fields = self._fields.copy()
        self.add_button.setEnabled(bool(self._fields))

    def get_rules(self) -> List['SortRule']:
        """Return the current sorting rules.

        Returns:
            List[Tuple[str, SortOrder]]: A list of tuples containing field names and sort orders.
        """
        return [item.get_rule() for item in self.get_items()]

    def apply(self):
        """Emit the rules_applied signal with current sorting rules.
        """
        self.rules_applied.emit(self.get_rules())

    # Class Properties
    # ----------------
    @property
    def fields(self) -> List[str]:
        return self._fields

    @fields.setter
    def fields(self, fields: List[str]):
        self.set_fields(fields)

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
