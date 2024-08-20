from qtpy import QtWidgets, QtCore, QtGui


class DragPixmap(QtGui.QPixmap):
    def __init__(self, items_count: int, icon: QtGui.QIcon = None, opacity: float = 0.8, badge_radius: int = 10, badge_margin: int = 0,
                 badge_color: QtGui.QColor = QtGui.QColor('red'), text_color: QtGui.QColor = QtGui.QColor('white')):
        """Initialize the DragPixmap with optional customizations for the badge.

        Args:
            items_count (int): The number of items to display on the badge.
            icon (QtGui.QIcon, optional): The icon to use for the pixmap. Defaults to the application icon.
            opacity (float, optional): The opacity of the pixmap. Defaults to 0.8.
            badge_radius (int, optional): The radius of the badge. Defaults to 10.
            badge_margin (int, optional): The margin around the badge. Defaults to 0.
            badge_color (QtGui.QColor, optional): The color of the badge background. Defaults to red.
            text_color (QtGui.QColor, optional): The color of the text on the badge. Defaults to white.
        """
        icon = icon or QtWidgets.QApplication.instance().windowIcon()

        if not icon.isNull():
            icon_pixmap = icon.pixmap(64, 64)
            if not icon_pixmap.width() or not icon_pixmap.height():
                icon_pixmap = QtGui.QPixmap(24, 24)
                icon_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        else:
            icon_pixmap = QtGui.QPixmap(24, 24)
            icon_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        # Initialize the base class with the desired pixmap size
        super().__init__(icon_pixmap.width() + badge_margin, icon_pixmap.height() + badge_margin)
        self.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(self)
        painter.setOpacity(opacity)
        painter.drawPixmap(QtCore.QPoint(0, badge_margin), icon_pixmap)

        # Draw badge logic
        items_count_text = "99+" if items_count > 99 else str(items_count)

        # Calculate the optimal badge radius and diameter
        metrics = QtGui.QFontMetrics(painter.font())
        text_width = metrics.width(items_count_text)
        badge_radius = max(badge_radius, int(text_width / 2))
        badge_diameter = badge_radius * 2

        # Apply custom badge color and text color
        painter.setBrush(badge_color)
        painter.setPen(text_color)
        painter.drawEllipse(self.width() - badge_diameter - 2, 0, badge_diameter, badge_diameter)
        painter.drawText(self.width() - badge_diameter - 2, 0, badge_diameter, badge_diameter, 
                         QtCore.Qt.AlignmentFlag.AlignCenter, items_count_text)

        painter.end()
