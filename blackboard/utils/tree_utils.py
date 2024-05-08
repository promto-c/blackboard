# Type Checking Imports
# ---------------------
from typing import Any, Callable, List, Optional, Tuple

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets

# Class Definitions
# -----------------
class TreeUtil:

    @classmethod
    def get_child_items(cls, tree_widget: 'QtWidgets.QTreeWidget',
                        parent_item: Optional['QtWidgets.QTreeWidgetItem'] = None,
                        is_only_leaf: bool = False, is_only_checked: bool = False,
                        filter_func: Optional[Callable[['QtWidgets.QTreeWidgetItem'], bool]] = None
                        ) -> List['QtWidgets.QTreeWidgetItem']:
        """Recursively gathers all child items from a QTreeWidget, performing a depth-first search traversal.

        Args:
            tree_widget (QtWidgets.QTreeWidget): The tree widget to traverse.
            parent_item (Optional[QtWidgets.QTreeWidgetItem]): The parent item to start traversal from. 
                If None, starts from the root.
            filter_func (Callable[['QtWidgets.QTreeWidgetItem'], bool]): Optional function to filter items.

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

            # Optionally filter by check state if only_checked is True.
            if is_only_checked and child_item.checkState() == QtCore.Qt.CheckState.Unchecked:
                continue

            # Check if the child item has children.
            if child_item.childCount() > 0:
                # Recursively add the child items to the list.
                items.extend(cls.get_child_items(tree_widget, child_item, is_only_leaf, is_only_checked, filter_func))
                if is_only_leaf:
                    continue

            # Apply the filter function to the child item if provided.
            if filter_func and not filter_func(child_item):
                continue

            # Add the child item to the list.
            items.append(child_item)

        return items

    @classmethod
    def get_model_indexes(cls, model: 'QtCore.QAbstractItemModel', parent: 'QtCore.QModelIndex' = QtCore.QModelIndex(), 
                          column: int = 0, is_only_leaf: bool = False, is_only_checked: bool = False,
                          data_match: Optional[Tuple['QtCore.Qt.ItemDataRole', Any]] = None,
                          filter_func: Optional[Callable[['QtCore.QModelIndex'], bool]] = None) -> List['QtCore.QModelIndex']:
        """Retrieve QModelIndexes from a QAbstractItemModel based on specified criteria.

        This function performs a depth-first search of the model's tree structure,
        collecting indexes based on the provided column number. It optionally filters
        indexes to include only leaf nodes, nodes matching specific data, or nodes that
        pass a custom filter function.

        Args:
            model: The QAbstractItemModel to search.
            column: The column number from which to retrieve QModelIndexes.
            is_only_checked: If True, only indexes with checked state will be returned.
            is_only_leaf: True if only leaf node indexes should be returned; False otherwise.
            data_match: Optional tuple (role, value) to match data in the nodes.
            filter_func: Optional function that takes a QModelIndex and returns a bool
                         indicating whether the index should be included.

        Returns:
             List['QtCore.QModelIndex']: A list of QModelIndex objects that meet the specified criteria.
        """
        indexes = []

        if not model:
            return indexes

        # Iterate through the model's rows and columns
        for row in range(model.rowCount(parent)):
            # Get the QModelIndex for the current row
            index = model.index(row, column, parent)
            if not index.isValid():
                continue

            # Optionally filter by check state if only_checked is True
            if is_only_checked and index.data(QtCore.Qt.CheckStateRole) == QtCore.Qt.CheckState.Unchecked:
                continue

            # Check if the index is a leaf node
            if model.hasChildren(index):
                indexes.extend(cls.get_model_indexes(model, index, column, is_only_leaf, is_only_checked, data_match, filter_func))
                if is_only_leaf:
                    continue

            # Apply custom filter function if provided
            if filter_func and not filter_func(index):
                continue

            # Match data if a specific role and value are provided
            if data_match is not None:
                role, value = data_match
                if model.data(index, role) != value:
                    continue

            # Add the index to the list
            indexes.append(index)

        return indexes
    
    @classmethod
    def get_model_data_list(cls, model: 'QtCore.QAbstractItemModel', parent: 'QtCore.QModelIndex' = QtCore.QModelIndex(),
                            column: int = 0, is_only_leaf: bool = False, is_only_checked: bool = False,
                            data_match: Optional[Tuple['QtCore.Qt.ItemDataRole', Any]] = None,
                            filter_func: Optional[Callable[['QtCore.QModelIndex'], bool]] = None) -> List[str]:
        """Retrieve data from a QAbstractItemModel based on specified criteria.

        This function retrieves data from the model based on the provided column number.
        It optionally filters data to include only leaf nodes, nodes matching specific data,
        or nodes that pass a custom filter function.

        Args:
            model: The QAbstractItemModel to search.
            parent: The parent QModelIndex to start the search from.
            column: The column number from which to retrieve data.
            is_only_checked: If True, only data from indexes with checked state will be returned.
            is_only_leaf: True if only data from leaf node indexes should be returned; False otherwise.
            data_match: Optional tuple (role, value) to match data in the nodes.
            filter_func: Optional function that takes a QModelIndex and returns a bool
                         indicating whether the index should be included.

        Returns:
            List[str]: A list of data strings that meet the specified criteria.
        """
        indexes = cls.get_model_indexes(model, parent, column, is_only_leaf, is_only_checked, data_match, filter_func)
        return [model.data(index) for index in indexes if index.isValid()]

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
