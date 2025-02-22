

import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QSizePolicy, QScrollArea,
                             QWidget, QPushButton, QFileDialog, QMessageBox,
                             QHBoxLayout, QVBoxLayout, QGroupBox, QLineEdit, QTextEdit,
                             QListWidget, QToolBar, QStatusBar, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import (QPixmap, QPainter, QPen, QColor, QCursor, QShortcut,
                         QImage, QMouseEvent, QAction, QKeySequence)


class DrawROI:
    """
    Represents a Region of Interest (DrawROI) in an image.
    Allows resizing and moving operations with handles and edges.
    """
    roi_counter = 0

    def __init__(self, start_point: QPoint, end_point: QPoint):
        """
        Initializes the ROI with start and end points.

        :param start_point: QPoint - The starting point of the ROI.
        :param end_point: QPoint - The ending point of the ROI.
        """
        self.start = start_point
        self.end = end_point
        self.selected = False
        self.resize_handle = None
        self.edge_thickness = 2
        self.icon_opacity = 0.1
        self.icon_background_opacity = 0

        self.gear_icon = QPixmap("gear.png")
        self.gear_icon = self.gear_icon.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)

        self.duplicate_icon = QPixmap("duplicate.png")
        self.duplicate_icon = self.duplicate_icon.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio,
                                                         Qt.TransformationMode.SmoothTransformation)

        # Increment the counter and set a unique name
        DrawROI.roi_counter += 1
        self.name = f"ROI_{DrawROI.roi_counter}"
        self.description = ""
        self.tags = []

    # We also need to update the is_on_icon method:
    def is_on_icon(self, point: QPoint, scale_factor: float) -> str:
        """
        Checks if the point is on one of the icons

        :param point: Point in the coordinates of the original image
        :param scale_factor: Current scale factor
        :return: 'gear' or 'duplicate' or None
        """
        # Get the position of the icons
        gear_pos, duplicate_pos, icon_size = self.get_icon_positions(scale_factor)

        # Convert the position of the icons to the scale of the original image
        gear_rect = QRect(
            int(gear_pos.x() / scale_factor),
            int(gear_pos.y() / scale_factor),
            int(icon_size / scale_factor),
            int(icon_size / scale_factor)
        )
        duplicate_rect = QRect(
            int(duplicate_pos.x() / scale_factor),
            int(duplicate_pos.y() / scale_factor),
            int(icon_size / scale_factor),
            int(icon_size / scale_factor)
        )

        if gear_rect.contains(point):
            return 'gear'
        elif duplicate_rect.contains(point):
            return 'duplicate'
        return None

    # In the DrawROI class, we change the get_icon_positions method to this:
    def get_icon_positions(self, scale_factor: float) -> tuple:
        rect = self.get_rect()
        icon_size = int(16 * scale_factor)
        # Place icons above and outside the ROI
        gear_pos = QPoint(
            int(rect.right() * scale_factor) - icon_size - 5,
            int(rect.top() * scale_factor) - icon_size - 5  # Outside ROI
        )
        duplicate_pos = QPoint(
            int(rect.right() * scale_factor) - 2 * (icon_size + 5),
            int(rect.top() * scale_factor) - icon_size - 5  # Outside ROI
        )
        return gear_pos, duplicate_pos, icon_size

    def get_rect(self) -> QRect:
        """
        Returns the normalized QRect representation of the ROI.
        """
        return QRect(self.start, self.end).normalized()

    def contains(self, point: QPoint) -> bool:
        """
        Checks if a point is inside the ROI, excluding the resize handles.

        :param point: QPoint - The point to check.
        :return: bool - True if the point is inside the ROI, False otherwise.
        """
        rect = self.get_rect()
        handles = self.get_handles(self.edge_thickness)
        for handle_rect in handles.values():
            if handle_rect.contains(point):
                return False
        return rect.contains(point)

    def get_handles(self, handle_size: int = 2) -> dict:
        """
        Returns the resize handles as small QRect regions at each corner.

        :param handle_size: int - The size of the handles.
        :return: dict - A dictionary of handle names and their corresponding QRect.
        """
        rect = self.get_rect()
        return {
            'top_left': QRect(
                rect.left() - handle_size // 2,
                rect.top() - handle_size // 2,
                handle_size,
                handle_size
            ),
            'top_right': QRect(
                rect.right() - handle_size // 2,
                rect.top() - handle_size // 2,
                handle_size,
                handle_size
            ),
            'bottom_left': QRect(
                rect.left() - handle_size // 2,
                rect.bottom() - handle_size // 2,
                handle_size,
                handle_size
            ),
            'bottom_right': QRect(
                rect.right() - handle_size // 2,
                rect.bottom() - handle_size // 2,
                handle_size,
                handle_size
            )
        }

    def is_on_handle(self, point: QPoint, handle_size: int = 6) -> str or None:
        """
        Checks if a point is on any of the resize handles.

        :param point: QPoint - The point to check.
        :param handle_size: int - The size of the handles.
        :return: str | None - The name of the handle if the point is on one, else None.
        """
        handles = self.get_handles(handle_size)
        for handle_name, handle_rect in handles.items():
            if handle_rect.contains(point):
                return handle_name
        return None

    def is_near_edge(self, point: QPoint) -> str or None:
        """
        Checks if a point is near any edge of the ROI.

        :param point: QPoint - The point to check.
        :return: str | None - The name of the edge if the point is near one, else None.
        """
        rect = self.get_rect()
        handles = self.get_handles(self.edge_thickness)

        for handle_name, handle_rect in handles.items():
            if handle_rect.contains(point):
                return handle_name

        left_edge = QRect(rect.left() - self.edge_thickness // 2, rect.top(), self.edge_thickness, rect.height())
        right_edge = QRect(rect.right() - self.edge_thickness // 2, rect.top(), self.edge_thickness, rect.height())
        top_edge = QRect(rect.left(), rect.top() - self.edge_thickness // 2, rect.width(), self.edge_thickness)
        bottom_edge = QRect(rect.left(), rect.bottom() - self.edge_thickness // 2, rect.width(), self.edge_thickness)

        if left_edge.contains(point):
            return 'left'
        elif right_edge.contains(point):
            return 'right'
        elif top_edge.contains(point):
            return 'top'
        elif bottom_edge.contains(point):
            return 'bottom'

        return None

    def get_cursor_shape(self, point: QPoint) -> Qt.CursorShape:
        """
        Determines the appropriate cursor shape based on the mouse position.

        :param point: QPoint - The current mouse position.
        :return: Qt.CursorShape - The appropriate cursor shape.
        """
        edge = self.is_near_edge(point)

        if edge in ['top_left', 'bottom_right']:
            return Qt.CursorShape.SizeFDiagCursor  # Diagonal ↘↖
        elif edge in ['top_right', 'bottom_left']:
            return Qt.CursorShape.SizeBDiagCursor  # Diagonal ↙↗
        elif edge in ['left', 'right']:
            return Qt.CursorShape.SizeHorCursor  # Horizontal ↔
        elif edge in ['top', 'bottom']:
            return Qt.CursorShape.SizeVerCursor  # Vertical ↕
        elif self.contains(point):
            return Qt.CursorShape.SizeAllCursor  # Move ✥

        return Qt.CursorShape.CrossCursor  # Default cross cursor

    def to_dict(self):
        """
        Converts the ROI to a dictionary format.

        :return: dict - The dictionary representation of the ROI.
        """
        return {
            'start': {'x': self.start.x(), 'y': self.start.y()},
            'end': {'x': self.end.x(), 'y': self.end.y()},
            'name': self.name,
            'description': self.description,
            'tags': self.tags
        }

    @classmethod
    def reset_counter(cls):
        """Reset the ROI counter to zero"""
        cls.roi_counter = 0

    @classmethod
    def from_dict(cls, data):
        roi = cls(
            QPoint(data['start']['x'], data['start']['y']),
            QPoint(data['end']['x'], data['end']['y'])
        )
        roi.name = data.get('name', f'ROI_{cls.roi_counter}')
        roi.description = data.get('description', '')
        roi.tags = data.get('tags', [])
        return roi


class ROIEditorDialog(QDialog):
    def __init__(self, roi: DrawROI, parent=None):
        super().__init__(parent)
        self.roi = roi
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Edit ROI")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        name_group = QGroupBox("Name and information")
        name_layout = QVBoxLayout()

        name_label = QLabel("Name:")
        self.name_edit = QLineEdit(self.roi.name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)

        coords_label = QLabel(f"Coordinate:")
        rect = self.roi.get_rect()
        coords_text = f"X: {rect.x()}, Y: {rect.y()}\nWidth: {rect.width()}, Height: {rect.height()}"
        coords_display = QLabel(coords_text)
        coords_display.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        name_layout.addWidget(coords_label)
        name_layout.addWidget(coords_display)

        name_group.setLayout(name_layout)
        layout.addWidget(name_group)

        desc_group = QGroupBox("Information")
        desc_layout = QVBoxLayout()
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.roi.description)
        self.desc_edit.setMaximumHeight(100)
        desc_layout.addWidget(self.desc_edit)
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout()

        tags_input_layout = QHBoxLayout()
        self.tag_edit = QLineEdit()
        add_tag_btn = QPushButton("Add")
        add_tag_btn.clicked.connect(self.add_tag)
        tags_input_layout.addWidget(self.tag_edit)
        tags_input_layout.addWidget(add_tag_btn)

        self.tags_list = QListWidget()
        self.tags_list.addItems(self.roi.tags)
        remove_tag_btn = QPushButton("Delete selected tag")
        remove_tag_btn.clicked.connect(self.remove_tag)

        tags_layout.addLayout(tags_input_layout)
        tags_layout.addWidget(self.tags_list)
        tags_layout.addWidget(remove_tag_btn)

        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_tag(self):
        tag = self.tag_edit.text().strip()
        if tag and tag not in self.roi.tags:
            self.tags_list.addItem(tag)
            self.tag_edit.clear()

    def remove_tag(self):
        current_item = self.tags_list.currentItem()
        if current_item:
            self.tags_list.takeItem(self.tags_list.row(current_item))

    def accept(self):
        self.roi.name = self.name_edit.text()
        self.roi.description = self.desc_edit.toPlainText()
        self.roi.tags = [self.tags_list.item(i).text()
                         for i in range(self.tags_list.count())]
        super().accept()


class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setObjectName("MainWindow")
        self.setFixedSize(1280, 720)
        self.centralwidget = QWidget(parent=self)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.scrollArea = QScrollArea(parent=self.centralwidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 1182, 631))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.horizontalLayout_2 = QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.image_label = QLabel(parent=self.scrollAreaWidgetContents)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding,
                                           QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.image_label.sizePolicy().hasHeightForWidth())
        self.image_label.setSizePolicy(sizePolicy)
        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.image_label.setObjectName("image_label")
        self.horizontalLayout_2.addWidget(self.image_label)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.horizontalLayout.addWidget(self.scrollArea)
        self.setCentralWidget(self.centralwidget)

        self.statusBar = QStatusBar(parent=self)
        self.statusBar.setObjectName("statusbar")
        self.setStatusBar(self.statusBar)

        # Required variables
        self.image = None
        self.image_path = None
        self.drawing = False
        self.roi_list = []
        self.selected_roi = None
        self.last_point = None
        self.resize_handle = None
        self.scale_factor = 1.0

        # Set the mouse cursor to +
        self.image_label.setCursor(Qt.CursorShape.CrossCursor)

        # Install event filters
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.mousePressEvent
        self.image_label.mouseMoveEvent = self.mouseMoveEvent
        self.image_label.mouseReleaseEvent = self.mouseReleaseEvent
        self.image_label.mouseDoubleClickEvent = self.mouseDoubleClickEvent

        self.create_toolbar()
        self.create_shortcuts()

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        open_action = QAction('Import Picture', self)
        open_action.triggered.connect(self.open_image)
        toolbar.addAction(open_action)

        save_roi_action = QAction('Save ROI', self)
        save_roi_action.triggered.connect(self.save_rois)
        toolbar.addAction(save_roi_action)

        load_roi_action = QAction('Load ROI', self)
        load_roi_action.triggered.connect(self.load_rois)
        toolbar.addAction(load_roi_action)

        toolbar.addSeparator()

        delete_roi_action = QAction('Delete Selected ROI', self)
        delete_roi_action.triggered.connect(self.delete_selected_roi)
        toolbar.addAction(delete_roi_action)

        clear_rois_action = QAction('Delete All ROI', self)
        clear_rois_action.triggered.connect(self.clear_rois)
        toolbar.addAction(clear_rois_action)

        toolbar.addSeparator()

        zoom_in_action = QAction('Zoom in', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        fit_screen_action = QAction('Scal Monitor', self)
        fit_screen_action.triggered.connect(self.fit_to_screen)
        toolbar.addAction(fit_screen_action)

    def create_shortcuts(self):
        QShortcut(QKeySequence('Ctrl+O'), self, self.open_image)
        QShortcut(QKeySequence('Ctrl+S'), self, self.save_rois)
        QShortcut(QKeySequence('Ctrl+L'), self, self.load_rois)
        QShortcut(QKeySequence('Delete'), self, self.delete_selected_roi)
        QShortcut(QKeySequence('Ctrl+Delete'), self, self.clear_rois)
        QShortcut(QKeySequence('Ctrl++'), self, self.zoom_in)
        QShortcut(QKeySequence('Ctrl+-'), self, self.zoom_out)
        QShortcut(QKeySequence('Ctrl+F'), self, self.fit_to_screen)

    def open_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Chose Picture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_name:
            self.image_path = file_name
            self.image = QImage(file_name)
            if self.image.isNull():
                QMessageBox.critical(self, "Error", "Can not load image")
                return

            self.scale_factor = 1.0
            self.fit_to_screen()
            self.roi_list.clear()
            DrawROI.reset_counter()
            self.update_status()

    def save_rois(self):
        if not self.image_path or not self.roi_list:
            QMessageBox.warning(self, "warning", "There is not picture or ROI")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save ROI's",
            "",
            "JSON Files (*.json)"
        )

        if file_name:
            data = {
                'image_path': self.image_path,
                'rois': [roi.to_dict() for roi in self.roi_list]
            }

            try:
                with open(file_name, 'w') as f:
                    json.dump(data, f)
                self.statusBar.showMessage("Save all ROI's", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Not save ROI: {str(e)}")

    def load_rois(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load ROI's",
            "",
            "JSON Files (*.json)"
        )

        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)

                # Image matching check
                if self.image_path != data['image_path']:
                    reply = QMessageBox.question(
                        self,
                        "Warning",
                        "The current image is different from the saved image. Do you want to upload a new image?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.image = QImage(data['image_path'])
                        if self.image.isNull():
                            raise Exception("Can not Load Picture")
                        self.image_path = data['image_path']
                        self.fit_to_screen()

                self.roi_list = [DrawROI.from_dict(roi_data) for roi_data in data['rois']]
                self.selected_roi = None
                self.update_image()
                self.statusBar.showMessage("Successfully loaded ROI's", 3000)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Can not Load ROI: {str(e)}")

    def delete_selected_roi(self):
        if self.selected_roi in self.roi_list:
            self.roi_list.remove(self.selected_roi)
            self.selected_roi = None
            self.update_image()
            self.update_status()

    def clear_rois(self):
        if self.roi_list:
            reply = QMessageBox.question(
                self,
                "Delete",
                "Are you shore delete all ROI's",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.roi_list.clear()
                self.selected_roi = None
                DrawROI.reset_counter()
                self.update_image()
                self.update_status()

    def zoom_in(self):
        self.scale_image(1.25)

    def zoom_out(self):
        self.scale_image(0.8)

    def scale_image(self, factor):
        if not self.image:
            return

        self.scale_factor *= factor
        self.update_image()
        self.update_status()

    def fit_to_screen(self):
        if not self.image:
            return

        # Calculate the appropriate scale to display the full image
        label_size = self.image_label.size()
        scaled_width = label_size.width()
        scaled_height = label_size.height()

        self.scale_factor = min(
            scaled_width / self.image.width(),
            scaled_height / self.image.height()
        )

        self.update_image()
        self.update_status()

    def map_to_image_coordinates(self, pos: QPoint) -> QPoint:
        """
        Converts mouse coordinates from QLabel space to the original image scale,
        assuming the image is aligned to the top-left corner.

        :param pos: QPoint - The position of the mouse event in QLabel coordinates
        :return: QPoint - The corresponding position in the original image coordinates
        """
        if not self.image or not self.image_label.pixmap():
            return pos

        # Get the current scaled dimensions
        scaled_width = int(self.image.width() * self.scale_factor)
        scaled_height = int(self.image.height() * self.scale_factor)

        # Since image is left-top aligned, we don't need offset calculations
        # Just check if the click is within the scaled image bounds
        if (pos.x() < 0 or pos.x() >= scaled_width or
                pos.y() < 0 or pos.y() >= scaled_height):
            return None

        # Convert directly to original image coordinates
        original_x = int(pos.x() / self.scale_factor)
        original_y = int(pos.y() / self.scale_factor)

        # Ensure coordinates are within original image bounds
        original_x = max(0, min(original_x, self.image.width() - 1))
        original_y = max(0, min(original_y, self.image.height() - 1))

        return QPoint(original_x, original_y)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.image_label.pixmap():
            return

        try:
            pos = self.map_to_image_coordinates(event.pos())
            # If the mouse is outside the image area
            if pos is None:
                return
            clicked_on_existing = False

            # Check icon clicks for selected ROI
            if self.selected_roi:
                icon_clicked = self.selected_roi.is_on_icon(pos, self.scale_factor)
                if icon_clicked == 'gear':
                    # Open the edit window
                    dialog = ROIEditorDialog(self.selected_roi, self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        self.update_image()
                        self.update_status()
                    return
                elif icon_clicked == 'duplicate':
                    # Create a copy of the ROI
                    offset = 10
                    new_roi = DrawROI(
                        QPoint(self.selected_roi.start.x() + offset, self.selected_roi.start.y() + offset),
                        QPoint(self.selected_roi.end.x() + offset, self.selected_roi.end.y() + offset)
                    )
                    #new_roi.name = f"Copy_of_{self.selected_roi.name}"
                    new_roi.description = self.selected_roi.description
                    new_roi.tags = self.selected_roi.tags.copy()
                    self.roi_list.append(new_roi)
                    self.selected_roi = new_roi
                    self.update_image()
                    self.update_status()
                    return

            # Check existing ROI clicks
            for roi in self.roi_list:
                handle = roi.is_on_handle(pos)
                if handle:
                    self.resize_handle = handle
                    self.selected_roi = roi
                    self.last_point = pos
                    clicked_on_existing = True
                    self.update_image()
                    self.update_status()
                    break

                # Check edges
                edge = roi.is_near_edge(pos)
                if edge:
                    # Set the resize handle for the edges
                    self.resize_handle = edge
                    self.selected_roi = roi
                    self.last_point = pos
                    clicked_on_existing = True
                    self.update_image()
                    self.update_status()
                    break

                if roi.contains(pos):
                    self.selected_roi = roi
                    self.last_point = pos
                    clicked_on_existing = True
                    self.update_image()
                    self.update_status()
                    break

            # Create a new ROI only if no existing ROI has been clicked on.
            if not clicked_on_existing:
                self.drawing = True
                self.selected_roi = DrawROI(pos, pos)
                self.roi_list.append(self.selected_roi)
                self.resize_handle = None
                self.update_status()

        except Exception as e:
            print(f"[mousePressEvent] {e}")

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.image_label.pixmap():
            return

        try:
            pos = self.map_to_image_coordinates(event.pos())
            # If the mouse is outside the image area
            if pos is None:
                return

            # Adjust mouse cursor shape based on positio
            cursor_updated = False

            # Mouse over icons for selected ROI
            if self.selected_roi:
                icon_type = self.selected_roi.is_on_icon(pos, self.scale_factor)
                if icon_type:
                    self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.selected_roi.icon_background_opacity = 150
                    self.selected_roi.icon_opacity = 0.9
                    cursor_updated = True
                else:
                    self.selected_roi.icon_background_opacity = 0
                    self.selected_roi.icon_opacity = 0.2

            if not cursor_updated:
                # Check other mouse modes (same as before)
                for roi in self.roi_list:
                    handle = roi.is_on_handle(pos)
                    edge = roi.is_near_edge(pos)

                    if handle or edge:
                        cursor_updated = True
                        self.image_label.setCursor(roi.get_cursor_shape(pos))
                        break

                    elif roi.contains(pos):
                        cursor_updated = True
                        self.image_label.setCursor(Qt.CursorShape.SizeAllCursor)
                        break

                if not cursor_updated:
                    self.image_label.setCursor(Qt.CursorShape.CrossCursor)

            # Resize or move ROI
            if self.drawing:
                self.selected_roi.end = pos

            elif self.selected_roi and self.last_point:
                if self.resize_handle:
                    # Change ROI size
                    dx = pos.x() - self.last_point.x()
                    dy = pos.y() - self.last_point.y()

                    if self.resize_handle == 'top_left':
                        self.selected_roi.start += QPoint(dx, dy)
                    elif self.resize_handle == 'top_right':
                        self.selected_roi.start.setY(self.selected_roi.start.y() + dy)
                        self.selected_roi.end.setX(self.selected_roi.end.x() + dx)
                    elif self.resize_handle == 'bottom_left':
                        self.selected_roi.start.setX(self.selected_roi.start.x() + dx)
                        self.selected_roi.end.setY(self.selected_roi.end.y() + dy)
                    elif self.resize_handle == 'bottom_right':
                        self.selected_roi.end += QPoint(dx, dy)
                    elif self.resize_handle == 'left':
                        self.selected_roi.start.setX(self.selected_roi.start.x() + dx)
                    elif self.resize_handle == 'right':
                        self.selected_roi.end.setX(self.selected_roi.end.x() + dx)
                    elif self.resize_handle == 'top':
                        self.selected_roi.start.setY(self.selected_roi.start.y() + dy)
                    elif self.resize_handle == 'bottom':
                        self.selected_roi.end.setY(self.selected_roi.end.y() + dy)

                    self.selected_roi.get_rect()  # Normalize the rectangle

                else:
                    # ROI relocation
                    dx = pos.x() - self.last_point.x()
                    dy = pos.y() - self.last_point.y()
                    self.selected_roi.start += QPoint(dx, dy)
                    self.selected_roi.end += QPoint(dx, dy)

                self.last_point = pos

            self.update_image()
            self.update_status()

        except Exception as e:
            print(f"[mouseMoveEvent] {e}")

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.drawing = False
        self.resize_handle = None
        self.last_point = None
        self.update_status()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self.image_label.pixmap():
            return

        # Convert mouse coordinates to original image coordinates
        pos = self.map_to_image_coordinates(event.pos())
        if pos is None:
            return

        # If the icons are not clicked, check the click on the ROI itself
        for roi in self.roi_list:
            if roi.contains(pos):
                self.selected_roi = roi
                dialog = ROIEditorDialog(roi, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.update_image()
                    self.update_status()
                break

    def update_image(self):
        try:
            if not self.image:
                return

            # Calculate scaled dimensions
            scaled_width = int(self.image.width() * self.scale_factor)
            scaled_height = int(self.image.height() * self.scale_factor)

            # Create a pixmap with scaled size
            temp_pixmap = QPixmap.fromImage(self.image).scaled(
                scaled_width,
                scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            painter = QPainter(temp_pixmap)

            for roi in self.roi_list:

                if roi == self.selected_roi:
                    pen = QPen(QColor(255, 0, 0), 2)
                else:
                    pen = QPen(QColor(0, 255, 0), 2)
                painter.setPen(pen)

                # Convert ROI coordinates to pixmap space
                rect = roi.get_rect()
                scaled_rect = QRect(
                    int(rect.x() * self.scale_factor),
                    int(rect.y() * self.scale_factor),
                    int(rect.width() * self.scale_factor),
                    int(rect.height() * self.scale_factor)
                )

                painter.drawRect(scaled_rect)

                # Draw resize handles for the selected ROI
                if roi == self.selected_roi:
                    handle_size = 6
                    for point in [scaled_rect.topLeft(), scaled_rect.topRight(),
                                  scaled_rect.bottomLeft(), scaled_rect.bottomRight()]:
                        # Draw ROI handles
                        painter.fillRect(
                            point.x() - handle_size // 2,
                            point.y() - handle_size // 2,
                            handle_size, handle_size,
                            QColor(255, 0, 0)
                        )

                        # Show icons
                        gear_pos, duplicate_pos, icon_size = roi.get_icon_positions(self.scale_factor)

                        # Draw a semi-transparent background for icons
                        painter.setOpacity(roi.icon_opacity)
                        painter.fillRect(
                            gear_pos.x(), gear_pos.y(),
                            icon_size, icon_size,
                            QColor(255, 255, 255, roi.icon_background_opacity)
                        )
                        painter.fillRect(
                            duplicate_pos.x(), duplicate_pos.y(),
                            icon_size, icon_size,
                            QColor(255, 255, 255, roi.icon_background_opacity)
                        )
                        painter.setOpacity(1.0)

                        # Drawing icons
                        painter.drawPixmap(gear_pos.x(), gear_pos.y(), icon_size, icon_size, roi.gear_icon)
                        painter.drawPixmap(duplicate_pos.x(), duplicate_pos.y(), icon_size, icon_size,
                                           roi.duplicate_icon)

                        # Draw ROI name
                        font = painter.font()
                        font.setBold(True)
                        painter.setFont(font)
                        name_rect = QRect(
                            scaled_rect.x(),
                            scaled_rect.y() - 20,  # High ROI
                            scaled_rect.width(),
                            20
                        )
                        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, roi.name)

            painter.end()
            self.image_label.setPixmap(temp_pixmap)

        except Exception as e:
            print(f"[update_image] {e}")

    def update_status(self):
        """Update status bar with useful information"""
        try:
            if not self.image:
                self.statusBar.showMessage("Image not loaded.")
                return

            status = f"Image dimensions: {self.image.width()}×{self.image.height()} | "
            status += f"Zoom: {self.scale_factor:.2f}× | "
            status += f"Number of ROIs:{len(self.roi_list)}"

            if self.selected_roi:
                rect = self.selected_roi.get_rect()
                status += f" | ROI: {self.selected_roi.name} "
                status += f"({rect.x()}, {rect.y()}, {rect.width()}, {rect.height()})"
                if self.selected_roi.tags:
                    status += f" | Tags: {', '.join(self.selected_roi.tags)}"

            self.statusBar.showMessage(status)
        except Exception as e:
            print(f"[update_status] {e}")

    def resizeEvent(self, event):
        """Window resize management"""
        super().resizeEvent(event)
        if self.image:
            self.fit_to_screen()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageProcessor()
    ex.show()
    sys.exit(app.exec())