import sys
import os
from PyQt5 import QtWidgets, QtCore
from itertools import islice


def generate_file_paths(start_path):
    """Generates file paths in the given directory and its subdirectories.

    Args:
        start_path: A string representing the starting directory path.

    Yields:
        Full path of each file found in the directory and subdirectories.
    """
    for root, dirs, files in os.walk(start_path):
        for file in files:
            yield os.path.join(root, file)


class InfiniteScrollTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, path, batch_size=100, threshold_to_load_more=50, parent=None):
        super(InfiniteScrollTreeWidget, self).__init__(parent)
        self.batch_size = batch_size
        self.threshold_to_load_more = threshold_to_load_more

        self.path_generator = generate_file_paths(path)

        first_batch_size = self.calculate_dynamic_batch_size()
        self._load_more_data(first_batch_size)  # Initial data loading

        self.verticalScrollBar().valueChanged.connect(self._check_scroll_position)

    def calculate_dynamic_batch_size(self):
        """Estimates the number of items that can fit in the current view.

        Returns:
            int: Estimated number of items that can fit in the view.
        """
        # Add a temporary item to calculate its size
        temp_item = QtWidgets.QTreeWidgetItem(["Temporary Item"])
        self.addTopLevelItem(temp_item)
        item_height = self.visualItemRect(temp_item).height()
        self.removeItemWidget(temp_item, 0)  # Remove the temporary item

        # Calculate the visible area height
        visible_height = self.viewport().height()

        # Calculate and return the number of items that can fit in the view
        estimated_items = visible_height // item_height if item_height > 0 else 0
        
        # Adjust the batch size based on the estimate
        # You may want to add some buffer (e.g., 10% more items) to ensure the view is fully populated
        return max(estimated_items, self.batch_size)

    def _load_more_data(self, batch_size: int = None):
        """Loads more data into the tree widget based on the batch size."""
        batch_size = batch_size or self.batch_size
        items_to_load = islice(self.path_generator, self.batch_size)
        loaded_any = False
        for file_path in items_to_load:
            item = QtWidgets.QTreeWidgetItem([file_path])
            self.addTopLevelItem(item)
            loaded_any = True
        if not loaded_any:
            # No more data to load, could disable further loading if desired
            # pass
            # NOTE: test
            self.verticalScrollBar().valueChanged.disconnect(self._check_scroll_position)

    def _check_scroll_position(self, value):
        """Checks the scroll position and loads more data if the threshold is reached."""
        scroll_bar = self.verticalScrollBar()
        if value >= scroll_bar.maximum() - self.threshold_to_load_more:
            self._load_more_data()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Set the start path to the directory you want to browse
    start_path = '/'
    treeWidget = InfiniteScrollTreeWidget(start_path)
    treeWidget.show()
    sys.exit(app.exec_())
