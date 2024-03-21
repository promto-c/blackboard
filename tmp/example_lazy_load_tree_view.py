import sys
from PyQt5 import QtGui, QtWidgets, QtCore


class InfiniteScrollModel(QtGui.QStandardItemModel):
    def __init__(self, totalItems=50000, batchSize=100, parent=None):
        super().__init__(parent)
        self.totalItems = totalItems
        self.batchSize = batchSize
        self.loadedItems = 0
        self.loading = False

        # Initially load placeholders for all items
        for _ in range(self.totalItems):
            item = QtGui.QStandardItem('Loading...')
            self.appendRow(item)

    def maybeLoadMoreData(self, start, end):
        if self.loading or self.loadedItems >= self.totalItems:
            return

        # Check if we need to load data based on the visibleIndex
        if end + self.batchSize > self.loadedItems:
            self.loadMoreData(start)

    def loadMoreData(self, start):
        self.loading = True
        endIndex = min(start + self.batchSize, self.totalItems)
        
        # Simulate loading data
        for i in range(start, endIndex):
            item = self.item(i)
            item.setText(f'Item {i}')

        self.loadedItems = endIndex
        self.loading = False

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.treeView = QtWidgets.QTreeView(self)
        self.model = InfiniteScrollModel()
        self.treeView.setModel(self.model)
        
        # Use a timer to periodically check which items are visible
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.checkVisibleItems)
        self.timer.start(100)  # Check every 100 milliseconds

        self.setCentralWidget(self.treeView)
        self.resize(800, 600)
        self.setWindowTitle('Infinite Scrolling QTreeView with Placeholder Items')

    def checkVisibleItems(self):
        # Get the index of the item at the bottom of the view
        topIndex = self.treeView.indexAt(self.treeView.viewport().rect().topLeft())
        bottomLeft = self.treeView.viewport().rect().bottomLeft()
        bottomLeft.setY(bottomLeft.y() - 30)  # Move up slightly from the absolute bottom
        indexAtBottom = self.treeView.indexAt(bottomLeft)

        if indexAtBottom.isValid():
            self.model.maybeLoadMoreData(topIndex.row(), indexAtBottom.row())

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())