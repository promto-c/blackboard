# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon


# Class Definitions
# -----------------
class EnumListWidgetItem(QtWidgets.QListWidgetItem):

    def __init__(self, parent: 'EnumListWidget'):
        """Initializes the EnumListWidgetItem.

        Args:
            parent (EnumListWidget): The parent list widget to which this item belongs.
        """
        super().__init__(parent)

        # Store the arguments
        self.list_widget = parent

        # Initialize setup
        self.__init_ui()
        self.__init_signal_connections()

    def __init_ui(self):
        """Initializes the UI of the widget.
        """
        # Create Layouts
        self.item_widget = QtWidgets.QWidget(self.list_widget)
        self.item_widget.setMinimumHeight(24)
        layout = QtWidgets.QHBoxLayout(self.item_widget)

        # Create Widgets
        self.value_input = QtWidgets.QLineEdit(self.item_widget)
        self.remove_button = QtWidgets.QPushButton(TablerQIcon.trash, '', self.item_widget)
        self.move_up_button = QtWidgets.QPushButton(TablerQIcon.chevron_up, '', self.item_widget)
        self.move_down_button = QtWidgets.QPushButton(TablerQIcon.chevron_down, '', self.item_widget)

        # Add Widgets to Layouts
        layout.addWidget(self.value_input)
        layout.addWidget(self.remove_button)
        layout.addWidget(self.move_up_button)
        layout.addWidget(self.move_down_button)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.list_widget.addItem(self)
        self.list_widget.setItemWidget(self, self.item_widget)

    def __init_signal_connections(self):
        """Initializes signal-slot connections.
        """
        # Connect signals to slots
        self.remove_button.clicked.connect(lambda: self.list_widget.takeItem(self.list_widget.row(self)))
        self.move_up_button.clicked.connect(lambda: self.list_widget.move_item_up(self))
        self.move_down_button.clicked.connect(lambda: self.list_widget.move_item_down(self))

    def get_value(self) -> str:
        """Gets the current value from the input field.

        Returns:
            str: The current value of the input field.
        """
        return self.value_input.text().strip()

    def set_value(self, value: str):
        """Sets the value of the input field.

        Args:
            value (str): The value to set in the input field.
        """
        self.value_input.setText(value)

class EnumListWidget(QtWidgets.QListWidget):
    """A QListWidget subclass to manage a list of EnumListWidgetItems.

    This widget allows the addition, retrieval, and reordering of items, each of which
    is represented by an `EnumListWidgetItem` containing a value input field and buttons
    for removal, moving up, and moving down.

    UI Wireframe:
        +---------------------------------+
        | +-----------------------------+ |
        | | [  QLineEdit  ] [🗑] [↑] [↓] | |
        | +-----------------------------+ |
        | | [  QLineEdit  ] [🗑] [↑] [↓] | |
        | +-----------------------------+ |
        | | [  QLineEdit  ] [🗑] [↑] [↓] | |
        | +-----------------------------+ |
        | | [  QLineEdit  ] [🗑] [↑] [↓] | |
        | +-----------------------------+ |
        | | [  QLineEdit  ] [🗑] [↑] [↓] | |
        | +-----------------------------+ |
        |                                 |
        +---------------------------------+

        Each row represents an item in the list, containing:
        - QLineEdit: An input field for entering a value.
        - 🗑 Button: A button to remove the item from the list.
        - ↑ Button: A button to move the item up in the list.
        - ↓ Button: A button to move the item down in the list.

        The EnumListWidget manages these items and allows for the retrieval
        of their values and the reordering of the items.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, parent=None):
        """Initializes the EnumListWidget.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.setGridSize(QtCore.QSize(0, 24))

    def add_item(self, value: str = ""):
        """Adds a new item to the list with the specified value.

        Args:
            value (str, optional): The value to set in the new item. Defaults to an empty string.
        """
        list_item = EnumListWidgetItem(self)
        list_item.set_value(value)

    def get_values(self) -> list[str]:
        """Gets the list of values from all items in the list.

        Returns:
            list[str]: A list of all the values in the list.
        """
        return [value for index in range(self.count()) if (value:= self.item(index).get_value())]

    def set_values(self, values: list[str]):
        """Sets the list of values in the widget.

        This will clear any existing items and replace them with the provided values.

        Args:
            values (list[str]): A list of strings to set as the new values in the widget.
        """
        self.clear()  # Clear existing items

        for value in values:
            self.add_item(value)  # Add new items with the provided values

    def move_item_up(self, item: EnumListWidgetItem):
        """Moves the value of the given item up in the list.

        Args:
            item (EnumListWidgetItem): The item whose value should be moved up.
        """
        current_row = self.row(item)
        
        if current_row > 0:
            item_above = self.item(current_row - 1)

            # Swap the values
            current_value = item.get_value()
            above_value = item_above.get_value()

            item.set_value(above_value)
            item_above.set_value(current_value)

    def move_item_down(self, item: EnumListWidgetItem):
        """Moves the value of the given item down in the list.

        Args:
            item (EnumListWidgetItem): The item whose value should be moved down.
        """
        current_row = self.row(item)

        if current_row < self.count() - 1:
            item_below = self.item(current_row + 1)

            # Swap the values
            current_value = item.get_value()
            below_value = item_below.get_value()

            item.set_value(below_value)
            item_below.set_value(current_value)


if __name__ == "__main__":
    # Example usage
    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()

            self.enum_list_widget = EnumListWidget()

            add_button = QtWidgets.QPushButton("Add Enum")
            add_button.clicked.connect(self.add_enum)

            self.central_widget = QtWidgets.QWidget()
            self.layout = QtWidgets.QVBoxLayout(self.central_widget)
            self.layout.addWidget(self.enum_list_widget)
            self.layout.addWidget(add_button)

            self.setCentralWidget(self.central_widget)

        def add_enum(self):
            # Add a new item with an empty value
            self.enum_list_widget.add_item()

    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
