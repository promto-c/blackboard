from PyQt5.QtWidgets import QPushButton, QApplication, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtProperty, pyqtSignal, QEasingCurve
from PyQt5.QtGui import QColor


from tablerqicon import TablerQIcon

# NOTE: Icon for fetch all
# self.setIcon(TablerQIcon.arrow_bar_to_down)

class AnimatedButton(QPushButton):
    entered = pyqtSignal()
    leaved = pyqtSignal()
    def __init__(self, text, icon, parent=None, hover_text=None, hover_icon=None, hover_color = QColor(Qt.GlobalColor.blue)):
        super().__init__(text, parent)
        # self.setMouseTracking(True)
        self.default_icon = icon
        self.setIcon(icon)
        self.hover_icon = hover_icon or icon
        self.defaultText = text
        self.hover_text = hover_text or text
        self.animation_duration = 100  # Milliseconds
        self.default_color = self.palette().color(self.backgroundRole())
        self.hover_color = hover_color
        self._color = self.default_color  # Initialize the color property
        self.color_anim = QPropertyAnimation(self, b'color')
        self.color_anim.setDuration(self.animation_duration)
        self._width = self.width()
        self.width_anim = QPropertyAnimation(self, b"anim_width", self)
        self.width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.width_anim.setDuration(self.animation_duration)  # Animation duration in milliseconds
        self.setProperty('widget-style', 'round')
        self.setStyleSheet('text-align: center;')

        self.style().unpolish(self)  # Refresh the style
        self.style().polish(self)

    def collapse(self):
        self.animate_width(24)
        self.setText('')

    def expand(self):
        self.animate_width(200)
        self.setText(self.defaultText)

    @pyqtProperty(int)
    def anim_width(self):
        return self._width

    @anim_width.setter
    def anim_width(self, width):
        self._width = width
        self.setFixedWidth(self._width)

    def animate_width(self, width):
        self.width_anim.stop()  # Stop any ongoing animation
        self.width_anim.setEndValue(width)
        self.width_anim.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.entered.emit()
        self.color_anim.setStartValue(self.default_color)
        self.color_anim.setEndValue(self.hover_color)
        self.setText(self.hover_text)
        self.setIcon(self.hover_icon)
        
        self.color_anim.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.leaved.emit()
        self.color_anim.setStartValue(self.hover_color)
        self.color_anim.setEndValue(self.default_color)
        self.setText(self.defaultText)
        self.setIcon(self.default_icon)
        self.color_anim.start()

    @pyqtProperty(QColor)
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        # Format the color to a string
        self.setStyleSheet(f"text-align: center;background-color: {color.name(QColor.HexRgb)};")


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 400, 100)
        self.layout = QHBoxLayout(self)

        # Initialize the "Fetch More" button
        self.fetchMoreButton = AnimatedButton('Fetch More', TablerQIcon.chevron_down, self, hover_icon=TablerQIcon.chevrons_down, hover_color=QColor("#167"))
        # Initialize the "Fetch All" button
        self.fetchAllButton = AnimatedButton('', TablerQIcon.arrow_down_to_arc, self, 'Fetch All', hover_icon=TablerQIcon.arrow_bar_to_down, hover_color=QColor("#187"))

        self.layout.addWidget(self.fetchMoreButton)
        self.layout.addWidget(self.fetchAllButton)

        # Connect the hover signal from fetchMoreButton to show fetchAllButton
        self.fetchAllButton.entered.connect(self.showFetchAllButton)
        self.fetchAllButton.leaved.connect(self.hideFetchAllButton)

        self.fetchMoreButton.setFixedHeight(24)
        self.fetchAllButton.setFixedHeight(24)
        self.fetchAllButton.setFixedWidth(24)

    def showFetchAllButton(self):
        # Show the "Fetch All" button when mouse hovers over "Fetch More"
        self.fetchAllButton.expand()
        self.fetchMoreButton.collapse()

    def hideFetchAllButton(self):
        # Hide the "Fetch All" button when mouse leaves "Fetch More"
        self.fetchAllButton.collapse()
        self.fetchMoreButton.expand()


if __name__ == "__main__":
    import sys
    import blackboard as bb
    app = QApplication(sys.argv)
    bb.theme.set_theme(app, 'dark')
    mainWin = MainWidget()
    mainWin.show()
    sys.exit(app.exec_())
