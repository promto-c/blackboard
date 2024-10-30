from typing import Union

from qtpy import QtWidgets, QtGui, QtCore


class SectionAction(QtWidgets.QWidgetAction):

    def __init__(self, parent_menu: QtWidgets.QMenu, text: str = None, icon: QtGui.QIcon = None):
        super().__init__(parent_menu)

        self.parent_menu = parent_menu

        # Create a label widget with the specified text
        self.label = QtWidgets.QLabel(text, self.parent_menu)

        if icon:
            # NOTE: Not Implement
            ...

        # Disable the label to make it non-interactive
        self.label.setDisabled(True)

        # Set the label as its default widget
        self.setDefaultWidget(self.label)

        self.parent_menu.addAction(self)
        self.separator = self.parent_menu.addSeparator()

    def addAction(self, action: Union[QtWidgets.QAction, str]) -> QtWidgets.QAction:
        if isinstance(action, str):
            action = QtWidgets.QAction(action, self.parent_menu)
        self.parent_menu.insertAction(self.separator, action)

        return action
    
    def addMenu(self, title: str) -> QtWidgets.QMenu:

        menu = ContextMenu(title, self.parent_menu)
        self.parent_menu.insertMenu(self.separator, menu)

        return menu
    
    def addSeparator(self) -> QtWidgets.QAction:
        return self.parent_menu.insertSeparator(self.separator)

class ContextMenu(QtWidgets.QMenu):

    def __init__(self, title: str = '', parent: QtWidgets.QWidget = None):
        super().__init__(title, parent)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    def addSection(self, text: str, icon: QtGui.QIcon = None) -> 'SectionAction':
        return SectionAction(self, text, icon)

    def insert_after_action(self, target_action: QtWidgets.QAction, action_to_insert: QtWidgets.QAction):
        """Insert an action after a specific target action in the menu.
        """
        actions = self.actions()
        for index, action in enumerate(actions):
            if action != target_action:
                continue

            if index + 1 < len(actions):
                self.insertAction(actions[index + 1], action_to_insert)
            else:
                self.addAction(action_to_insert)
            break
