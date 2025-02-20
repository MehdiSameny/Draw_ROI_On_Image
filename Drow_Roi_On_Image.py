import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QSizePolicy, QScrollArea,
                             QWidget, QPushButton, QFileDialog, QMessageBox,
                             QHBoxLayout, QMenu, QToolBar, QStatusBar)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import (QPixmap, QPainter, QPen, QColor, QCursor, QShortcut,
                         QImage, QMouseEvent, QAction, QKeySequence)



class DrawROI:
    """
    Represents a Region of Interest (DrawROI) in an image.
    Allows resizing and moving operations with handles and edges.
    """
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
            'end': {'x': self.end.x(), 'y': self.end.y()}
        }

    @classmethod
    def from_dict(cls, data):
        """
        Creates an ROI instance from a dictionary.

        :param data: dict - The dictionary containing ROI data.
        :return: ROI - The reconstructed ROI instance.
        """
        start = QPoint(data['start']['x'], data['start']['y'])
        end = QPoint(data['end']['x'], data['end']['y'])
        return cls(start, end)



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

        # متغیرهای مورد نیاز
        self.image = None
        self.image_path = None
        self.drawing = False
        self.roi_list = []
        self.selected_roi = None
        self.last_point = None
        self.resize_handle = None
        self.scale_factor = 1.0

        # تنظیم نشانگر ماوس به شکل +
        self.image_label.setCursor(Qt.CursorShape.CrossCursor)

        # نصب event filters
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.mousePressEvent
        self.image_label.mouseMoveEvent = self.mouseMoveEvent
        self.image_label.mouseReleaseEvent = self.mouseReleaseEvent

        self.create_toolbar()
        # اضافه کردن کلیدهای میانبر
        self.create_shortcuts()

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # دکمه‌های نوار ابزار
        open_action = QAction('باز کردن تصویر', self)
        open_action.triggered.connect(self.open_image)
        toolbar.addAction(open_action)

        save_roi_action = QAction('ذخیره ROIها', self)
        save_roi_action.triggered.connect(self.save_rois)
        toolbar.addAction(save_roi_action)

        load_roi_action = QAction('بارگذاری ROIها', self)
        load_roi_action.triggered.connect(self.load_rois)
        toolbar.addAction(load_roi_action)

        toolbar.addSeparator()

        delete_roi_action = QAction('حذف ROI انتخاب شده', self)
        delete_roi_action.triggered.connect(self.delete_selected_roi)
        toolbar.addAction(delete_roi_action)

        clear_rois_action = QAction('حذف همه ROIها', self)
        clear_rois_action.triggered.connect(self.clear_rois)
        toolbar.addAction(clear_rois_action)

        toolbar.addSeparator()

        zoom_in_action = QAction('بزرگنمایی', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction('کوچکنمایی', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        fit_screen_action = QAction('تناسب با صفحه', self)
        fit_screen_action.triggered.connect(self.fit_to_screen)
        toolbar.addAction(fit_screen_action)

    def create_shortcuts(self):
        # کلیدهای میانبر
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
            "انتخاب تصویر",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_name:
            self.image_path = file_name
            self.image = QImage(file_name)
            if self.image.isNull():
                QMessageBox.critical(self, "خطا", "خطا در بارگذاری تصویر")
                return

            self.scale_factor = 1.0
            self.fit_to_screen()
            self.roi_list.clear()
            self.update_status()

    def save_rois(self):
        if not self.image_path or not self.roi_list:
            QMessageBox.warning(self, "هشدار", "تصویر یا ROI برای ذخیره وجود ندارد")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره ROIها",
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
                self.statusBar.showMessage("ROIها با موفقیت ذخیره شدند", 3000)
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ذخیره ROIها: {str(e)}")

    def load_rois(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "بارگذاری ROIها",
            "",
            "JSON Files (*.json)"
        )

        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)

                # بررسی تطابق تصویر
                if self.image_path != data['image_path']:
                    reply = QMessageBox.question(
                        self,
                        "هشدار",
                        "تصویر فعلی با تصویر ذخیره شده متفاوت است. آیا مایل به بارگذاری تصویر جدید هستید؟",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.image = QImage(data['image_path'])
                        if self.image.isNull():
                            raise Exception("خطا در بارگذاری تصویر")
                        self.image_path = data['image_path']
                        self.fit_to_screen()

                self.roi_list = [DrawROI.from_dict(roi_data) for roi_data in data['rois']]
                self.selected_roi = None
                self.update_image()
                self.statusBar.showMessage("ROIها با موفقیت بارگذاری شدند", 3000)

            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در بارگذاری ROIها: {str(e)}")

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
                "تأیید حذف",
                "آیا مطمئن هستید که می‌خواهید تمام ROIها را حذف کنید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.roi_list.clear()
                self.selected_roi = None
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

            # محاسبه مقیاس مناسب برای نمایش کامل تصویر
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
            if pos is None:  # اگر ماوس خارج از محدوده تصویر باشد
                return
            clicked_on_existing = False

            # بررسی کلیک روی ROI موجود
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

                edge = roi.is_near_edge(pos)  # بررسی لبه‌ها
                if edge:
                    self.resize_handle = edge  # مقداردهی دستگیره تغییر اندازه برای لبه‌ها
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

            # فقط در صورتی که روی هیچ ROI موجودی کلیک نشده باشد، ROI جدید ایجاد کن
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
            if pos is None:  # اگر ماوس خارج از محدوده تصویر باشد
                return

            # تنظیم شکل نشانگر موس بر اساس موقعیت
            cursor_updated = False
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

            # تغییر اندازه یا جابجایی ROI
            if self.drawing:
                self.selected_roi.end = pos
                self.update_image()

            elif self.selected_roi and self.last_point:
                if self.resize_handle:
                    # تغییر اندازه ROI
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
                    self.update_image()

                else:
                    # جابجایی ROI
                    dx = pos.x() - self.last_point.x()
                    dy = pos.y() - self.last_point.y()
                    self.selected_roi.start += QPoint(dx, dy)
                    self.selected_roi.end += QPoint(dx, dy)
                    self.update_image()

                self.last_point = pos
                self.update_status()

        except Exception as e:
            print(f"[mouseMoveEvent] {e}")

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.drawing = False
        self.resize_handle = None
        self.last_point = None
        self.update_status()

    def update_image(self):
        try:
            if not self.image:
                return

            # محاسبه ابعاد مقیاس شده
            scaled_width = int(self.image.width() * self.scale_factor)
            scaled_height = int(self.image.height() * self.scale_factor)

            # ایجاد pixmap با اندازه مقیاس شده
            temp_pixmap = QPixmap.fromImage(self.image).scaled(
                scaled_width,
                scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            painter = QPainter(temp_pixmap)

            for roi in self.roi_list:
                if roi == self.selected_roi:
                    pen = QPen(QColor(255, 0, 0), 2)  # قرمز برای ROI انتخاب شده
                else:
                    pen = QPen(QColor(0, 255, 0), 2)  # سبز برای سایر ROIها
                painter.setPen(pen)

                # تبدیل مختصات ROI به فضای pixmap
                rect = roi.get_rect()
                scaled_rect = QRect(
                    int(rect.x() * self.scale_factor),
                    int(rect.y() * self.scale_factor),
                    int(rect.width() * self.scale_factor),
                    int(rect.height() * self.scale_factor)
                )

                painter.drawRect(scaled_rect)

                # رسم دستگیره‌های تغییر اندازه برای ROI انتخاب شده
                if roi == self.selected_roi:
                    handle_size = 6
                    for point in [scaled_rect.topLeft(), scaled_rect.topRight(),
                                  scaled_rect.bottomLeft(), scaled_rect.bottomRight()]:
                        painter.fillRect(
                            point.x() - handle_size // 2,
                            point.y() - handle_size // 2,
                            handle_size, handle_size,
                            QColor(255, 0, 0)
                        )

            painter.end()
            self.image_label.setPixmap(temp_pixmap)

        except Exception as e:
            print(f"[update_image] {e}")

    def update_status(self):
        """به‌روزرسانی نوار وضعیت با اطلاعات مفید"""
        try:
            if not self.image:
                self.statusBar.showMessage("تصویری بارگذاری نشده است")
                return

            status = f"ابعاد تصویر: {self.image.width()}×{self.image.height()} | "
            status += f"بزرگنمایی: {self.scale_factor:.2f}× | "
            status += f"تعداد ROIها: {len(self.roi_list)}"

            if self.selected_roi:
                rect = self.selected_roi.get_rect()
                status += f" | ROI انتخاب شده: ({rect.x()}, {rect.y()}, {rect.width()}, {rect.height()})"

            self.statusBar.showMessage(status)
        except Exception as e:
            print(f"[update_status] {e}")

    def resizeEvent(self, event):
        """مدیریت تغییر اندازه پنجره"""
        super().resizeEvent(event)
        if self.image:
            self.fit_to_screen()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageProcessor()
    ex.show()
    sys.exit(app.exec())