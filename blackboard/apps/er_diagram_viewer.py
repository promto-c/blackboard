from PyQt5 import QtWidgets, QtGui, QtCore
import sqlite3

# Constants for colors, sizes, etc.
BACKGROUND_COLOR = QtGui.QColor(30, 30, 30)
TABLE_COLOR = QtGui.QColor(40, 40, 40)
HIGHLIGHT_COLOR = QtGui.QColor(60, 60, 60)
LINE_COLOR = QtGui.QColor(0, 128, 255)
HIGHLIGHT_LINE_COLOR = QtGui.QColor(255, 165, 0)
TEXT_COLOR = QtGui.QColor(255, 255, 255)

TABLE_WIDTH = 200
ROW_HEIGHT = 20
HEADER_HEIGHT = 30
MARGIN = 80
COLUMN_WIDTH = 240

def get_db_schema(db_path: str) -> tuple[dict, list]:
    """Fetch schema information and foreign keys from the SQLite database."""
    schema = {}
    foreign_keys = []

    # Open database in read-only mode
    conn = sqlite3.connect(f"file:///{db_path}?mode=ro", uri=True)

    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema[table_name] = columns

            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            fks = cursor.fetchall()
            for fk in fks:
                foreign_keys.append((table_name, fk[3], fk[2], fk[4]))  # (from_table, from_column, to_table, to_column)

    return schema, foreign_keys

class TableItem(QtWidgets.QGraphicsRectItem):
    """Custom QGraphicsRectItem to represent a database table."""

    def __init__(self, table_name: str, columns: list, position: tuple, theme: str = 'dark'):
        super().__init__(0, 0, TABLE_WIDTH, HEADER_HEIGHT + len(columns) * ROW_HEIGHT)
        self.setPos(*position)

        # Enable hover events
        self.setAcceptHoverEvents(True)

        # Set pen and brush for dark theme
        self.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200)))  # Light gray border
        self.setBrush(QtGui.QBrush(TABLE_COLOR))

        # Table header
        self.header = QtWidgets.QGraphicsTextItem(table_name, self)
        self.header.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.header.setDefaultTextColor(TEXT_COLOR)
        self.header.setPos(5, 5)

        # Add column names
        self.columns = []
        for i, column in enumerate(columns):
            column_text = QtWidgets.QGraphicsTextItem(f"{'* ' if column[5] else ''}{column[1]} ({column[2]})", self)
            column_text.setDefaultTextColor(QtGui.QColor(180, 180, 180))  # Light gray text
            column_text.setPos(5, HEADER_HEIGHT + i * ROW_HEIGHT)
            self.columns.append(column_text)

        # List to store connections associated with this table
        self.connections = []

    def add_connection(self, connection_item):
        """Add a connection item associated with this table."""
        self.connections.append(connection_item)

    def get_column_edge_position(self, column_name: str, side: str) -> QtCore.QPointF:
        """Get the edge position of a specific column within the table."""
        for column in self.columns:
            if column_name in column.toPlainText():
                column_rect = column.sceneBoundingRect()
                if side == 'left':
                    return QtCore.QPointF(column_rect.left(), column_rect.center().y())
                else:
                    return QtCore.QPointF(column_rect.right(), column_rect.center().y())
        return self.sceneBoundingRect().center()

    def hoverEnterEvent(self, event):
        """Change appearance on hover and highlight connections."""
        self.setPen(QtGui.QPen(QtGui.QColor(255, 255, 0), 2))  # Yellow border on hover
        self.setBrush(QtGui.QBrush(HIGHLIGHT_COLOR))  # Lighter fill on hover

        # Highlight associated connections
        for connection in self.connections:
            connection.highlight(True)

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Revert appearance on hover leave and reset connection highlights."""
        self.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200)))  # Revert to light gray border
        self.setBrush(QtGui.QBrush(TABLE_COLOR))  # Revert to dark gray fill

        # Reset associated connections
        for connection in self.connections:
            connection.highlight(False)

        super().hoverLeaveEvent(event)

class ConnectionItem(QtWidgets.QGraphicsPathItem):
    """Custom QGraphicsPathItem to represent a connection between tables."""

    def __init__(self, path: QtGui.QPainterPath, from_table: str, to_table: str, from_column: str, to_column: str):
        super().__init__(path)

        # Enable hover events
        self.setAcceptHoverEvents(True)

        # Set pen for dark theme
        self.default_pen = QtGui.QPen(LINE_COLOR, 2)  # Light blue line
        self.highlight_pen = QtGui.QPen(HIGHLIGHT_LINE_COLOR, 3)  # Orange line for highlight

        self.setPen(self.default_pen)

        # Store connection details
        self.from_table = from_table
        self.to_table = to_table
        self.from_column = from_column
        self.to_column = to_column

        # Set tooltip with connection details
        self.setToolTip(f"{from_table}.{from_column} -> {to_table}.{to_column}")

    def hoverEnterEvent(self, event):
        """Change line appearance on hover."""
        self.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 3, QtCore.Qt.DashLine))  # Red dashed line on hover
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Revert line appearance on hover leave."""
        self.setPen(self.default_pen)  # Revert to default line
        super().hoverLeaveEvent(event)

    def highlight(self, should_highlight: bool):
        """Highlight or unhighlight the line."""
        self.setPen(self.highlight_pen if should_highlight else self.default_pen)

