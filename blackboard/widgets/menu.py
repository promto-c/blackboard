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
        self.label.setStyleSheet('''
            color: #999;
            padding: 6px;
        ''')

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

        menu = QtWidgets.QMenu(title, self.parent_menu)
        self.parent_menu.insertMenu(self.separator, menu)

        return menu
    
    def addSeparator(self) -> QtWidgets.QAction:
        return self.parent_menu.addSeparator()

class ContextMenu(QtWidgets.QMenu):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    def addSection(self, text: str, icon: QtGui.QIcon = None) -> 'SectionAction':
        return SectionAction(self, text, icon)

