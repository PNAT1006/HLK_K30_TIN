import sys
import csv
import cv2
import numpy as np
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget,
    QStackedWidget, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QIcon, QFont, QPixmap, QImage, QColor
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint

# --- Lấy thông tin màn hình (fallback nếu thiếu screeninfo) ---
try:
    from screeninfo import get_monitors
    _screen = get_monitors()[0]
    SW, SH, SX, SY = _screen.width, _screen.height, _screen.x, _screen.y
except Exception:
    SW, SH, SX, SY = 1280, 800, 0, 0

# --- ĐƯỜNG DẪN LƯU CSV CỐ ĐỊNH ---
EXPORT_DIR = Path(__file__).resolve().parent / "exports"
EXPORT_CSV = EXPORT_DIR / "boxes.csv"


# ====================== WIDGET PHỤ ======================
class ClickableLabel(QLabel):
    clicked = pyqtSignal(QPoint)
    moved   = pyqtSignal(QPoint)

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.moved.emit(event.position().toPoint())
        super().mouseMoveEvent(event)


class AspectRatioView(QWidget):
    """Giữ tỉ lệ w/h mục tiêu cho vùng hiển thị ảnh (bọc QLabel)."""
    def __init__(self, label: QLabel, ratio: float = 16/9):
        super().__init__()
        self.label = label
        self.target_ratio = ratio
        self.label.setParent(self)

    def set_ratio(self, ratio: float):
        self.target_ratio = max(0.1, ratio)
        self.update()

    def resizeEvent(self, event):
        W, H = self.width(), self.height()
        if H == 0:
            return
        r = self.target_ratio
        if W / H > r:
            child_h = H
            child_w = int(child_h * r)
        else:
            child_w = W
            child_h = int(child_w / r)
        x = (W - child_w) // 2
        y = (H - child_h) // 2
        self.label.setGeometry(QRect(x, y, child_w, child_h))
        super().resizeEvent(event)


# ====================== RECT MANAGER (tách riêng logic vẽ) ======================
class RectManager:
    """
    Quản lý & vẽ các hình chữ nhật (axis-aligned) theo toạ độ label.
    - rects: list[(x1,y1,x2,y2)]
    - active: đang bật chế độ vẽ
    - start: góc đầu (sau click 1) hoặc None
    - preview_end: điểm hiện tại để hiển thị preview
    """
    def __init__(self):
        self.rects: list[tuple[int, int, int, int]] = []
        self.active: bool = False
        self.start: tuple[int, int] | None = None
        self.preview_end: tuple[int, int] | None = None

    def reset(self):
        self.rects.clear()
        self.start = None
        self.preview_end = None

    def toggle(self, state: bool):
        self.active = state
        if not state:
            self.start = None
            self.preview_end = None

    def start_rect(self, x: int, y: int):
        if not self.active:
            return
        self.start = (x, y)
        self.preview_end = (x, y)

    def update_preview(self, x: int, y: int):
        if self.active and self.start is not None:
            self.preview_end = (x, y)

    def commit(self, x: int, y: int):
        if not self.active or self.start is None:
            return
        x1, y1 = self.start
        x2, y2 = x, y
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        if abs(x2 - x1) >= 2 and abs(y2 - y1) >= 2:
            self.rects.append((x1, y1, x2, y2))
        self.start = None
        self.preview_end = None

    def delete_last(self):
        if self.rects:
            self.rects.pop()

    def render(self, disp: np.ndarray):
        # Vẽ rect đã chốt (xanh lá)
        for (x1, y1, x2, y2) in self.rects:
            cv2.rectangle(disp, (x1, y1), (x2, y2), (0, 220, 0), 2)
            for (cx, cy) in [(x1, y1), (x1, y2), (x2, y1), (x2, y2)]:
                cv2.circle(disp, (cx, cy), 4, (0, 200, 0), -1)
        # Preview (vàng) khi đang kéo
        if self.start is not None and self.preview_end is not None:
            x1, y1 = self.start
            x2, y2 = self.preview_end
            cv2.rectangle(disp, (x1, y1), (x2, y2), (255, 200, 0), 2)
            cv2.circle(disp, (x1, y1), 5, (0, 0, 255), -1)
            cv2.circle(disp, (x2, y2), 5, (0, 0, 255), -1)


