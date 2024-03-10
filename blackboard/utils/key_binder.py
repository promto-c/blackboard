# Type Checking Imports
# ---------------------
from typing import Callable, Union, List, Dict

# Third Party Imports
# -------------------
from PyQt5 import QtCore, QtGui, QtWidgets

# Local Imports
# -------------
from blackboard.utils.event_filter import FocusEventFilter


# Class Definitions
# -----------------
# TODO: Add supported for any QtCore.Qt.ShortcutContext
class Shortcut(QtWidgets.QShortcut):
    def __init__(self, key_sequence: Union[str, QtGui.QKeySequence], parent_widget, 
                 callback: Callable, context:  QtCore.Qt.ShortcutContext = QtCore.Qt.ShortcutContext.WindowShortcut, 
                 target_widget=None):
        super().__init__(QtGui.QKeySequence(key_sequence), parent_widget)
        self.setContext(context)

        self.target_widget = target_widget or parent_widget
        self.callback = callback

        # TODO: Check if not wrapped by ScalableView
        # # Connect the activated signal of the shortcut to the given function
        # self.activated.connect(self.callback)

        QtWidgets.QApplication.instance().installEventFilter(KeyBinder.focus_event_filter)
        self.activated.connect(self.check_focus_and_activate)

    def check_focus_and_activate(self):
        if FocusEventFilter.focus_widget == self.target_widget:
            self.callback()

class KeyBinder(QtWidgets.QWidget):
    shortcuts: Dict[str, Shortcut] = {}

    # NOTE: Use FocusEventFilter to handle focused_widget instead of original focusWidget()
    #       because it will get only ScalableView that wrapped all inside widgets
    focus_event_filter = FocusEventFilter()

    @classmethod
    def bind_key(cls, widget, key_sequence: Union[str, QtGui.QKeySequence], callback: Callable, 
                 context: QtCore.Qt.ShortcutContext = QtCore.Qt.ShortcutContext.WindowShortcut) -> Shortcut:
        """Binds a given key sequence to a function.
        
        Args:
            key_sequence (Union[str, QtGui.QKeySequence]): The key sequence as a string or QKeySequence, e.g., "Ctrl+F".
            callback (Callable): The function to be called when the key sequence is activated.
            context (QtCore.Qt.ShortcutContext, optional): The context in which the shortcut is active.
        """
        # Create a shortcut with the specified key sequence
        shortcut = Shortcut(key_sequence, widget, callback, context=context)
        # Store the shortcut object
        cls.shortcuts[str(key_sequence)] = shortcut

        return shortcut

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
    def get_bound_keys(cls) -> List[str]:
        """Lists all key sequences that are currently bound."""
        return list(cls.shortcuts.keys())
    
    @classmethod
    def get_bound_keys_detail(cls):
        """Returns detailed information about all bound keys."""
        details = []
        for key, shortcut in cls.shortcuts.items():
            detail = {
                'key_sequence': key,
                'callback': shortcut.callback.__name__,
                'context': shortcut.context(),
                'target_widget': shortcut.target_widget
            }
            details.append(detail)

        return details