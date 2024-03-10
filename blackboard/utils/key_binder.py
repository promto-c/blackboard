# Type Checking Imports
# ---------------------
from typing import Callable, Union, List, Dict

# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class KeyBinder(QtWidgets.QWidget):
    shortcuts: Dict[str, QtWidgets.QShortcut] = {}
    focus_widget: QtWidgets.QWidget = None

    @classmethod
    def bind_key(cls, widget, key_sequence: Union[str, QtGui.QKeySequence], function: Callable, 
                 context: QtCore.Qt.ShortcutContext = QtCore.Qt.ShortcutContext.WidgetShortcut):
        """Binds a given key sequence to a function.
        
        Args:
            key_sequence (Union[str, QtGui.QKeySequence]): The key sequence as a string or QKeySequence, e.g., "Ctrl+F".
            function (Callable): The function to be called when the key sequence is activated.
            context (QtCore.Qt.ShortcutContext, optional): The context in which the shortcut is active.
        """
        # Create a shortcut with the specified key sequence
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key_sequence), widget)
        shortcut.setContext(context)
        # Connect the activated signal of the shortcut to the given function
        shortcut.activated.connect(function)

        cls.shortcuts[str(key_sequence)] = shortcut

    @classmethod
    def unbind_key(cls, key_sequence: Union[str, QtGui.QKeySequence]):
        """Removes a binding for a given key sequence."""
        key = str(key_sequence)
        if key in cls.shortcuts:
            shortcut = cls.shortcuts[key]
            shortcut.activated.disconnect()
            del cls.shortcuts[key]

    @classmethod
    def disable_key(cls, key_sequence: Union[str, QtGui.QKeySequence]):
        """Disables a binding without removing it completely."""
        key = str(key_sequence)
        if key in cls.shortcuts:
            cls.shortcuts[key].setEnabled(False)

    @classmethod
    def enable_key(cls, key_sequence: Union[str, QtGui.QKeySequence]):
        """Enables a previously disabled binding."""
        key = str(key_sequence)
        if key in cls.shortcuts:
            cls.shortcuts[key].setEnabled(True)

    @classmethod
    def list_bound_keys(cls) -> List[str]:
        """Lists all key sequences that are currently bound."""
        return list(cls.shortcuts.keys())

    @classmethod
    def eventFilter(cls, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Custom event filter to track focus changes."""
        if event.type() == QtCore.QEvent.Type.FocusIn and isinstance(obj, QtWidgets.QWidget):
            cls.focus_widget = obj
        elif event.type() == QtCore.QEvent.Type.FocusOut and cls.focus_widget == obj:
            cls.focus_widget = None

        return super(KeyBinder, cls).eventFilter(obj, event)
