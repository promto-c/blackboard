from PyQt5 import QtWidgets, QtGui, QtCore


class HoverableWidgetExtension(QtCore.QObject):
    """An extension to add a hoverable widget to QTreeWidget items.

    This extension allows you to add any widget (e.g., buttons, labels) to the right side of a QTreeWidget item
    when the mouse hovers over it. The widget is customizable, and the current interacting item can be retrieved.

    Attributes:
        tree_widget (QtWidgets.QTreeWidget): The tree widget to which this extension is applied.
        hovered_item (QtWidgets.QTreeWidgetItem): The item currently hovered by the mouse.
        hover_widget (QtWidgets.QWidget): The widget that appears on hover.
    """

    def __init__(self, tree_widget: QtWidgets.QTreeWidget, hover_widget: QtWidgets.QWidget):
        """Initializes the HoverableWidgetExtension with the specified tree widget and hover widget.

        Args:
            tree_widget (QtWidgets.QTreeWidget): The tree widget to enhance with a hoverable widget.
            hover_widget (QtWidgets.QWidget): The widget to display when hovering over an item.
        """
        super().__init__(tree_widget)
        self.tree_widget = tree_widget
        self.hover_widget = hover_widget
        self.tree_widget.setMouseTracking(True)
        self.tree_widget.viewport().installEventFilter(self)

        self.hovered_item = None
        self.hover_widget.setParent(self.tree_widget)
        self.hover_widget.hide()

    def eventFilter(self, source: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Filters events for the tree widget's viewport to handle mouse movements and leave events.

        Args:
            source (QtCore.QObject): The source object of the event.
            event (QtCore.QEvent): The event to be filtered.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type() == QtCore.QEvent.Type.MouseMove and source is self.tree_widget.viewport():
            self.handle_mouse_move(event)
        elif event.type() == QtCore.QEvent.Type.Leave and source is self.tree_widget.viewport():
            self.handle_leave_event(event)
        return super().eventFilter(source, event)

    def handle_mouse_move(self, event: QtGui.QMouseEvent) -> None:
        """Handles the mouse move event to show the hover widget on the hovered item.

        Args:
            event (QtGui.QMouseEvent): The mouse move event.
        """
        item = self.tree_widget.itemAt(event.pos())
        if item == self.hovered_item:
            return

        self.hover_widget.hide()
        if item:
            self.show_hover_widget(item)
        self.hovered_item = item

    def handle_leave_event(self, event: QtCore.QEvent) -> None:
        """Handles the leave event to hide the hover widget when the mouse leaves the tree widget.

        Args:
            event (QtCore.QEvent): The leave event.
        """
        # Ensure that the mouse isn't over the hover widget before hiding it
        mouse_pos = self.tree_widget.mapFromGlobal(QtGui.QCursor.pos())
        if not self.hover_widget.geometry().contains(mouse_pos):
            self.hover_widget.hide()
            self.hovered_item = None

    def show_hover_widget(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Shows the hover widget at the right edge of the hovered item.

        Args:
            item (QtWidgets.QTreeWidgetItem): The tree widget item currently hovered by the mouse.
        """
        item_rect = self.tree_widget.visualItemRect(item)
        self.hover_widget.move(item_rect.right() - self.hover_widget.width(), item_rect.top())
        self.hover_widget.show()

    def get_current_hovered_item(self) -> QtWidgets.QTreeWidgetItem:
        """Returns the item currently being hovered over by the mouse.

        Returns:
            QtWidgets.QTreeWidgetItem: The currently hovered tree widget item.
        """
        return self.hovered_item


if __name__ == "__main__":
    import sys

    def handle_button_click():
        item = extension.get_current_hovered_item()
        if item:
            print(f"Item clicked: {item.text(0)}")

    app = QtWidgets.QApplication(sys.argv)

    # Create a QTreeWidget and apply the extension
    tree_widget = QtWidgets.QTreeWidget()
    tree_widget.setColumnCount(1)
    tree_widget.setHeaderHidden(True)

    # Add some items to the tree widget
    for i in range(5):
        item = QtWidgets.QTreeWidgetItem(tree_widget)
        item.setText(0, f"Item {i + 1}")

    # Create a custom widget (e.g., a button) to be shown on hover
    hover_button = QtWidgets.QPushButton("X")
    # hover_button.setStyleSheet("background-color: none; border: none;")
    hover_button.setFixedSize(20, 20)

    # Apply the HoverableWidgetExtension
    extension = HoverableWidgetExtension(tree_widget, hover_button)
    hover_button.clicked.connect(handle_button_click)

    tree_widget.show()
    sys.exit(app.exec_())