# ====================== TRANG XỬ LÝ ẢNH ======================
class Image_Processing(QWidget):
    def __init__(self):
        super().__init__()

        # ----- Vùng ảnh -----
        self.image_label = ClickableLabel("Nhập ảnh từ folder")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #333;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
                color: #222;
                background-color: #f7f7f9;
            }
        """)
        self.aspect_view = AspectRatioView(self.image_label, ratio=16/9)

        # Dữ liệu ảnh & vùng hiển thị
        self.cv_img_orig: np.ndarray | None = None   # ảnh gốc (BGR)
        self.img_rect = (0, 0, 0, 0)                 # (x0, y0, w, h) vùng ảnh thật trong label

        # Quản lý hình chữ nhật
        self.rect_manager = RectManager()

        # ----- Nút -----
        self.btn_open   = QPushButton("Chọn ảnh")
        self.btn_draw   = QPushButton("Chọn Vùng")
        self.btn_draw.setCheckable(True)
        self.btn_del    = QPushButton("Xóa box")
        self.btn_export = QPushButton("Xác nhận")  # Xuất CSV (cố định)

        self._btn_css_static = """
            QPushButton {
                border: none;
                border-radius: 16px;  /* radius sẽ ghi đè động ở resizeEvent */
                padding: 12px 16px;
                font-size: 16px;
                font-weight: 600;
                color: white;
                background-color: #000000;
            }
            QPushButton:hover  { background-color: #1a1a1a; }
            QPushButton:pressed{ background-color: #333333; }
            QPushButton:checked{ background-color: #1a1a1a; }
            QPushButton:disabled { background-color: #555555; color: #cccccc; }
        """
        for b in (self.btn_open, self.btn_draw, self.btn_del, self.btn_export):
            b.setStyleSheet(self._btn_css_static)
            sh = QGraphicsDropShadowEffect(self)
            sh.setBlurRadius(16); sh.setOffset(0, 4); sh.setColor(QColor(0,0,0,120))
            b.setGraphicsEffect(sh)

        # Sự kiện
        self.btn_open.clicked.connect(self.load_image)
        self.btn_draw.toggled.connect(self._toggle_draw_mode)
        self.btn_del.clicked.connect(self._delete_last_rect)
        self.btn_export.clicked.connect(self._export_csv)
        self.image_label.clicked.connect(self._on_image_clicked)
        self.image_label.moved.connect(self._on_image_moved)

        # ----- Layout -----
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.btn_open,   alignment=Qt.AlignmentFlag.AlignTop)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.btn_draw,   alignment=Qt.AlignmentFlag.AlignTop)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.btn_del,    alignment=Qt.AlignmentFlag.AlignTop)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.btn_export, alignment=Qt.AlignmentFlag.AlignTop)
        right_layout.addStretch(1)

        right_widget = QWidget(); right_widget.setLayout(right_layout)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.aspect_view, stretch=8)  # 80%
        main_layout.addWidget(right_widget,   stretch=2)    # 20%

        self._update_buttons_state()

    # ---------------- Utils ----------------
    def _np_to_qpix(self, img_bgr: np.ndarray) -> QPixmap:
        if img_bgr is None:
            return QPixmap()
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        qimg = QImage(img_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def _update_buttons_state(self):
        self.btn_del.setEnabled(len(self.rect_manager.rects) > 0)
        self.btn_export.setEnabled(self.cv_img_orig is not None and len(self.rect_manager.rects) > 0)

    # ---------------- Render: giữ AR gốc, letterbox ----------------
    def _render_display(self):
        if self.cv_img_orig is None:
            return

        lw, lh = self.image_label.width(), self.image_label.height()
        if lw <= 1 or lh <= 1:
            return

        ih, iw = self.cv_img_orig.shape[:2]
        scale = min(lw / iw, lh / ih)
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))

        img_fit = cv2.resize(self.cv_img_orig, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # canvas nền
        disp = np.full((lh, lw, 3), (247, 247, 249), dtype=np.uint8)

        # canh giữa ảnh
        x0 = (lw - new_w) // 2
        y0 = (lh - new_h) // 2
        disp[y0:y0 + new_h, x0:x0 + new_w] = img_fit
        self.img_rect = (x0, y0, new_w, new_h)

        # vẽ rectangles (gồm preview)
        self.rect_manager.render(disp)

        self.image_label.setPixmap(self._np_to_qpix(disp))

    # ---------------- Mapping toạ độ label -> ảnh gốc ----------------
    def _label_to_image_coord(self, xl: int, yl: int) -> tuple[int, int]:
        """Đổi toạ độ trong label (sau letterbox) -> toạ độ ảnh gốc."""
        if self.cv_img_orig is None:
            return 0, 0
        x0, y0, wf, hf = self.img_rect
        ih, iw = self.cv_img_orig.shape[:2]
        # nằm ngoài vùng ảnh -> kẹp vào biên
        xl = max(x0, min(xl, x0 + wf - 1))
        yl = max(y0, min(yl, y0 + hf - 1))
        # tỉ lệ
        sx = (xl - x0) / max(1, wf)
        sy = (yl - y0) / max(1, hf)
        xi = int(round(sx * (iw - 1)))
        yi = int(round(sy * (ih - 1)))
        return xi, yi

    # ---------------- Export CSV (lưu cố định) ----------------
    def _export_csv(self):
        if self.cv_img_orig is None or len(self.rect_manager.rects) == 0:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa có ảnh hoặc chưa có box.")
            return

        try:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with EXPORT_CSV.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header: TL, TR, BR, BL (theo toạ độ ảnh gốc)
                writer.writerow([
                    "index",
                    "tl_x","tl_y",
                    "tr_x","tr_y",
                    "br_x","br_y",
                    "bl_x","bl_y"
                ])
                for idx, (x1l, y1l, x2l, y2l) in enumerate(self.rect_manager.rects, start=1):
                    tl = self._label_to_image_coord(x1l, y1l)
                    tr = self._label_to_image_coord(x2l, y1l)
                    br = self._label_to_image_coord(x2l, y2l)
                    bl = self._label_to_image_coord(x1l, y2l)
                    writer.writerow([idx, tl[0], tl[1], tr[0], tr[1], br[0], br[1], bl[0], bl[1]])

            QMessageBox.information(self, "Thành công", f"Đã lưu CSV tại:\n{EXPORT_CSV}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu CSV:\n{e}")

    # ---------------- Events ----------------
    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if not file:
            return
        img = cv2.imread(file)
        if img is None:
            QMessageBox.warning(self, "Lỗi", "Không mở được ảnh.")
            return
        self.cv_img_orig = img
        self.rect_manager.reset()
        self._update_buttons_state()
        self._render_display()

    def _toggle_draw_mode(self, checked: bool):
        self.rect_manager.toggle(checked)
        self._render_display()

    def _delete_last_rect(self):
        self.rect_manager.delete_last()
        self._update_buttons_state()
        self._render_display()

    def _on_image_clicked(self, pos: QPoint):
        if not self.rect_manager.active or self.cv_img_orig is None:
            return
        x, y = pos.x(), pos.y()
        x0, y0, ww, hh = self.img_rect
        # chỉ nhận click trong vùng ảnh thật
        if not (x0 <= x < x0 + ww and y0 <= y < y0 + hh):
            return

        if self.rect_manager.start is None:
            self.rect_manager.start_rect(x, y)
        else:
            self.rect_manager.commit(x, y)
            self._update_buttons_state()
        self._render_display()

    def _on_image_moved(self, pos: QPoint):
        if not self.rect_manager.active or self.cv_img_orig is None:
            return
        if self.rect_manager.start is None:
            return
        x, y = pos.x(), pos.y()
        x0, y0, ww, hh = self.img_rect
        # clamp vào vùng ảnh thật để preview không vượt
        x = max(x0, min(x, x0 + ww - 1))
        y = max(y0, min(y, y0 + hh - 1))
        self.rect_manager.update_preview(x, y)
        self._render_display()

    def resizeEvent(self, event):
        # cập nhật tỉ lệ khung ảnh = tỉ lệ cửa sổ hiện tại
        w = max(1, self.width())
        h = max(1, self.height())
        self.aspect_view.set_ratio(w / h)

        # nút co giãn & bo góc theo chiều cao
        base_h = max(44, int(h * 0.06))
        radius = max(14, base_h // 3)
        dynamic = f"\nQPushButton{{ border-radius:{radius}px; }}"
        for btn in (self.btn_open, self.btn_draw, self.btn_del, self.btn_export):
            btn.setMinimumHeight(base_h)
            btn.setMaximumHeight(int(base_h * 1.4))
            btn.setStyleSheet(self._btn_css_static + dynamic)

        self._render_display()
        super().resizeEvent(event)


# ====================== MENU CHÍNH ======================
class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.btn1 = QPushButton("Ảnh", self)
        self.btn2 = QPushButton("Viết thủ công", self)

        # Tỉ lệ nút
        self.btn_w_ratio = 0.18
        self.btn_h_ratio = 0.10
        self.spacing_ratio = 0.04

        # Giới hạn min/max
        self.min_btn_w, self.min_btn_h = 80, 36
        self.max_btn_w, self.max_btn_h = 280, 80

    def resizeEvent(self, event):
        self.update_button_positions()
        super().resizeEvent(event)

    def update_button_positions(self):
        w = self.width()
        h = self.height()

        bw = int(w * self.btn_w_ratio)
        bh = int(h * self.btn_h_ratio)
        bw = max(self.min_btn_w, min(bw, self.max_btn_w))
        bh = max(self.min_btn_h, min(bh, self.max_btn_h))

        fs = max(9, int(bh * 0.4))
        f = QFont(); f.setPointSize(fs)
        self.btn1.setFont(f)
        self.btn2.setFont(f)

        spacing = max(12, int(w * self.spacing_ratio))

        total_w = bw * 2 + spacing
        x0 = max(0, (w - total_w) // 2)
        y0 = max(0, (h - bh) // 2)

        self.btn1.setGeometry(x0, y0, bw, bh)
        self.btn2.setGeometry(x0 + bw + spacing, y0, bw, bh)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo Application")
        try:
            self.setWindowIcon(QIcon("icon.png"))
        except Exception:
            pass

        w = int(SW * 0.8)
        h = int(SH * 0.8)
        x = SX + (SW - w) // 2
        y = SY + (SH - h) // 2
        self.setGeometry(x, y, w, h)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.page_main  = MainMenu()
        self.page_image = Image_Processing()

        self.stack.addWidget(self.page_main)   # index 0
        self.stack.addWidget(self.page_image)  # index 1

        self.page_main.btn1.clicked.connect(self.event_button_1)
        self.page_main.btn2.clicked.connect(
            lambda: QMessageBox.information(self, "Thông báo", "Bạn bấm Nút 2")
        )

    def event_button_1(self):
        self.stack.setCurrentWidget(self.page_image)

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()

if __name__ == "__main__":
    main()