class ERDiagramView(QtWidgets.QGraphicsView):
    """Custom QGraphicsView to display the ER diagram."""

    def __init__(self, schema: dict, foreign_keys: list, parent=None):
        super().__init__(parent)
        scene = QtWidgets.QGraphicsScene()
        self.setScene(scene)
        scene.setBackgroundBrush(QtGui.QBrush(BACKGROUND_COLOR))  # Dark background
        self.table_items = {}
        self.draw_schema(schema)
        self.draw_relationships(foreign_keys)

        # Enable zooming and panning
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Hide scrollbars
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Store the initial point for panning
        self.last_drag_pos = None

    def draw_schema(self, schema: dict):
        """Draw tables and their columns on the scene."""
        x, y = 0, 0
        max_height = 0

        for table_name, columns in schema.items():
            table_item = TableItem(table_name, columns, (x, y))
            self.scene().addItem(table_item)
            self.table_items[table_name] = table_item

            y += table_item.boundingRect().height() + MARGIN
            max_height = max(max_height, table_item.boundingRect().height())

            if y > 600:  # If y position exceeds 600, move to the next column
                y = 0
                x += COLUMN_WIDTH + MARGIN

    def draw_relationships(self, foreign_keys: list):
        """Draw lines representing foreign key relationships between tables."""
        for from_table, from_column, to_table, to_column in foreign_keys:
            from_item = self.table_items[from_table]
            to_item = self.table_items[to_table]

            # Determine positions
            from_pos = from_item.sceneBoundingRect().center()
            to_pos = to_item.sceneBoundingRect().center()

            # Logic for determining connection sides
            start_pos, end_pos = self.determine_connection_sides(from_item, to_item, from_pos, to_pos, from_column, to_column)

            # Calculate the midpoint for cleaner paths
            horizontal_midpoint = (start_pos.x() + end_pos.x()) / 2

            # Create a path starting with horizontal movement
            path = QtGui.QPainterPath()
            path.moveTo(start_pos)
            path.lineTo(horizontal_midpoint, start_pos.y())  # Horizontal line
            path.lineTo(horizontal_midpoint, end_pos.y())    # Vertical line
            path.lineTo(end_pos)                             # Final horizontal line

            # Add the connection item with hover effects
            connection_item = ConnectionItem(path, from_table, to_table, from_column, to_column)
            # Move an item to the back
            connection_item.setZValue(-1000)

            self.scene().addItem(connection_item)

            # Associate connection with both tables
            from_item.add_connection(connection_item)
            to_item.add_connection(connection_item)

    def determine_connection_sides(self, from_item, to_item, from_pos, to_pos, from_column, to_column):
        """Determine which sides of the tables to connect based on their positions."""
        if from_pos.x() < to_pos.x():
            # Connect from right of source to left of destination
            start_pos = from_item.get_column_edge_position(from_column, 'right')
            end_pos = to_item.get_column_edge_position(to_column, 'left')
        elif from_pos.x() > to_pos.x():
            # Connect from left of source to right of destination
            start_pos = from_item.get_column_edge_position(from_column, 'left')
            end_pos = to_item.get_column_edge_position(to_column, 'right')
        else:
            # If same vertical alignment, connect from right to left
            start_pos = from_item.get_column_edge_position(from_column, 'right')
            end_pos = to_item.get_column_edge_position(to_column, 'right')
        return start_pos, end_pos

    def wheelEvent(self, event):
        """Zoom in or out with mouse wheel."""
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        """Start panning with the middle mouse button."""
        if event.button() == QtCore.Qt.MiddleButton:
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.last_drag_pos = event.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle panning."""
        if self.last_drag_pos is not None:
            # Calculate delta movement and account for zoom level
            delta = self.mapToScene(event.pos()) - self.mapToScene(self.last_drag_pos)
            # Invert the delta to drag in the correct direction
            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.translate(delta.x(), delta.y())
            self.last_drag_pos = event.pos()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End panning."""
        if event.button() == QtCore.Qt.MiddleButton:
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.last_drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class MainWindow(QtWidgets.QWidget):
    """Main application window for displaying the ER diagram."""

    def __init__(self, db_path: str):
        super().__init__()
        self.setWindowTitle("ER Diagram Viewer")
        self.setGeometry(100, 100, 1200, 800)

        schema, foreign_keys = get_db_schema(db_path)

        self.layout = QtWidgets.QVBoxLayout()

        # Search bar
        search_layout = QtWidgets.QHBoxLayout()
        self.search_bar = QtWidgets.QLineEdit(self)
        self.search_bar.setPlaceholderText("Search tables...")
        self.search_bar.textChanged.connect(self.search_tables)
        search_layout.addWidget(self.search_bar)
        self.layout.addLayout(search_layout)

        # Diagram view
        self.diagram_view = ERDiagramView(schema, foreign_keys)
        self.layout.addWidget(self.diagram_view)

        self.setLayout(self.layout)

    def search_tables(self):
        """Filter tables based on search input."""
        search_text = self.search_bar.text().lower()
        for table_name, table_item in self.diagram_view.table_items.items():
            table_item.setVisible(search_text in table_name.lower())

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)

    # Load your database path here
    db_path = "chinook.db"  # Adjust the path to your database file

    main_window = MainWindow(db_path)
    main_window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
