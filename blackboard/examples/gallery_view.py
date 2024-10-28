import sys
import os
import glob
from typing import Any, Dict
from qtpy import QtCore, QtGui, QtWidgets
from tablerqicon import TablerQIcon  # Importing TablerQIcon

from blackboard.widgets.momentum_scroll_widget import MomentumScrollListWidget
from blackboard.widgets.thumbnail_widget import ThumbnailWidget

@staticmethod
def create_shadow_effect(blur_radius=30, x_offset=0, y_offset=4, color=QtGui.QColor(0, 0, 0, 150)):
    """Create and return a shadow effect for the floating card or any widget.

    Args:
        blur_radius (int): The blur radius of the shadow.
        x_offset (int): The horizontal offset of the shadow.
        y_offset (int): The vertical offset of the shadow.
        color (QColor): The color of the shadow effect.

    Returns:
        QGraphicsDropShadowEffect: Configured shadow effect.
    """
    shadow = QtWidgets.QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setXOffset(x_offset)
    shadow.setYOffset(y_offset)
    shadow.setColor(color)
    return shadow

class GallerySectionHeader(QtWidgets.QWidget):
    """Section header widget for gallery groups."""
    
    def __init__(self, group_name: str, gallery_widget: 'GalleryWidget' = None):
        super().__init__(gallery_widget)

        self.gallery_widget = gallery_widget
        self.group_name = group_name
        self.collapsed = False
        
        self.__init_ui()

    def __init_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Collapse/expand icon using TablerQIcon
        self.icon_label = QtWidgets.QLabel(self)
        self.icon_label.setFixedSize(24, 24)
        self.update_icon()
        layout.addWidget(self.icon_label)

        # Group name label
        self.label = QtWidgets.QLabel(self.group_name, self)
        self.label.setStyleSheet('''
            QLabel {
                background-color: rgba(127, 127, 127, 0.4);
            }
            QLabel:hover {
                background-color: rgba(127, 127, 127, 0.6);
            }
        ''')
        layout.addWidget(self.label)

        # Set layout
        self.setLayout(layout)

        # Make the entire widget clickable
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        """Handle mouse press events to toggle only on left-click."""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.toggle()
        
        super().mousePressEvent(event)

    def toggle(self):
        """Toggle the collapse state of the section."""
        self.collapsed = not self.collapsed
        self.update_icon()
        self.gallery_widget.toggle_section(self.group_name, self.collapsed)

    def update_icon(self):
        """Update the icon based on the collapse state."""
        icon = TablerQIcon.chevron_down if not self.collapsed else TablerQIcon.chevron_right
        self.icon_label.setPixmap(icon.pixmap(20, 20))

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
        self.form_layout = QtWidgets.QVBoxLayout(self.form_widget)
        
        self.field_widgets = {}
        for field, value in self.data_fields.items():
            label = QtWidgets.QLabel(value)
            label.setToolTip(field)
            self.form_layout.addWidget(label)
            self.field_widgets[field] = label

        self.content_area.addWidget(self.thumbnail_widget)
        self.content_area.addWidget(self.form_widget)

        # Add Widgets to Layouts
        # ----------------------
        layout.addWidget(self.title_widget)
        layout.addWidget(self.content_area)

        self.set_view_mode()
        self.lock_splitter_handle()

    def set_field_visibility(self, field, visible):
        """Set the visibility of a specific field."""
        if field in self.field_widgets:
            self.field_widgets[field].setVisible(visible)

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

class GalleryManipulationToolBar(QtWidgets.QToolBar):
    """A unified toolbar for sorting, grouping, and managing field visibility."""

    def __init__(self, parent: 'GalleryWidget') -> None:
        super().__init__(parent)
        self.gallery_widget = parent
        self.__init_ui()

    def __init_ui(self) -> None:
        self.setIconSize(QtCore.QSize(22, 22))
        self.setProperty('widget-style', 'overlay')

        # Get available fields from the gallery view
        fields = self.gallery_widget.get_available_fields()

        # Sort
        self.sort_rule_button = QtWidgets.QPushButton(TablerQIcon.arrows_sort, 'Sort', self)
        self.sort_rule_button.setMinimumWidth(100)
        self.sort_rule_menu = QtWidgets.QMenu(self.sort_rule_button)
        self.sort_rule_button.setMenu(self.sort_rule_menu)

        # Group
        self.group_button = QtWidgets.QPushButton(TablerQIcon.layout_2, 'Group', self)
        self.group_button.setMinimumWidth(100)
        self.group_menu = QtWidgets.QMenu(self.group_button)
        self.group_button.setMenu(self.group_menu)

        # Show/Hide Fields Button
        self.fields_action = QtGui.QAction(TablerQIcon.list, 'Show/Hide Fields')

        self.addAction(self.fields_action)
        self.addSeparator()
        self.addWidget(self.sort_rule_button)
        self.addWidget(self.group_button)

        self.fields_action.triggered.connect(self.show_field_settings)

    def group_by_changed(self, text):
        self.gallery_widget.set_group_by_field(text)

    def sort_by_changed(self, text):
        # Implement sorting logic here
        pass

    def show_field_settings(self):
        # Implement a dialog or dropdown for field visibility settings
        self.gallery_widget.open_visualize_settings()

