# Type Checking Imports
# ---------------------
from typing import Any, Callable, List, Optional, Tuple, Dict, Iterable

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
        """Get the indexes of the shown columns in the tree widget.

        Args:
            tree_widget (QtWidgets.QTreeWidget): The tree widget to get shown column indexes from.

        Returns:
            List[int]: A list of indexes for the shown columns.
        """
        return [column_index for column_index in range(tree_widget.columnCount()) if not tree_widget.isColumnHidden(column_index)]

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

    @classmethod
    def fit_column_in_view(cls, tree_widget: 'QtWidgets.QTreeWidget') -> None:
        """Adjust the width of all columns to fit the entire view.
    
            This method resizes columns so that their sum is equal to the width of the view minus the width of the vertical scroll bar. 
            It starts by reducing the width of the column with the largest width by 10% until all columns fit within the expected width.
        """
        # Resize all columns to fit their contents
        cls.resize_all_to_contents(tree_widget)
        
        # Get the expected width of the columns (the width of the view minus the width of the scroll bar)
        expect_column_width = tree_widget.size().width() - tree_widget.verticalScrollBar().width()
        # Calculate the sum of the current column widths
        column_width_sum = sum(tree_widget.columnWidth(column) for column in range(tree_widget.columnCount()))
        
        # Loop until all columns fit within the expected width
        while column_width_sum > expect_column_width:
            # Find the column with the largest width
            largest_column = max(range(tree_widget.columnCount()), key=lambda x: tree_widget.columnWidth(x))
            # Reduce the width of the largest column by 10%
            new_width = max(tree_widget.columnWidth(largest_column) - expect_column_width // 10, 0)
            tree_widget.setColumnWidth(largest_column, new_width)
            # Update the sum of the column widths
            column_width_sum -= tree_widget.columnWidth(largest_column) - new_width

    @staticmethod
    def resize_all_to_contents(tree_widget: 'QtWidgets.QTreeWidget') -> None:
        """Resize all columns in the object to fit their contents.
        """
        # Iterate through all columns
        for column_index in range(tree_widget.columnCount()):  
            # Resize the column to fit its contents
            tree_widget.resizeColumnToContents(column_index) 

    @staticmethod
    def get_item_data_dict(tree_widget: 'QtWidgets.QTreeWidget', item: 'QtWidgets.QTreeWidgetItem') -> Dict[str, Optional[str]]:
        """Retrieve data from a QTreeWidgetItem and return it as a dictionary.

        Args:
            tree_widget (QtWidgets.QTreeWidget): The tree widget containing the item.
            item (QtWidgets.QTreeWidgetItem): The item to extract data from.

        Returns:
            Dict[str, Optional[str]]: A dictionary where keys are column headers and values are the data in the corresponding columns.
        """
        data_dict = {}
        
        # Get the column headers from the tree widget
        headers = [tree_widget.headerItem().text(column) for column in range(tree_widget.columnCount())]
        
        # Assuming you want to get data from all columns
        for column in range(item.columnCount()):
            # Retrieve the text from each column of the item using the header as the key
            data_dict[headers[column]] = item.text(column)
        
        return data_dict

    @classmethod
    def get_all_item_data_dicts(cls, tree_widget: 'QtWidgets.QTreeWidget', parent_item: Optional['QtWidgets.QTreeWidgetItem'] = None) -> Dict[str, Dict[str, Optional[str]]]:
        """Retrieve data from all items in the QTreeWidget as a dictionary of dictionaries.

        Args:
            tree_widget (QtWidgets.QTreeWidget): The tree widget to traverse.
            parent_item (Optional[QtWidgets.QTreeWidgetItem]): The parent item to start traversal from. If None, starts from the root.

        Returns:
            Dict[str, Dict[str, Optional[str]]]: A dictionary where keys are item texts and values are dictionaries containing data for each column.
        """
        parent_item = parent_item or tree_widget.invisibleRootItem()
        all_data = {}

        def traverse_item(item: 'QtWidgets.QTreeWidgetItem'):
            item_data = cls.get_item_data_dict(tree_widget, item)
            all_data[item.text(0)] = item_data  # Using the text from the first column as the key

            for row in range(item.childCount()):
                child_item = item.child(row)
                traverse_item(child_item)

        traverse_item(parent_item)
        return all_data

class TreeItemUtil:

    @staticmethod
    def get_model_indexes(tree_items: Iterable[QtWidgets.QTreeWidgetItem], only_shown: bool = True, column_index: Optional[int] = None) -> List[QtCore.QModelIndex]:
        """Get the model index for each column in the tree widget.

        Args:
            tree_items (List[QtWidgets.QTreeWidgetItem]): The tree widget items to get model indexes for.
            only_shown (bool): If True, only get indexes for shown columns. If False, get indexes for all columns.
            column_index (Optional[int]): If provided, get indexes for this specific column only.

        Returns:
            List[QtCore.QModelIndex]: A list of model indexes for each column in the tree widget.
        """
        if not tree_items:
            return []

        _reference_item = tree_items[0] if isinstance(tree_items, list) else next(iter(tree_items))
        tree_widget = _reference_item.treeWidget()
        
        # Determine the list of column indices to process
        if column_index is not None:
            column_indexes = [column_index]
        else:
            column_indexes = (
                only_shown and TreeUtil.get_shown_column_indexes(tree_widget) or 
                range(tree_widget.columnCount())
            )

        model_indexes = []
        for column_index in column_indexes:
            # Get the model index for each column
            model_indexes.extend([
                tree_widget.indexFromItem(tree_item, column_index)
                for tree_item in tree_items
            ])

        # Return the list of model indexes
        return model_indexes
