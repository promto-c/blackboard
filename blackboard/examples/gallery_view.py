import sys
import os
import glob
from typing import Any, Dict
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon  # Importing TablerQIcon

from blackboard.widgets.momentum_scroll_widget import MomentumScrollListWidget
from blackboard.widgets.thumbnail_widget import ThumbnailWidget


class GalleryItemWidget(QtWidgets.QWidget):

    DEFAULT_SIZE = 150

    def __init__(self, image_path, data_fields: Dict[str, Any], parent: 'GalleryWidget' = None):
        super().__init__(parent)

        # Store the arguments
        self.image_path = image_path
        self.data_fields = data_fields

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        self._card_size = self.DEFAULT_SIZE
        self._view_mode = QtWidgets.QListWidget.ViewMode.IconMode

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        # Create Layouts
        # --------------
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create Widgets
        # --------------
        self.title_widget = QtWidgets.QLabel('Title', self)
        self.content_area = QtWidgets.QSplitter(self)

        # Thumbnail widget at the top
        self.thumbnail_widget = ThumbnailWidget(self.image_path, parent=self)

        # Form-like widget to show data fields
        self.form_widget = QtWidgets.QWidget(self)
        form_layout = QtWidgets.QFormLayout(self.form_widget)
        for field, value in self.data_fields.items():
            form_layout.addRow(field, QtWidgets.QLabel(value))

        self.content_area.addWidget(self.thumbnail_widget)
        self.content_area.addWidget(self.form_widget)

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.title_widget)
        layout.addWidget(self.content_area)

        self.set_view_mode()
        self.lock_splitter_handle()

    def lock_splitter_handle(self):
        # Set handle width to zero to make it invisible
        self.content_area.setHandleWidth(0)

        # Disable resizing interaction
        for i in range(self.content_area.count()):
            handle = self.content_area.handle(i)
            handle.setEnabled(False)

    def set_card_size(self, size: int = DEFAULT_SIZE):
        self._card_size = size
        self.thumbnail_widget.setFixedSize(size, size)
        if self._view_mode == QtWidgets.QListWidget.ViewMode.IconMode:
            self.content_area.setMinimumHeight(0)
            self.content_area.setMaximumHeight(16777215)
            self.content_area.setFixedWidth(size)
        else:
            self.content_area.setMinimumWidth(0)
            self.content_area.setMaximumWidth(16777215)
            self.content_area.setFixedHeight(size)

    def set_view_mode(self, view_mode: QtWidgets.QListWidget.ViewMode = QtWidgets.QListWidget.ViewMode.IconMode) -> None:
        """Adjust the layout based on the view mode."""
        self._view_mode = view_mode
        if self._view_mode == QtWidgets.QListWidget.ViewMode.IconMode:
            # Unset the fixed height
            self.content_area.setOrientation(QtCore.Qt.Vertical)
        else:
            self.content_area.setOrientation(QtCore.Qt.Horizontal)

        self.set_card_size(self._card_size)


class InvisibleItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.row() == 0:
            # Skip painting for the spacer item
            return
        else:
            super().paint(painter, option, index)

