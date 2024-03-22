# Type Checking Imports
# ---------------------
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class TreeUtil:

    @classmethod
    def get_child_items(cls, tree_widget: 'QtWidgets.QTreeWidget', 
                        parent_item: Optional['QtWidgets.QTreeWidgetItem'] = None) -> List['QtWidgets.QTreeWidgetItem']:
        """Recursively gathers all child items from a QTreeWidget, performing a depth-first search traversal.

        Args:
            tree_widget (QtWidgets.QTreeWidget): The tree widget to traverse.
            parent_item (Optional[QtWidgets.QTreeWidgetItem]): The parent item to start traversal from. 
                If None, starts from the root.

        Returns:
            List['QtWidgets.QTreeWidgetItem']: A list of QtWidgets.QTreeWidgetItem, including all child items in the tree.
        """
        # Get the root item of the tree widget if not provided.
        parent_item = parent_item or tree_widget.invisibleRootItem()

        # Initialize an empty list to hold the traversed items.
        items = []

        # Recursively traverse the children of the current item.
        for child_index in range(parent_item.childCount()):
            # Retrieve and store the child item at the current index.
            child_item = parent_item.child(child_index)

            # Append the child item and recursively add its children to the list.
            items.append(child_item)
            items.extend(cls.get_child_items(tree_widget, child_item))

        return items

    @staticmethod
    def get_shown_column_indexes(tree_widget: 'QtWidgets.QTreeWidget') -> List[int]:
        """Returns a list of indices for the columns that are shown (i.e., not hidden) in the tree widget.

        Returns:
            List[int]: A list of integers, where each integer is the index of a shown column in the tree widget.
        """
        # Get the header of the tree widget
        header = tree_widget.header()

        # Generate a list of the indices of the columns that are not hidden
        column_indexes = [column_index for column_index in range(header.count()) if not header.isSectionHidden(column_index)]

        # Return the list of the index of a shown column in the tree widget.
        return column_indexes

    @staticmethod
    def get_child_level(item: 'QtWidgets.QTreeWidgetItem') -> int:
        """Get the child level of TreeWidgetItem

        Returns:
            int: The child level of the TreeWidgetItem
        """
        # Initialize child level
        child_level = 0

        # Iterate through the parent items to determine the child level
        while item.parent():
            # Increment child level for each parent
            child_level += 1
            # Update item to be its parent
            item = item.parent()

        # Return the final child level
        return child_level

    @classmethod
    def get_items_at_child_level(cls, tree_widget: 'QtWidgets.QTreeWidget', child_level: int = 0) -> List['QtWidgets.QTreeWidgetItem']:
        """Retrieve all items at a specific child level in the tree widget.

        Args:
            child_level (int): The child level to retrieve items from. Defaults to 0 (top-level items).

        Returns:
            List[TreeWidgetItem]: List of `QTreeWidgetItem` objects at the specified child level.
        """
        # If child level is 0, return top-level items
        if not child_level:
            # return top-level items
            return [tree_widget.topLevelItem(row) for row in range(tree_widget.topLevelItemCount())]

        # Get all items in the tree widget
        all_items = cls.get_child_items(tree_widget)

        # Filter items to only those at the specified child level
        return [item for item in all_items if cls.get_child_level(item) == child_level]
