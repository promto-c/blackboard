# Type Checking Imports
# ---------------------
from typing import Optional

# Third Party Imports
# -------------------
from qtpy import QtWidgets, QtCore, QtGui


# Class Definitions
# -----------------
class DragPixmap(QtGui.QPixmap):

    # Initialization and Setup
    # ------------------------
    def __init__(self, items_count: int, icon: Optional[QtGui.QIcon] = None, opacity: float = 0.8, badge_radius: int = 10, badge_margin: int = 0,
                 badge_color: QtGui.QColor = QtGui.QColor('red'), text_color: QtGui.QColor = QtGui.QColor('white')):
        """Initialize a pixmap with optional customization for an icon, opacity, and a badge displaying an item count.

        Args:
            items_count (int): Number of items to display on the badge.
            icon (Optional[QtGui.QIcon]): Icon for the pixmap. Defaults to the application icon.
            opacity (float): Opacity level of the pixmap. Defaults to 0.8.
            badge_radius (int): Radius of the badge. Defaults to 10.
            badge_margin (int): Margin around the badge. Defaults to 0.
            badge_color (QtGui.QColor): Background color of the badge. Defaults to red.
            text_color (QtGui.QColor): Color of the text on the badge. Defaults to white.
        """
        # Use the provided icon or fallback to the application's window icon
        icon = icon or QtWidgets.QApplication.instance().windowIcon()

        if icon.isNull():
            # Create a transparent fallback pixmap when no valid icon is provided
            icon_pixmap = QtGui.QPixmap(24, 24)
            icon_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        else:
            # Generate the icon pixmap with default size and ensure it is not empty
            icon_pixmap = icon.pixmap(64, 64)
            if not icon_pixmap.width() or not icon_pixmap.height():
                icon_pixmap = QtGui.QPixmap(24, 24)
                icon_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        # Initialize the base class with the desired pixmap size
        super().__init__(icon_pixmap.width() + badge_margin, icon_pixmap.height() + badge_margin)
        self.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(self)
        painter.setOpacity(opacity)
        painter.drawPixmap(QtCore.QPoint(0, badge_margin), icon_pixmap)

        # Determine the badge text, capped at "99+"
        items_count_text = "99+" if items_count > 99 else str(items_count)

        # Calculate the optimal badge radius and diameter based on text width
        metrics = QtGui.QFontMetrics(painter.font())
        text_width = metrics.width(items_count_text)
        badge_radius = max(badge_radius, int(text_width / 2))
        badge_diameter = badge_radius * 2

        # Draw the badge with the specified colors
        painter.setBrush(badge_color)
        painter.setPen(text_color)
        painter.drawEllipse(self.width() - badge_diameter - 2, 0, badge_diameter, badge_diameter)
        painter.drawText(self.width() - badge_diameter - 2, 0, badge_diameter, badge_diameter, 
                         QtCore.Qt.AlignmentFlag.AlignCenter, items_count_text)

        painter.end()
