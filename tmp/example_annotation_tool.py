import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon
import scipy
import numpy as np
from enum import Enum


class ScreenCaptureArea(QtWidgets.QWidget):
    closed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setWindowState(QtCore.Qt.WindowState.WindowFullScreen)
        self.setWindowOpacity(0.3)
        self.rubber_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Shape.Rectangle, self)
        self.origin: QtCore.QPoint = QtCore.QPoint()
        self.selected_rect: QtCore.QRect = QtCore.QRect()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.rubber_band.isVisible():
            self.rubber_band.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.selected_rect = self.rubber_band.geometry()
            self.rubber_band.hide()
            self.close()

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.closed.emit()
        super().closeEvent(event)

    def get_selected_rect(self) -> QtCore.QRect:
        return self.selected_rect


class DrawingObject:
    def __init__(self, points, color, width):
        self.points = points
        self.color = color
        self.width = width


class ToolMode(Enum):
    NONE = 0
    FREEHAND = 1
    RECTANGLE = 2
    ERASER = 3
    TEXT = 4


class DrawingLabel(QtWidgets.QWidget):
    # Define the signal
    drawing_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: QtGui.QPixmap = QtGui.QPixmap()
        self.last_point: QtCore.QPoint = QtCore.QPoint()
        self.current_tool: ToolMode = ToolMode.NONE
        self.rectangle_start: QtCore.QPoint = QtCore.QPoint()
        self.rectangle_end: QtCore.QPoint = QtCore.QPoint()
        self.rectangles: list[QtCore.QRect] = []
        self.control_points: list[QtCore.QPoint] = []
        self.drawing_objects: list[DrawingObject] = []
        self.text_items: list[tuple[QtCore.QPoint, str]] = []
        self.text_editor = None
        self.text_font = QtGui.QFont('Arial', 12)
        self.pen_color: QtGui.QColor = QtGui.QColor(QtCore.Qt.GlobalColor.red)
        self.pen_width: int = 3
        self.is_dragging: bool = False
        self.start_drag_position: QtCore.QPoint = QtCore.QPoint()
        self.initial_pen_width: int = self.pen_width
        self.cursor_visible: bool = False
        self.text_color: QtGui.QColor = QtGui.QColor(0, 0, 0)  # Text color

        self.setMouseTracking(True)  # Enable mouse tracking to get mouseMoveEvent even when no button is pressed

    def set_pixmap(self, pixmap: QtGui.QPixmap):
        self.image = pixmap.copy()
        self.setFixedSize(self.image.size())
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        if not self.image.isNull():
            self._draw_background(painter)
            self._draw_rectangles(painter)
            self._draw_drawing_objects(painter)
            self._draw_text_items(painter)

        # Draw the preview cursor if it's visible
        if self.cursor_visible and self.current_tool == ToolMode.FREEHAND:
            painter.setPen(QtGui.QPen(self.pen_color, 1, QtCore.Qt.PenStyle.DashLine))
            cursor_size = self.pen_width
            cursor_center = self.start_drag_position if self.is_dragging else self.last_point
            cursor_rect = QtCore.QRect(cursor_center.x() - cursor_size // 2,
                                       cursor_center.y() - cursor_size // 2,
                                       cursor_size, cursor_size)
            painter.drawEllipse(cursor_rect)

    def _draw_background(self, painter: QtGui.QPainter):
        painter.drawPixmap(self.rect(), self.image)

    def _draw_rectangles(self, painter: QtGui.QPainter):
        pen = QtGui.QPen(self.pen_color, self.pen_width, QtCore.Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        for rect in self.rectangles:
            painter.drawRect(rect)
        if self.current_tool == ToolMode.RECTANGLE:
            painter.drawRect(QtCore.QRect(self.rectangle_start, self.rectangle_end))

    def _draw_drawing_objects(self, painter: QtGui.QPainter):
        for obj in self.drawing_objects:
            pen = QtGui.QPen(obj.color, obj.width, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap, QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            for i in range(1, len(obj.points)):
                start_point = obj.points[i - 1]
                end_point = obj.points[i]
                painter.drawLine(start_point, end_point)

    def _draw_text_items(self, painter: QtGui.QPainter):
        painter.setPen(self.text_color)
        for point, text in self.text_items:
            painter.drawText(point, text)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and not self.image.isNull():
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                # Start brush size adjustment
                self.is_dragging = True
                self.start_drag_position = event.pos()
                self.initial_pen_width = self.pen_width  # Store the initial brush size
            else:
                if self.current_tool == ToolMode.RECTANGLE:
                    self.rectangle_start = event.pos()
                    self.rectangle_end = self.rectangle_start
                elif self.current_tool == ToolMode.ERASER:
                    self.erase_drawing(event.pos())
                elif self.current_tool == ToolMode.FREEHAND:
                    self.last_point = event.pos()
                    self.control_points = [event.pos()]
                elif self.current_tool == ToolMode.TEXT:
                    self.add_text(event.pos())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self.last_point = event.pos()  # Update the last point for cursor preview

        if self.is_dragging:
            # Adjust brush size based on horizontal drag distance from the start position
            delta_x = event.pos().x() - self.start_drag_position.x()
            new_width = max(1, self.initial_pen_width + delta_x)
            self.pen_width = new_width
            self.update()  # Refresh to update the preview cursor
        elif self.current_tool == ToolMode.FREEHAND and (event.buttons() & QtCore.Qt.MouseButton.LeftButton) and not self.image.isNull():
            painter = QtGui.QPainter(self.image)
            pen = QtGui.QPen(self.pen_color, self.pen_width, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap, QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.control_points.append(event.pos())
            self.update()
        else:
            self.update()  # Ensure the cursor preview is updated when moving

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False  # End brush size adjustment
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.current_tool == ToolMode.RECTANGLE:
                self.rectangles.append(QtCore.QRect(self.rectangle_start, self.rectangle_end))
            elif self.current_tool == ToolMode.FREEHAND:
                self.smooth_drawn_line()

            # Emit the signal when the drawing changes
            self.drawing_changed.emit()
        self.update()

    def enterEvent(self, event: QtCore.QEvent):
        self.cursor_visible = True
        self.update()

    def leaveEvent(self, event: QtCore.QEvent):
        self.cursor_visible = False
        self.update()

    def erase_drawing(self, point: QtCore.QPoint):
        # Find and remove the drawing object closest to the given point
        for obj in self.drawing_objects:
            for pt in obj.points:
                if (pt - point).manhattanLength() < 10:  # Threshold to detect proximity
                    self.drawing_objects.remove(obj)
                    self.drawing_changed.emit()  # Emit the signal after erasing
                    self.update()
                    return

    def smooth_drawn_line(self):
        if len(self.control_points) < 4:  # Need at least 4 points for a cubic B-spline
            return

        # Convert control points to numpy array
        points = np.array([(pt.x(), pt.y()) for pt in self.control_points], dtype=float)

        # Generate B-spline representation
        tck, u = scipy.interpolate.splprep([points[:, 0], points[:, 1]], s=len(points) * 5)
        u_fine = np.linspace(0, 1, len(points) * 10)
        x_fine, y_fine = scipy.interpolate.splev(u_fine, tck)

        # Store the smoothed line as a DrawingObject
        smooth_points = [QtCore.QPointF(x, y) for x, y in zip(x_fine, y_fine)]
        self.drawing_objects.append(DrawingObject(smooth_points, self.pen_color, self.pen_width))

        self.update()

    def add_text(self, position: QtCore.QPoint):
        if hasattr(self, 'text_editor') and self.text_editor is not None:
            # Ignore new clicks if a text editor is already active
            return

        # Create a QTextEdit for inline text input
        self.text_editor = QtWidgets.QTextEdit(self)
        self.text_editor.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.text_editor.move(position)
        self.text_editor.setStyleSheet("background: transparent; color: {};".format(self.text_color.name()))
        self.text_editor.setFont(self.text_font)
        self.text_editor.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_editor.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_editor.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.text_editor.setFixedSize(200, 50)  # Initial size, can be adjusted
        self.text_editor.show()
        self.text_editor.setFocus()

        # Connect signals to handle when editing is finished
        self.text_editor.focusOutEvent = self.finish_text_editing
        self.text_editor.keyPressEvent = self.text_editor_key_press_event
        self.text_editor.textChanged.connect(self.adjust_text_editor_size)

    def text_editor_key_press_event(self, event):
        if event.key() == QtCore.Qt.Key.Key_Return and not (event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier):
            # Commit text on Enter (without Shift)
            self.commit_text()
        else:
            # Allow default behavior (including Shift+Enter for new lines)
            QtWidgets.QTextEdit.keyPressEvent(self.text_editor, event)

    def finish_text_editing(self, event):
        # Commit text when focus is lost
        self.commit_text()
        if self.text_editor is not None:
            self.text_editor.focusOutEvent(event)

    def commit_text(self):
        if self.text_editor:
            text = self.text_editor.toPlainText()
            if text.strip():
                position = self.text_editor.pos()
                # Store the text and position
                self.text_items.append((position, text))
            # Remove the text editor
            self.text_editor.deleteLater()
            self.text_editor = None
            self.update()

    def adjust_text_editor_size(self):
        doc = self.text_editor.document()
        doc.setTextWidth(200)  # Set a maximum width if desired
        height = doc.size().height() + 10  # Add some padding
        self.text_editor.setFixedHeight(height)

    def _draw_text_items(self, painter: QtGui.QPainter):
        painter.setPen(QtGui.QPen(self.text_color))
        painter.setFont(self.text_font)
        for point, text in self.text_items:
            # Support multi-line text
            rect = QtCore.QRectF(point, QtCore.QSizeF(self.width() - point.x(), self.height() - point.y()))
            painter.drawText(rect, text)

class FloatingActionButton(QtWidgets.QToolButton):
    def __init__(self, icon, tooltip_text, parent=None):
        super().__init__(parent)
        self.setIcon(icon)
        self.setToolTip(tooltip_text)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.setIconSize(QtCore.QSize(40, 40))
        self.setStyleSheet('''
            QToolButton {
                border-radius: 20px;
                background-color: #888;
                color: white;
            }
            QToolButton:hover {
                background-color: #aaa;
            }
            QToolButton:pressed {
                background-color: #666;
            }
        ''')
        self.setFixedSize(50, 50)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))


class ScreenshotWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Floating Action Button Example")
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: #444; border-radius: 30;")
        self.setWindowOpacity(0.8)

        # Create an opacity animation for visual effects
        self._opacity_animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self._opacity_animation.setDuration(200)

        self.tmp_layout = QtWidgets.QHBoxLayout(self)
        self.widget = QtWidgets.QWidget(self)
        self.widget.setWindowOpacity(0.8)
        self.tmp_layout.addWidget(self.widget)

        # Layout to arrange the floating buttons horizontally
        self.fab_layout = QtWidgets.QHBoxLayout(self.widget)
        self.fab_layout.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.fab_layout.setSpacing(10)

        self.tabler_qicon = TablerQIcon(color=QtGui.QColor(255, 255, 255))

        # Add grip_vertical button for drag area
        self.grip_vertical_btn = FloatingActionButton(TablerQIcon(color=QtGui.QColor(255, 255, 255), opacity=0.6).grip_vertical, "Drag Area")
        self.grip_vertical_btn.setStyleSheet('''
            QToolButton {
                background-color: transparent;
            }
        ''')
        self.fab_layout.addWidget(self.grip_vertical_btn)
        self.grip_vertical_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))

        # Add screen_share button for screenshot whole screen
        self.screen_share_btn = FloatingActionButton(self.tabler_qicon.screen_share, "Screenshot Whole Screen")
        self.fab_layout.addWidget(self.screen_share_btn)

        # Add screenshot button for grab from screen shot
        self.screenshot_btn = FloatingActionButton(self.tabler_qicon.screenshot, "Grab Screenshot")
        self.fab_layout.addWidget(self.screenshot_btn)

        # Add close button to close the window
        self.close_btn = FloatingActionButton(self.tabler_qicon.x, "Close")
        self.close_btn.setStyleSheet('''
            QToolButton {
                border-radius: 20px;
                background-color: #888;
            }
            QToolButton:hover {
                background-color: #F66;
            }
            QToolButton:pressed {
                background-color: #C44;
            }
        ''')
        self.fab_layout.addWidget(self.close_btn)
        self.close_btn.clicked.connect(self.close)

        # Initialize dragging variables
        self.drag_start_position = None

        # Install event filter
        self.grip_vertical_btn.installEventFilter(self)

        # Connect buttons to annotation mode
        self.screen_share_btn.clicked.connect(self.take_screenshot)
        self.screenshot_btn.clicked.connect(self.grab_screen_area)

    def enterEvent(self, event: QtCore.QEvent):
        self._opacity_animation.setStartValue(self.windowOpacity())
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent):
        self._opacity_animation.setStartValue(self.windowOpacity())
        self._opacity_animation.setEndValue(0.8)
        self._opacity_animation.start()
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.grip_vertical_btn:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self.start_drag(event)
                return True
            elif event.type() == QtCore.QEvent.MouseMove and event.buttons() == QtCore.Qt.LeftButton:
                self.perform_drag(event)
                return True
        return super().eventFilter(obj, event)

    def start_drag(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def perform_drag(self, event: QtGui.QMouseEvent):
        if event.buttons() == QtCore.Qt.LeftButton:
            new_pos = event.globalPos() - self.drag_start_position
            screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
            x = max(screen_geometry.left(), min(new_pos.x(), screen_geometry.right() - self.width()))
            y = max(screen_geometry.top(), min(new_pos.y(), screen_geometry.bottom() - self.height()))
            self.move(x, y)
            event.accept()

    def take_screenshot(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        # Hide before capture
        self.hide()
        screenshot = screen.grabWindow(0)
        self.switch_to_annotation_mode(screenshot)

    def grab_screen_area(self):
        self.capture_window = ScreenCaptureArea()
        self.capture_window.closed.connect(self.on_capture_window_closed)
        self.capture_window.show()

    def on_capture_window_closed(self):
        QtCore.QTimer.singleShot(200, self.capture_selected_area)

    def capture_selected_area(self):
        selected_rect = self.capture_window.get_selected_rect()
        if selected_rect.isNull():
            return

        # Hide the widget before capturing
        self.hide()
        self._capture_area(selected_rect)

    def _capture_area(self, selected_rect: QtCore.QRect):
        screen = QtGui.QGuiApplication.primaryScreen()
        screenshot = screen.grabWindow(
            0, selected_rect.x(), selected_rect.y(), selected_rect.width(), selected_rect.height()
        )
        self.switch_to_annotation_mode(screenshot)

    def switch_to_annotation_mode(self, screenshot: QtGui.QPixmap):
        self.annotate_window = AnnotateWindow()
        self.annotate_window.drawing_label.set_pixmap(screenshot)
        self.annotate_window.update_object_list()
        self.close()
        self.annotate_window.show()


class AnnotateWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Screenshot Annotator with Tabler Icons')
        self.current_tool_action = None
        self.__init_ui()
        self.select_tool(ToolMode.FREEHAND)

    def __init_ui(self):
        # Toolbar setup
        toolbar = QtWidgets.QToolBar("Annotation Tools", self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, toolbar)

        # Add Freehand Tool with TablerQIcon
        self.freehand_action = QtWidgets.QAction(TablerQIcon.pencil, 'Freehand Tool', self)
        self.freehand_action.setCheckable(True)
        self.freehand_action.triggered.connect(lambda: self.select_tool(ToolMode.FREEHAND))

        # Add Rectangle Tool with TablerQIcon
        self.rectangle_action = QtWidgets.QAction(TablerQIcon.square, 'Rectangle Tool', self)
        self.rectangle_action.setCheckable(True)
        self.rectangle_action.triggered.connect(lambda: self.select_tool(ToolMode.RECTANGLE))

        # Add Eraser Tool with TablerQIcon
        self.eraser_action = QtWidgets.QAction(TablerQIcon.eraser, 'Eraser Tool', self)
        self.eraser_action.setCheckable(True)
        self.eraser_action.triggered.connect(lambda: self.select_tool(ToolMode.ERASER))

        # Add Text Tool with TablerQIcon
        self.text_action = QtWidgets.QAction(TablerQIcon.text_size, 'Text Tool', self)
        self.text_action.setCheckable(True)
        self.text_action.triggered.connect(lambda: self.select_tool(ToolMode.TEXT))

        toolbar.addActions([self.freehand_action, self.rectangle_action, self.eraser_action, self.text_action])

        # Color Picker Button
        color_action = QtWidgets.QAction(TablerQIcon.color_swatch, 'Select Color', self)
        color_action.triggered.connect(self.select_color)
        toolbar.addAction(color_action)

        # Save Button
        save_action = QtWidgets.QAction(TablerQIcon.device_floppy, 'Save Image', self)
        save_action.triggered.connect(self.save_image)
        toolbar.addAction(save_action)

        # Drawing Area
        self.drawing_label = DrawingLabel(self)
        self.setCentralWidget(self.drawing_label)

        # Connect the signal from DrawingLabel to update the object list
        self.drawing_label.drawing_changed.connect(self.update_object_list)

        # Object List Widget
        self.object_list_widget = QtWidgets.QTreeWidget()
        self.object_list_widget.setHeaderLabels(["Object Type", "Details"])
        dock = QtWidgets.QDockWidget("Drawing Objects", self)
        dock.setWidget(self.object_list_widget)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def update_object_list(self):
        self.object_list_widget.clear()
        for i, obj in enumerate(self.drawing_label.drawing_objects):
            item = QtWidgets.QTreeWidgetItem(self.object_list_widget)
            item.setText(0, f"Smoothed Line {i+1}")
            item.setText(1, f"Points: {len(obj.points)}, Color: {obj.color.name()}, Width: {obj.width}")
        for i, rect in enumerate(self.drawing_label.rectangles):
            item = QtWidgets.QTreeWidgetItem(self.object_list_widget)
            item.setText(0, f"Rectangle {i+1}")
            item.setText(1, f"Top-left: ({rect.topLeft().x()}, {rect.topLeft().y()}), Size: ({rect.width()}x{rect.height()})")

    def select_tool(self, tool: ToolMode):
        # Select the current tool action
        self.current_tool_action = self.sender()

        # Uncheck all other tool actions
        for action in [self.freehand_action, self.rectangle_action, self.eraser_action, self.text_action]:
            if action.isChecked() and action != self.current_tool_action:
                action.setChecked(False)

        # Set the tool for the drawing label
        self.current_tool = tool
        self.drawing_label.current_tool = tool

    def select_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.drawing_label.pen_color = color

    def save_image(self):
        if not self.drawing_label.image.isNull():
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg)")
            if file_path:
                self.drawing_label.image.save(file_path)


if __name__ == '__main__':
    from blackboard.theme import set_theme
    app = QtWidgets.QApplication(sys.argv)
    set_theme(app, 'dark')
    main_window = ScreenshotWidget()
    main_window.show()
    sys.exit(app.exec_())