# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, List, Optional, Dict

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
if TYPE_CHECKING:
    from blackboard.widgets.base_rule_widget import BaseRuleListWidget
from blackboard.widgets.base_rule_widget import BaseRuleWidgetItem, BaseRuleWidget


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

class SortRuleWidgetItem(BaseRuleWidgetItem):
    """Widget representing a single sort rule.

    UI Wireframe:

        +--------------------------------------+
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        +--------------------------------------+
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, rule_list_widget: 'BaseRuleListWidget', field: str):
        """Initialize a SortRuleWidgetItem.

        Args:
            rule_list_widget (BaseRuleListWidget): The parent BaseRuleListWidget.
        """
        super().__init__(rule_list_widget, field=field)

        # Initialize UI and connections
        self.__init_ui()

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Widgets
        # --------------
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

        # Add Widgets to Layouts
        # ----------------------
        self.rule_option_layout.addWidget(self.asc_button)
        self.rule_option_layout.addWidget(self.desc_button)

    # Public Methods
    # --------------
    def get_rule(self) -> 'SortRule':
        """Return the current sort rule as a SortRule dataclass instance.

        Returns:
            SortRule: An instance containing the field and sort order.
        """
        return SortRule(
            field=self._current_field,
            order=SortOrder.ASCENDING if self.asc_button.isChecked() else SortOrder.DESCENDING,
        )

class SortRuleWidget(BaseRuleWidget):
    """Widget containing sort rules with a list and control buttons.

    UI Layout:
        +--------------------------------------+
        | Sort By:                             |
        |                                      |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        |                                      |
        | [(+) Add][Clear]             [Apply] |
        +--------------------------------------+
    """

    LABEL = 'Sort By'

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """Initialize the SortRuleWidget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent, item_class=SortRuleWidgetItem)

class GroupRuleWidget(BaseRuleWidget):
    """Widget containing sort rules with a list and control buttons.

    UI Layout:
        +----------------------------+
        | Group By:                  |
        |                            |
        | ○ [  Field Dropdown  ] [x] |
        | ○ [  Field Dropdown  ] [x] |
        | ○ [  Field Dropdown  ] [x] |
        |                            |
        | [(+) Add][Clear]   [Apply] |
        +----------------------------+
    """

    LABEL = 'Group By'


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
