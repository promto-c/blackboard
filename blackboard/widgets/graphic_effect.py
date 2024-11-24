# Third Party Imports
# -------------------
from qtpy import QtCore, QtGui, QtWidgets


# Class Definitions
# -----------------
class DropShadowEffect(QtWidgets.QGraphicsDropShadowEffect):
    """A configurable shadow effect for widgets.
    """

    def __init__(self, blur_radius=30, x_offset=0, y_offset=4, color=QtGui.QColor(0, 0, 0, 150), parent=None):
        """Initialize the shadow effect with specific properties.

        Args:
            blur_radius (int): The blur radius of the shadow.
            x_offset (int): The horizontal offset of the shadow.
            y_offset (int): The vertical offset of the shadow.
            color (QColor): The color of the shadow effect.
            parent (QObject): Optional parent for the effect.
        """
        super().__init__(parent, blurRadius=blur_radius, xOffset=x_offset, yOffset=y_offset, color=color)