class GalleryViewToolBar(QtWidgets.QToolBar):

    BUTTON_SIZE = 22

    def __init__(self, parent: 'GalleryWidget') -> None:
        """Initialize the GalleryViewToolBar."""
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

        self.refresh_action = self.add_action(
            icon=self.tabler_icon.refresh,
            tooltip="Refresh Gallery",
        )

    def add_action(self, icon: QtGui.QIcon, tooltip: str, checkable: bool = False) -> QtGui.QAction:
        """Adds an action to the toolbar."""
        action = self.addAction(icon, tooltip)
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
            QtWidgets.QListWidget.ViewMode.ListMode: (self.tabler_icon.list_details, "List View"),
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
        self.size_slider.valueChanged.connect(self.gallery_widget.set_card_size)
        self.refresh_action.triggered.connect(self.refresh_gallery)

    def refresh_gallery(self) -> None:
        """Refresh the gallery content."""
        # Implement the logic to refresh the gallery
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

        # Initialize setup
        self.__init_attributes()
        self.__init_ui()

    def __init_attributes(self):
        """Initialize the attributes.
        """
        # Initialize available fields as an empty list
        self.fields = []
        self.visible_fields = {}
        self.groups = {}  # To track headers and items under each group
        self.group_by_field = None  # The field used for grouping items

    def __init_ui(self):
        """Initialize the UI of the widget.
        """
        self.setViewMode(QtWidgets.QListWidget.IconMode)
        self.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.setMovement(QtWidgets.QListWidget.Movement.Static)
        self.setSpacing(10)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Create the spacer item
        self.spacer_item = QtWidgets.QListWidgetItem()
        self.spacer_item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
        self.insertItem(0, self.spacer_item)

        # Set the custom item delegate
        self.setItemDelegate(InvisibleItemDelegate(self))

        # Configure overlay layout
        self.overlay_layout = QtWidgets.QHBoxLayout(self)
        self.overlay_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.overlay_layout.setContentsMargins(8, 8, 16, 8)

        # Initialize and add toolbars
        self.general_tool_bar = QtWidgets.QToolBar(self)
        self.utility_tool_bar = GalleryViewToolBar(self)
        self.manipulation_tool_bar = GalleryManipulationToolBar(self)

        self.utility_tool_bar.setGraphicsEffect(create_shadow_effect())
        self.manipulation_tool_bar.setGraphicsEffect(create_shadow_effect())

        # Add toolbars
        self.overlay_layout.addWidget(self.general_tool_bar, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.overlay_layout.addWidget(self.manipulation_tool_bar, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.overlay_layout.addWidget(self.utility_tool_bar, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def get_available_fields(self):
        """Return a list of available fields for grouping, sorting, and visibility."""
        return self.fields

    def set_fields(self, fields):
        """Set the available fields for grouping, sorting, and visibility.
        
        Args:
            fields (list): A list of field names (strings) to be set as available fields.
        """
        self.fields = fields

    def set_group_by_field(self, field_name: str):
        """Set the field by which to group the items."""
        self.group_by_field = field_name
        
        # Store the spacer item temporarily before clearing
        spacer_item = self.takeItem(0) if self.spacer_item else None

        # Clear all items in the gallery
        self.clear()
        self.groups = {}

        # Re-add the spacer item if it was successfully stored
        if spacer_item:
            self.insertItem(0, spacer_item)
            self.spacer_item = spacer_item

    def set_resize_mode(self, mode: 'ThumbnailWidget.ResizeMode' = ThumbnailWidget.ResizeMode.Fit):
        for index in range(self.count()):
            list_item = self.item(index)
            item_widget = self.itemWidget(list_item)
            if not item_widget or not isinstance(item_widget, GalleryItemWidget):
                continue
            item_widget.thumbnail_widget.set_resize_mode(mode)

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

        # Determine the group name based on the grouping field
        if self.group_by_field and self.group_by_field in data_fields:
            group_name = data_fields[self.group_by_field]
        else:
            group_name = 'Ungrouped'

        # Create a section header if the group doesn't exist
        if group_name not in self.groups:
            self.add_section_header(group_name)

        # Find the position to insert the new item under the section header
        group_data = self.groups[group_name]
        insert_position = self.row(group_data['header']) + len(group_data['items']) + 1

        # Create the GalleryItemWidget
        gallery_item_widget = GalleryItemWidget(image_path, data_fields, self)

        # Create the QListWidgetItem and set its size hint
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(gallery_item_widget.sizeHint())

        # Insert the item after the section header
        self.insertItem(insert_position, item)
        self.setItemWidget(item, gallery_item_widget)

        # Track the item under its group
        group_data['items'].append(item)

    def add_section_header(self, group_name: str):
        """Add a section header for a new group."""
        header_widget = GallerySectionHeader(group_name, self)
        header_item = QtWidgets.QListWidgetItem()
        header_item.setSizeHint(QtCore.QSize(self.viewport().width() - 20, 40))
        header_item.setFlags(QtCore.Qt.NoItemFlags)  # Make it non-selectable

        self.addItem(header_item)
        self.setItemWidget(header_item, header_widget)

        # Initialize the group data with the header and an empty item list
        self.groups[group_name] = {'header': header_item, 'items': []}

    def toggle_section(self, group_name: str, collapsed: bool):
        """Show or hide items under the specified section."""
        if group_name not in self.groups:
            return

        group_data = self.groups[group_name]
        for item in group_data['items']:
            item.setHidden(collapsed)

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
        for field in self.fields:
            checkbox = QtWidgets.QCheckBox(field)
            checkbox.setChecked(self.visible_fields.get(field, True))
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

    def set_fields(self, fields):
        """Set the available fields for grouping, sorting, and visibility.
        
        Args:
            fields (list): A list of field names (strings) to be set as available fields.
        """
        self.fields = fields
        # Initialize all fields as visible by default
        self.visible_fields = {field: True for field in fields}

    def toggle_field_visibility(self, field, state):
        """Toggle visibility of a specific field."""
        visible = state == QtCore.Qt.Checked
        self.visible_fields[field] = visible

        # Update all GalleryItemWidgets to reflect the new visibility state
        for index in range(self.count()):
            list_item = self.item(index)
            item_widget = self.itemWidget(list_item)
            if isinstance(item_widget, GalleryItemWidget):
                item_widget.set_field_visibility(field, visible)

        # Refresh the view
        self.model().layoutChanged.emit()

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_spacer_item_size()
        self.update_section_headers_size()

    def update_spacer_item_size(self):
        # Get the viewport width and adjust for any margins or spacing
        full_width = self.viewport().width() - 20  # Adjust as needed

        # Set the size hint for the spacer item
        self.spacer_item.setSizeHint(QtCore.QSize(full_width, self.TOP_MARGIN))  # Adjust height as needed

    def update_section_headers_size(self):
        """Update the size of all section headers to match the viewport width."""
        full_width = self.viewport().width() - 20
        for group_name, group_data in self.groups.items():
            header_item = group_data['header']
            header_item.setSizeHint(QtCore.QSize(full_width, 32))  # Update the size hint

class GalleryWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Gallery")
        self.setGeometry(100, 100, 800, 800)
        self.__init_ui()

    def __init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Create QListWidget with vertical scroll and wrap items horizontally
        self.gallery_view_widget = GalleryWidget(self)
        layout.addWidget(self.gallery_view_widget)

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

    # Example metadata for images
    vfx_shot_metadata = [
        {
            'image_path': image_files[0],
            'data_fields': {
                "Shot Name": "shot_001",
                "Description": "Explosion in the background with debris flying.",
                "Frame Range": "1001-1100",
                "Artist": "Alice Smith",
                "Shot Type": "FX",
                "Status": "In Progress",
            }
        },
        {
            'image_path': image_files[1],
            'data_fields': {
                "Shot Name": "shot_002",
                "Description": "Character enters the frame from the left.",
                "Frame Range": "1050-1150",
                "Artist": "Bob Johnson",
                "Shot Type": "Compositing",
                "Status": "Complete",
            }
        },
        {
            'image_path': image_files[2],
            'data_fields': {
                "Shot Name": "shot_003",
                "Description": "Background matte painting integration.",
                "Frame Range": "1200-1300",
                "Artist": "Alice Smith",
                "Shot Type": "Matte Painting",
                "Status": "Review",
            }
        },
        {
            'image_path': image_files[3],
            'data_fields': {
                "Shot Name": "shot_004",
                "Description": "Fire effect on building collapse.",
                "Frame Range": "1150-1250",
                "Artist": "Charlie Davis",
                "Shot Type": "FX",
                "Status": "Pending",
            }
        },
        {
            'image_path': image_files[4],
            'data_fields': {
                "Shot Name": "shot_005",
                "Description": "Character close-up with lighting adjustments.",
                "Frame Range": "1100-1200",
                "Artist": "Bob Johnson",
                "Shot Type": "Compositing",
                "Status": "In Progress",
            }
        },
        {
            'image_path': image_files[5],
            'data_fields': {
                "Shot Name": "shot_006",
                "Description": "CG assets integrated into live-action plate.",
                "Frame Range": "1300-1400",
                "Artist": "Charlie Davis",
                "Shot Type": "Integration",
                "Status": "Complete",
            }
        },
        {
            'image_path': image_files[6],
            'data_fields': {
                "Shot Name": "shot_007",
                "Description": "Water simulation running through the street.",
                "Frame Range": "1400-1500",
                "Artist": "Alice Smith",
                "Shot Type": "FX",
                "Status": "In Progress",
            }
        },
        {
            'image_path': image_files[7],
            'data_fields': {
                "Shot Name": "shot_008",
                "Description": "Sky replacement with volumetric clouds.",
                "Frame Range": "1250-1350",
                "Artist": "Bob Johnson",
                "Shot Type": "Matte Painting",
                "Status": "Review",
            }
        },
        {
            'image_path': image_files[8],
            'data_fields': {
                "Shot Name": "shot_009",
                "Description": "Car chase with motion blur effects.",
                "Frame Range": "1500-1600",
                "Artist": "Charlie Davis",
                "Shot Type": "Compositing",
                "Status": "Pending",
            }
        },
        {
            'image_path': image_files[9],
            'data_fields': {
                "Shot Name": "shot_010",
                "Description": "Day-to-night color grading transformation.",
                "Frame Range": "1601-1700",
                "Artist": "Alice Smith",
                "Shot Type": "Color Grading",
                "Status": "In Progress",
            }
        },
        {
            'image_path': image_files[10],
            'data_fields': {
                "Shot Name": "shot_011",
                "Description": "Explosion aftermath with dust and smoke simulation.",
                "Frame Range": "1700-1800",
                "Artist": "Bob Johnson",
                "Shot Type": "FX",
                "Status": "Pending",
            }
        },
        {
            'image_path': image_files[11],
            'data_fields': {
                "Shot Name": "shot_012",
                "Description": "Green screen replacement with futuristic cityscape.",
                "Frame Range": "1801-1900",
                "Artist": "Charlie Davis",
                "Shot Type": "Compositing",
                "Status": "Complete",
            }
        },
        {
            'image_path': image_files[12],
            'data_fields': {
                "Shot Name": "shot_013",
                "Description": "Spaceship takeoff with realistic exhaust flames.",
                "Frame Range": "1900-2000",
                "Artist": "Alice Smith",
                "Shot Type": "FX",
                "Status": "In Progress",
            }
        },
        {
            'image_path': image_files[13],
            'data_fields': {
                "Shot Name": "shot_014",
                "Description": "Character shadow enhancement for evening scene.",
                "Frame Range": "2001-2100",
                "Artist": "Bob Johnson",
                "Shot Type": "Compositing",
                "Status": "Review",
            }
        },
        {
            'image_path': image_files[14],
            'data_fields': {
                "Shot Name": "shot_015",
                "Description": "CG building destruction with camera shake effect.",
                "Frame Range": "2101-2200",
                "Artist": "Charlie Davis",
                "Shot Type": "FX",
                "Status": "Pending",
            }
        },
    ]


    # Initialize and show the gallery window
    window = GalleryWindow()
    # Set available fields dynamically
    fields = ["Artist", "Shot Type", "Status", "Shot Name", "Frame Range", "Date"]
    window.gallery_view_widget.set_fields(fields)
    window.gallery_view_widget.set_group_by_field("Status")
    
    # Add items to the gallery based on metadata
    for metadata in vfx_shot_metadata:
        window.gallery_view_widget.add_item(metadata)

    window.show()
    sys.exit(app.exec_())
