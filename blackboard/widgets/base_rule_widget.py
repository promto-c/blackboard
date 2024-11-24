# Type Checking Imports
# ---------------------
from typing import List, Optional, Any, Type

# Third-Party Imports
# -------------------
from qtpy import QtCore, QtWidgets
from tablerqicon import TablerQIcon

# Local Imports
# -------------
from blackboard.utils.list_utils import ListUtil


# Class Definitions
# -----------------
class BaseRuleWidgetItem(QtWidgets.QListWidgetItem):
    """Base class for rule widget items with shared UI and an extendable placeholder layout.

    UI Wireframe:

        +--------------------------------------+
        | ○ [ Field Dropdown ] [         ] [x] |
        +--------------------------------------+
    """

    def __init__(self, rule_list_widget: 'BaseRuleListWidget', field: str):
        """Initialize a SortRuleWidgetItem.

        Args:
            rule_list_widget (BaseRuleListWidget): The parent SortRuleListWidget.
            field (str): The field associated with this rule item.
        """
        super().__init__(rule_list_widget)

        # Store the arguments
        self.rule_list_widget = rule_list_widget
        self._current_field = field

        # Initialize UI and connections
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initialize the shared UI of the widget.
        """
        # Create Layouts
        # --------------
        self.widget = QtWidgets.QWidget(self.rule_list_widget)
        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.setContentsMargins(4, 4, 4, 4)

        # Shared Widgets
        self.drag_handle = QtWidgets.QLabel(
            self.widget, maximumWidth=20,
            pixmap=TablerQIcon.grip_vertical.pixmap(20, 20),
            cursor=QtCore.Qt.CursorShape.SizeAllCursor
        )
        self.field_dropdown = QtWidgets.QComboBox(
            self.widget, toolTip="Select a field", cursor=QtCore.Qt.CursorShape.PointingHandCursor,
        )
        self.delete_button = QtWidgets.QToolButton(
            self.widget, icon=TablerQIcon.trash, toolTip="Delete this rule",
            cursor=QtCore.Qt.CursorShape.PointingHandCursor,
        )

        # Add shared widgets to layout
        layout.addWidget(self.drag_handle)
        layout.addWidget(self.field_dropdown)

        # Placeholder layout for subclass-specific components
        self.rule_option_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self.rule_option_layout)

        # Add delete button last
        layout.addWidget(self.delete_button)

        self.setSizeHint(self.widget.sizeHint())
        self.rule_list_widget.setItemWidget(self, self.widget)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.field_dropdown.currentTextChanged.connect(self._update_used_field)
        self.delete_button.clicked.connect(lambda: self.rule_list_widget.remove_rule(self))

    # Public Methods
    # --------------
    def set_available_fields(self, fields: List[str]):
        """Update the field dropdown with unused fields.

        Args:
            fields (List[str]): List of available fields.
        """
        self.field_dropdown.blockSignals(True)
        self.field_dropdown.clear()
        self.field_dropdown.addItems([self._current_field] + fields)
        self.field_dropdown.blockSignals(False)

    # Placeholder Methods for Subclasses
    # ----------------------------------
    def get_rule(self) -> Any:
        """Retrieve the rule details. Default implementation returns the current field.
        """
        return self._current_field

    # Class Properties
    # ----------------
    @property
    def current_field(self) -> str:
        """Current field used by the rule widget."""
        return self._current_field

    @current_field.setter
    def current_field(self, field: str):
        self.field_dropdown.setCurrentText(field)

    # Private Methods
    # ---------------
    def _update_used_field(self, new_field: str):
        """Handle field selection changes."""
        old_field = self._current_field
        self._current_field = new_field
        self.rule_list_widget._update_used_fields(old_field, new_field)


class BaseRuleListWidget(QtWidgets.QListWidget):
    """Base widget for managing rules with customizable items.

    This widget serves as a base class for rule list widgets, providing 
    core functionality while allowing subclasses to implement specific 
    rule item behavior.

    Attributes:
        rule_added (Signal): Emitted when a new rule is added.
        rule_removed (Signal): Emitted when a rule is removed.
        rules_cleared (Signal): Emitted when all rules are cleared.

    UI Layout:
        +--------------------------------------+
        | ○ [ Field Dropdown ] [         ] [x] |
        | ○ [ Field Dropdown ] [         ] [x] |
        | ○ [ Field Dropdown ] [         ] [x] |
        +--------------------------------------+
    """

    # Signals
    rule_added = QtCore.Signal()
    rule_removed = QtCore.Signal()
    rules_cleared = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, item_class: Type['BaseRuleWidgetItem'] = BaseRuleWidgetItem):
        """Initialize the BaseRuleListWidget.

        Args:
            parent (Optional[QtWidgets.QWidget]): The parent widget.
            item_class (Type[BaseRuleWidgetItem]): The class to use for rule items.
        """
        if not issubclass(item_class, BaseRuleWidgetItem):
            raise TypeError("item_class must be a subclass of BaseRuleWidgetItem")

        super().__init__(parent, dragDropMode=QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        # Store the arguments
        self._item_class = item_class

        # Initialize setup
        self.__init_attributes()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._fields: List[str] = []
        self._available_fields: List[str] = []

    # Public Methods
    # --------------
    def set_fields(self, fields: List[str]):
        """Set the available fields for rule items.

        Args:
            fields (List[str]): The list of fields.
        """
        self._fields = fields
        self.clear_rules()

    def add_rule(self, field: Optional[str] = None):
        """Add a new rule to the list.

        Args:
            field (Optional[str]): The field associated with the rule.
        """
        if not self._fields:
            return

        if field and field not in self._fields:
            raise ValueError(f"Field '{field}' is not valid. Available fields: {self._fields}")

        if field is None:
            if not self._available_fields:
                raise ValueError("No available fields to add a new rule.")
            field = self._available_fields.pop(0)
        else:
            self._available_fields.remove(field)

        # Create a rule item using the specified item class
        _rule_item = self._item_class(rule_list_widget=self, field=field)

        self._set_available_fields()
        self.rule_added.emit()

    def remove_rule(self, rule_item: 'BaseRuleWidgetItem'):
        """Remove a rule item from the list.

        Args:
            rule_item (BaseRuleWidgetItem): The rule item to remove.
        """
        # Remove selected field and remove item
        self._available_fields.append(rule_item.current_field)
        self.takeItem(self.row(rule_item))

        # Update field_dropdowns in other items
        self._set_available_fields()
        self.rule_removed.emit()

    def clear_rules(self):
        """Clear all rules from the list.
        """
        self.clear()
        self._available_fields = self._fields.copy()
        self.rules_cleared.emit()

    def get_rules(self) -> List:
        """Retrieve the list of rules.

        Returns:
            List: A list of rules.
        """
        return [item.get_rule() for item in self._get_items()]

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
    def _get_items(self) -> List[BaseRuleWidgetItem]:
        """Retrieve all rule items.
        """
        return ListUtil.get_items(self)

    def _set_available_fields(self):
        """Update the available fields for all rule items.
        """
        for item in self._get_items():
            item.set_available_fields(self._available_fields)

    def _update_used_fields(self, old_field: str, new_field: str):
        """Handle changes to a rule's field selection.

        Args:
            old_field (str): The previously selected field.
            new_field (str): The newly selected field.
        """
        self._available_fields.append(old_field)
        self._available_fields.remove(new_field)

        # Update field_dropdowns in SortRuleItems
        self._set_available_fields()


class BaseRuleWidget(QtWidgets.QWidget):
    """Base class for widgets managing rules with a list and control buttons.

    Attributes:
        LABEL (str): The label for the widget (to be overridden in subclasses).
        rules_applied (Signal): Emitted when rules are applied.

    UI Layout:
        +--------------------------------------+
        | [LABEL]:                             |
        |                                      |
        | ○ [ Field Dropdown ] [         ] [x] |
        | ○ [ Field Dropdown ] [         ] [x] |
        | ○ [ Field Dropdown ] [         ] [x] |
        |                                      |
        | [(+) Add][Clear]        [Apply]      |
        +--------------------------------------+
    """

    LABEL = "Rules"

    # Signal emitted when rules are applied
    rules_applied = QtCore.Signal(list)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, item_class: Type['BaseRuleWidgetItem'] = BaseRuleWidgetItem):
        """Initialize the BaseRuleWidget.

        Args:
            parent (Optional[QtWidgets.QWidget]): Parent widget.
            item_class (Type[BaseRuleWidgetItem]): The class to use for rule items.
        """
        super().__init__(parent)

        # Store the arguments
        self._item_class = item_class

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
        self.rule_list_widget = BaseRuleListWidget(self, item_class=self._item_class)

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
        main_layout.addWidget(self.rule_list_widget)
        main_layout.addLayout(button_layout)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.rule_list_widget.rule_added.connect(lambda: self.add_button.setEnabled(bool(self.rule_list_widget.available_fields)))
        self.rule_list_widget.rule_removed.connect(lambda: self.add_button.setEnabled(True))
        self.rule_list_widget.rules_cleared.connect(lambda: self.add_button.setEnabled(bool(self.fields)))

        self.add_button.clicked.connect(lambda: self.rule_list_widget.add_rule())
        self.clear_button.clicked.connect(self.rule_list_widget.clear_rules)
        self.apply_button.clicked.connect(lambda: self.rules_applied.emit(self.rule_list_widget.get_rules()))

    # Public Methods
    # --------------
    def set_fields(self, fields: List[str]):
        """Set the available fields for rules.

        Args:
            fields (List[str]): The list of fields.
        """
        self.rule_list_widget.set_fields(fields)

    # Class Properties
    # ----------------
    @property
    def fields(self) -> List[str]:
        return self.rule_list_widget.fields

    @fields.setter
    def fields(self, fields: List[str]):
        self.set_fields(fields)
