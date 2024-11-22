# Type Checking Imports
# ---------------------
from typing import Any, Callable, List, Optional

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class ListUtil:

    @classmethod
    def get_items(cls, list_widget: 'QtWidgets.QListWidget', is_only_checked: bool = False, 
                  filter_func: Optional[Callable[['QtWidgets.QListWidgetItem'], bool]] = None) -> List['QtWidgets.QListWidgetItem']:
        """Retrieve all items from a QListWidget, optionally filtering them.

        Args:
            list_widget (QtWidgets.QListWidget): The QListWidget to get items from.
            is_only_checked (bool): Whether to include only checked items.
            filter_func (Callable[['QtWidgets.QListWidgetItem'], bool]): Optional function to filter items.

        Returns:
            List[QtWidgets.QListWidgetItem]: A list of QListWidgetItems that meet the criteria.
        """
        items = []
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            if is_only_checked and item.checkState() != QtCore.Qt.CheckState.Checked:
                continue
            if filter_func and not filter_func(item):
                continue
            items.append(item)
        return items

    @staticmethod
    def get_item_data_list(items: List['QtWidgets.QListWidgetItem'], 
                           role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> List[Any]:
        """Retrieve data from a list of QListWidgetItems using a specified data role.

        Args:
            items (List[QtWidgets.QListWidgetItem]): The list of items to extract data from.
            role (int): The data role to use when retrieving data. Defaults to DisplayRole.

        Returns:
            List[Any]: A list of data from the specified role for each item.
        """
        return [item.data(role) for item in items]

    @classmethod
    def show_all_items(cls, list_widget: 'QtWidgets.QListWidget'):
        """Show all items in the QListWidget.

        Args:
            list_widget (QtWidgets.QListWidget): The list widget to operate on.
        """
        cls.set_items_visibility(cls.get_items(list_widget), True)

    @classmethod
    def hide_all_items(cls, list_widget: 'QtWidgets.QListWidget'):
        """Hide all items in the QListWidget.

        Args:
            list_widget (QtWidgets.QListWidget): The list widget to operate on.
        """
        cls.set_items_visibility(cls.get_items(list_widget), False)

    @classmethod
    def set_items_visibility(cls, items: List['QtWidgets.QListWidgetItem'], is_visible: bool):
        """Set visibility of the specified items.

        Args:
            items (List[QtWidgets.QListWidgetItem]): The list of items whose visibility will be set.
            is_visible (bool): The visibility state to apply (True for show, False for hide).
        """
        for item in items:
            item.setHidden(not is_visible)