class GalleryUtilityToolBar(QtWidgets.QToolBar):

    BUTTON_SIZE = 22

    def __init__(self, parent: 'GalleryWidget') -> None:
        """Initialize the GalleryUtilityToolBar."""
        super().__init__(parent)
        self.gallery_widget = parent
        self.__init_attributes()
        self.__init_ui()
        self.__init_signal_connections()

    def __init_attributes(self) -> None:
        """Initialize attributes."""
        self.tabler_icon = TablerQIcon(opacity=0.8)
        self.resize_mode_actions = {}
        self.current_resize_mode = ThumbnailWidget.ResizeMode.Fit

    def __init_ui(self) -> None:
        """Initialize the UI of the toolbar."""
        self.setIconSize(QtCore.QSize(self.BUTTON_SIZE, self.BUTTON_SIZE))
        self.setProperty('widget-style', 'overlay')

        # Add actions to the toolbar
        self.add_view_mode_actions()

        self.addSeparator()

        # Add Resize Mode actions
        self.add_resize_mode_actions()

        self.addSeparator()
        # Add size slider
        self.size_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.size_slider.setMinimum(50)
        self.size_slider.setMaximum(300)
        self.size_slider.setValue(150)  # Default value
        self.size_slider.setMaximumWidth(100)
        self.size_slider.setToolTip("Adjust Thumbnail Size")
        self.addWidget(self.size_slider)
        self.addSeparator()
        # self.settings_action = self.add_action(
        #     icon=self.tabler_icon.settings,
        #     tooltip="Settings",
        # )
        # self.visualize_action = self.add_action(
        #     icon=self.tabler_icon.adjustments,
        #     tooltip="Visualize Settings",
        # )

        self.refresh_action = self.add_action(
            icon=self.tabler_icon.refresh,
            tooltip="Refresh Gallery",
        )

    def add_action(self, icon: QtGui.QIcon, tooltip: str, checkable: bool = False) -> QtGui.QAction:
        """Adds an action to the toolbar."""
        action = self.addAction(icon, '')
        action.setToolTip(tooltip)
        action.setCheckable(checkable)

        # Access the widget for the action and set the cursor
        self.widgetForAction(action).setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        
        return action

    def add_view_mode_actions(self) -> None:
        """Add view mode actions to the toolbar."""
        view_mode_group = QtWidgets.QActionGroup(self)
        view_mode_group.setExclusive(True)

        # Define view modes with icons and tooltips
        view_modes = {
            QtWidgets.QListWidget.ViewMode.IconMode: (self.tabler_icon.layout_grid, "Grid View"),
            QtWidgets.QListWidget.ViewMode.ListMode: (self.tabler_icon.section, "List View"),
        }

        for mode, (icon, tooltip) in view_modes.items():
            action = self.add_action(
                icon=icon,
                tooltip=tooltip,
                checkable=True,
            )
            action.setData(mode)
            view_mode_group.addAction(action)
            # Check the current view mode
            if mode == self.gallery_widget.viewMode():
                action.setChecked(True)

        # Connect the action group's triggered signal
        view_mode_group.triggered.connect(self.set_view_mode)

    # Callback methods for actions
    def set_view_mode(self, action: QtWidgets.QAction) -> None:
        """Set the view mode based on the selected action."""
        mode = action.data()
        self.gallery_widget.setViewMode(mode)

    def add_resize_mode_actions(self) -> None:
        """Add resize mode actions to the toolbar."""
        # Create an action group for mutual exclusivity
        resize_mode_group = QtWidgets.QActionGroup(self)
        resize_mode_group.setExclusive(True)

        # Define resize modes and corresponding icons
        resize_modes = {
            ThumbnailWidget.ResizeMode.Fit: (self.tabler_icon.aspect_ratio, "Fit Image"),
            ThumbnailWidget.ResizeMode.Fill: (self.tabler_icon.box_padding, "Fill Image"),
        }

        for mode, (icon, tooltip) in resize_modes.items():
            action = self.add_action(
                icon=icon,
                tooltip=tooltip,
                checkable=True,
            )
            action.setData(mode)
            resize_mode_group.addAction(action)
            self.resize_mode_actions[mode] = action
            # Check the default resize mode
            if mode == self.current_resize_mode:
                action.setChecked(True)

        # Connect the action group's triggered signal
        resize_mode_group.triggered.connect(self.set_resize_mode)

    def __init_signal_connections(self) -> None:
        """Initialize signal-slot connections."""
        # Additional signal connections can be added here if needed
        # self.toggle_view_action.triggered.connect(self.toggle_view)
        # self.settings_action.triggered.connect(self.open_settings)
        # self.visualize_action.triggered.connect(self.open_visualize_settings)
        self.size_slider.valueChanged.connect(self.gallery_widget.set_card_size)
        self.refresh_action.triggered.connect(self.refresh_gallery)

    def refresh_gallery(self) -> None:
        """Refresh the gallery content."""
        # Implement the logic to refresh the gallery
        pass

    def open_settings(self) -> None:
        """Open the settings dialog."""
        # Implement the logic to open settings
        pass

    def open_visualize_settings(self) -> None:
        """Open the visualize settings dialog."""
        # Implement the logic to open visualize settings
        pass

    def set_resize_mode(self, action: QtWidgets.QAction) -> None:
        """Set the image resize mode based on the selected action."""
        mode = action.data()
        if isinstance(mode, ThumbnailWidget.ResizeMode):
            self.current_resize_mode = mode
            self.gallery_widget.set_resize_mode(mode)

