# Type Checking Imports
# ---------------------
from typing import List, Optional, Tuple

# Standard Library Imports
# ------------------------
from enum import Enum

# Third-Party Imports
# -------------------
from qtpy import QtCore, QtWidgets
from tablerqicon import TablerQIcon


# Class Definitions
# -----------------
class SortOrder(Enum):
    """Enumeration for sort order.
    """
    ASCENDING = 'ASC'
    DESCENDING = 'DESC'


class SortRuleWidgetItem(QtWidgets.QListWidgetItem):
    """Widget representing a single sort rule.

    UI Wireframe:

        +--------------------------------------+
        | ○ [ Field Dropdown ] [Asc][Desc] [x] |
        +--------------------------------------+
    """

    # Initialization and Setup
    # ------------------------
    def __init__(self, sort_rule_widget: 'SortRuleWidget'):
        """Initialize a SortRuleWidgetItem.

        Args:
            sort_rule_widget (SortRuleWidget): The parent SortRuleWidget.
        """
        super().__init__(sort_rule_widget)

        # Store the arguments
        self.sort_rule_widget = sort_rule_widget

        # Initialize UI and connections
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.current_field: Optional[str] = None

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
        button_group = QtWidgets.QButtonGroup(self.widget, exclusive=True)
        button_group.addButton(self.asc_button)
        button_group.addButton(self.desc_button)

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

        # Populate the field dropdown
        self.update_fields()

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.field_dropdown.currentIndexChanged.connect(self.field_changed)
        self.delete_button.clicked.connect(self.delete_rule)

    def update_fields(self):
        """Update the field dropdown with unused fields.
        """
        current_field = self.current_field
        self.field_dropdown.blockSignals(True)
        self.field_dropdown.clear()

        unused_fields = self.sort_rule_widget.get_unused_fields()
        # Include the current field if it's already selected
        if current_field and current_field not in unused_fields:
            unused_fields.append(current_field)

        self.field_dropdown.addItems(unused_fields)
        # Set the current field
        if current_field:
            index = self.field_dropdown.findText(current_field)
            if index >= 0:
                self.field_dropdown.setCurrentIndex(index)
        else:
            # Select the first available field
            if unused_fields:
                self.field_dropdown.setCurrentIndex(0)
                self.current_field = self.field_dropdown.currentText()
                # Update selected_fields in SortRuleWidget
                self.sort_rule_widget.field_changed(self, None, self.current_field)
        self.field_dropdown.blockSignals(False)

    def field_changed(self, index: int):
        """Handle field selection changes.

        Args:
            index (int): The index of the selected field in the dropdown.
        """
        old_field = self.current_field
        new_field = self.field_dropdown.currentText()
        self.current_field = new_field
        # Update the selected_fields in sort_rule_widget
        self.sort_rule_widget.field_changed(self, old_field, new_field)

    def delete_rule(self):
        """Delete this sort rule.
        """
        self.sort_rule_widget.remove_sort_rule(self)

    def get_sort_rule(self) -> Tuple[str, SortOrder]:
        """Return the current sort rule as a tuple.

        Returns:
            Tuple[str, SortOrder]: The field and sort order.
        """
        sort_order = SortOrder.ASCENDING if self.asc_button.isChecked() else SortOrder.DESCENDING
        return (self.field_dropdown.currentText(), sort_order)


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

    # Signal emitted when sorting rules are applied
    sorting_changed = QtCore.Signal(list)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, fields: Optional[List[str]] = None):
        """Initialize the SortRuleWidget.

        Args:
            parent (Optional[QtWidgets.QWidget]): The parent widget.
            fields (Optional[List[str]]): The list of available fields for sorting.
        """
        super().__init__(parent, dragDropMode=QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        # Store the arguments
        self.fields: List[str] = fields or []

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self.sort_rule_items: List[SortRuleWidgetItem] = []
        self.selected_fields: List[str] = []

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        self.overlay_layout = QtWidgets.QHBoxLayout(self)
        self.overlay_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)

        # Create Widgets
        # --------------
        # Add Sort Button
        self.add_sort_button = QtWidgets.QPushButton(TablerQIcon.plus, "Add Sort", self)
        self.clear_button = QtWidgets.QPushButton(TablerQIcon.clear_all, '', self, toolTip="Clear All")
        self.apply_button = QtWidgets.QPushButton("Apply", self)

        # Add Widgets to Layouts
        # ----------------------
        self.overlay_layout.addWidget(self.add_sort_button)
        self.overlay_layout.addWidget(self.clear_button, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.overlay_layout.addWidget(self.apply_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def __init_signal_connections(self):
        """Initialize signal-slot connections.
        """
        self.add_sort_button.clicked.connect(self.add_sort_rule)
        self.clear_button.clicked.connect(self.clear_all_rules)
        self.apply_button.clicked.connect(self.emit_sorting_changed)
        self.model().rowsMoved.connect(self.on_rows_moved)

    def set_fields(self, fields: List[str]):
        """Set the available fields for sorting.

        Args:
            fields (List[str]): The list of fields.
        """
        self.fields = fields
        self.selected_fields.clear()
        # Update existing sort rule items
        for item in self.sort_rule_items:
            item.current_field = None
            item.update_fields()
        # Enable add_sort_button if there are fields
        self.add_sort_button.setDisabled(len(self.get_unused_fields()) == 0)

    def get_unused_fields(self) -> List[str]:
        """Get the list of fields not currently used in sort rules.

        Returns:
            List[str]: The list of unused fields.
        """
        return [field for field in self.fields if field not in self.selected_fields]

    def add_sort_rule(self):
        """Add a new sort rule.
        """
        sort_rule_item = SortRuleWidgetItem(self)
        self.addItem(sort_rule_item)
        self.sort_rule_items.append(sort_rule_item)
        sort_rule_item.update_fields()

        # Disable add_sort_button if all fields are used
        if len(self.get_unused_fields()) == 0:
            self.add_sort_button.setDisabled(True)

    def field_changed(self, sort_rule_item: 'SortRuleWidgetItem', old_field: Optional[str], new_field: str):
        """Handle changes to a sort rule's field selection.

        Args:
            sort_rule_item (SortRuleWidgetItem): The sort rule item that changed.
            old_field (Optional[str]): The previously selected field.
            new_field (str): The newly selected field.
        """
        if old_field in self.selected_fields:
            self.selected_fields.remove(old_field)
        if new_field not in self.selected_fields:
            self.selected_fields.append(new_field)
        # Update field_dropdowns in other SortRuleItems
        for item in self.sort_rule_items:
            if item != sort_rule_item:
                item.update_fields()

        self.add_sort_button.setDisabled(len(self.get_unused_fields()) == 0)

    def remove_sort_rule(self, sort_rule_item: 'SortRuleWidgetItem'):
        """Remove a sort rule item.

        Args:
            item_widget (SortRuleWidgetItem): The sort rule item to remove.
        """
        # Remove selected field
        if sort_rule_item.current_field in self.selected_fields:
            self.selected_fields.remove(sort_rule_item.current_field)
        # Remove item
        self.takeItem(self.row(sort_rule_item))
        self.sort_rule_items.remove(sort_rule_item)
        # Update field_dropdowns in other items
        for item in self.sort_rule_items:
            item.update_fields()
        # Enable add_sort_button if necessary
        self.add_sort_button.setDisabled(len(self.get_unused_fields()) == 0)

    def clear_all_rules(self):
        """Clear all sort rules.
        """
        self.clear()
        self.sort_rule_items.clear()
        self.selected_fields.clear()
        self.add_sort_button.setDisabled(False)

    def on_rows_moved(self, parent, start: int, end: int, destination, row: int):
        """Handle the event when sort rules are reordered.

        Args:
            parent: The parent model index.
            start (int): The starting row.
            end (int): The ending row.
            destination: The destination model index.
            row (int): The destination row.
        """
        # Rows have been moved; no action needed here
        pass

    def emit_sorting_changed(self):
        """Emit the sorting_changed signal with current sorting rules.
        """
        sorting_rules = self.get_sorting_rules()
        self.sorting_changed.emit(sorting_rules)

    def get_sorting_rules(self) -> List[Tuple[str, 'SortOrder']]:
        """Return the current sorting rules.

        Returns:
            List[Tuple[str, SortOrder]]: A list of tuples containing field names and sort orders.
        """
        sorting_rules = [item.get_sort_rule() for item in self.sort_rule_items]
        return sorting_rules


if __name__ == "__main__":
    import sys
    from blackboard import theme

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            """Initialize the main window."""
            super().__init__()

            # Create SortRuleWidget with fields
            self.sort_rule_widget = SortRuleWidget(fields=["Name", "Date", "Size", "Type"])

            # Connect sortingChanged signal
            self.sort_rule_widget.sorting_changed.connect(self.on_sorting_changed)

            # Set up the main window
            self.setCentralWidget(self.sort_rule_widget)
            self.setWindowTitle("Sort Rule Widget Example with Apply Button")
            self.resize(400, 300)

        def on_sorting_changed(self, sorting_rules: List[Tuple[str, SortOrder]]) -> None:
            """Handle the sortingChanged signal.

            Args:
                sorting_rules (List[Tuple[str, SortOrder]]): The list of sorting rules.
            """
            # Handle the sorting logic here
            print("Sorting rules applied:")
            for field, order in sorting_rules:
                print(f"Field: {field}, Order: {order.name}")

    app = QtWidgets.QApplication(sys.argv)
    theme.set_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