class GalleryWidget(MomentumScrollListWidget):

    TOP_MARGIN = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QtWidgets.QListWidget.IconMode)
        self.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.setMovement(QtWidgets.QListWidget.Movement.Static)
        self.setSpacing(10)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Create the spacer item
        self.spacer_item = QtWidgets.QListWidgetItem()
        self.spacer_item.setFlags(QtCore.Qt.NoItemFlags)  # Make it non-selectable
        self.insertItem(0, self.spacer_item)

        # Set the custom item delegate
        self.setItemDelegate(InvisibleItemDelegate(self))

        # Initialize the overlay layout and add tool buttons
        self.overlay_layout = QtWidgets.QHBoxLayout(self)
        self.overlay_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.overlay_layout.setContentsMargins(4, 4, 16, 4)

        self.utility_tool_bar = GalleryUtilityToolBar(self)
        self.overlay_layout.addWidget(self.utility_tool_bar, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # Connect the scroll event to check the position and update button styles
        # self.verticalScrollBar().valueChanged.connect(self.update_button_background)

    def set_resize_mode(self, mode: 'ThumbnailWidget.ResizeMode' = ThumbnailWidget.ResizeMode.Fit):
        for index in range(self.count()):
            list_item = self.item(index)
            item_widget = self.itemWidget(list_item)
            if not item_widget or not isinstance(item_widget, GalleryItemWidget):
                continue
            item_widget.thumbnail_widget.set_resize_mode(mode)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_spacer_item_size()

    def update_spacer_item_size(self):
        # Get the viewport width and adjust for any margins or spacing
        full_width = self.viewport().width() - 20  # Adjust as needed

        # Set the size hint for the spacer item
        self.spacer_item.setSizeHint(QtCore.QSize(full_width, self.TOP_MARGIN))  # Adjust height as needed

    def add_item(self, datadict):
        """Add an item to the gallery view.

        Args:
            datadict (dict): A dictionary containing the data for the item.
                Expected keys:
                    - 'image_path': Path to the image file.
                    - 'data_fields': A dictionary of field names and values.
        """
        image_path = datadict.get('image_path')
        data_fields = datadict.get('data_fields', {})

        if not image_path or not os.path.exists(image_path):
            print(f"Image path '{image_path}' is invalid or does not exist.")
            return

        # Create the GalleryItemWidget
        gallery_item_widget = GalleryItemWidget(image_path, data_fields)

        # Create the QListWidgetItem and set its size hint
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(gallery_item_widget.sizeHint())

        # Insert the item after the spacer item
        self.addItem(item)
        self.setItemWidget(item, gallery_item_widget)

    def open_visualize_settings(self):
        """Open a dialog for visualization settings."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Visualize Settings")

        # Layout for the dialog
        dialog_layout = QtWidgets.QVBoxLayout(dialog)

        # Checkbox for toggling field visibility
        field_toggle_layout = QtWidgets.QVBoxLayout()
        field_toggle_layout.addWidget(QtWidgets.QLabel("Field Visibility:"))

        # Example field checkboxes
        self.field_checkboxes = {}
        fields = ['Title', 'Description', 'Date', 'Author']  # Example fields
        for field in fields:
            checkbox = QtWidgets.QCheckBox(field)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, field=field: self.toggle_field_visibility(field, state))
            field_toggle_layout.addWidget(checkbox)
            self.field_checkboxes[field] = checkbox

        dialog_layout.addLayout(field_toggle_layout)

        # Set dialog layout and show it
        dialog.setLayout(dialog_layout)
        dialog.exec_()

    def set_card_size(self, size):
        """Set the size of gallery items based on the slider value."""
        for index in range(self.count()):
            list_item = self.item(index)
            item_widget = self.itemWidget(list_item)
            if not item_widget or not isinstance(item_widget, GalleryItemWidget):
                continue
            item_widget.set_card_size(size)
            list_item.setSizeHint(item_widget.sizeHint())

        # Refresh the view
        self.model().layoutChanged.emit()

    def toggle_field_visibility(self, field, state):
        """Toggle visibility of a specific field."""
        visible = state == QtCore.Qt.Checked
        print(f"Field '{field}' visibility set to: {visible}")
        # Implement actual visibility logic based on your application

    def update_button_background(self):
        """Update the background of the tool buttons based on the scroll position."""
        scroll_position = self.verticalScrollBar().value()

        if scroll_position == 0:
            # When at the top, set buttons to have transparent background
            self.set_button_transparent()
        else:
            # When scrolled down, set a solid background for better visibility
            self.set_button_solid_background()

    def set_button_transparent(self):
        """Set the buttons to have a transparent background."""
        for button in [self.toggle_view_button, self.refresh_button, self.settings_button, self.visualize_button]:
            button.setStyleSheet('''
                QPushButton#tool_button {
                    border: none;
                    background: transparent;
                    padding: 5px;
                }
                QPushButton#tool_button:hover {
                    background-color: rgba(127, 127, 127, 1.0);
                }
            ''')

    def set_button_solid_background(self):
        """Set the buttons to have a solid background."""
        for button in [self.toggle_view_button, self.refresh_button, self.settings_button, self.visualize_button]:
            button.setStyleSheet('''
                QPushButton#tool_button {
                    border: none;
                    background-color: rgba(127, 127, 127, 0.6);
                    padding: 5px;
                    border-radius: 5px;
                }
                QPushButton#tool_button:hover {
                    background-color: rgba(127, 127, 127, 1.0);
                }
            ''')

    def setViewMode(self, mode: QtWidgets.QListWidget.ViewMode):
        """Override setViewMode to update item widgets."""
        super().setViewMode(mode)
        # Update all item widgets to adjust their layout
        for index in range(self.count()):
            list_item = self.item(index)
            item_widget = self.itemWidget(list_item)
            if not item_widget or not isinstance(item_widget, GalleryItemWidget):
                continue
            item_widget.set_view_mode(mode)
            list_item.setSizeHint(item_widget.sizeHint())

class GalleryWindow(QtWidgets.QWidget):
    def __init__(self, image_paths):
        super().__init__()
        self.setWindowTitle("Image Gallery")
        self.setGeometry(100, 100, 800, 800)
        self.__init_ui(image_paths)

    def __init_ui(self, image_paths):
        layout = QtWidgets.QVBoxLayout(self)

        # Create QListWidget with vertical scroll and wrap items horizontally
        self.gallery_view_widget = GalleryWidget(self)
        layout.addWidget(self.gallery_view_widget)

        # Add items to the gallery using the add_item method
        for image_path in image_paths:
            datadict = {
                'image_path': image_path,
                'data_fields': {
                    "Title": "Sunset Over the Mountains",
                    "Description": "A stunning view of the sun setting behind the mountain range with vibrant colors in the sky.",
                    "Date": "2024-10-20",
                    "Author": "Jane Doe",
                    # Add more fields as needed
                }
            }
            self.gallery_view_widget.add_item(datadict)

        self.setLayout(layout)

def get_image_paths(directory, extensions=('*.jpg', '*.png', '*.jpeg', '*.gif', '*.webp')):
    """Fetch image paths from the specified directory with the given extensions."""
    image_paths = []
    for ext in extensions:
        image_paths.extend(glob.glob(os.path.join(directory, ext)))
    return image_paths


if __name__ == "__main__":
    from blackboard import theme
    app = QtWidgets.QApplication(sys.argv)
    theme.set_theme(app, 'dark')

    # Specify directory to load images
    directory = ''
    image_files = get_image_paths(directory)

    # Initialize and show the gallery window
    window = GalleryWindow(image_files)
    window.show()
    sys.exit(app.exec_())
