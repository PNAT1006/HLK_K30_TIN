import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget,
    QStackedWidget, QMessageBox
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt
from screeninfo import get_monitors

screen = get_monitors()[0]
sw, sh = screen.width, screen.height


class Image_Processing(QWidget):
    def __init__(self):
        super().__init__()
        pass


class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        # 2 nút
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

        # Kích thước nút
        bw = int(w * self.btn_w_ratio)
        bh = int(h * self.btn_h_ratio)
        bw = max(self.min_btn_w, min(bw, self.max_btn_w))
        bh = max(self.min_btn_h, min(bh, self.max_btn_h))

        # Font theo chiều cao nút
        fs = max(9, int(bh * 0.4))
        f = QFont()
        f.setPointSize(fs)
        self.btn1.setFont(f)
        self.btn2.setFont(f)

        # Khoảng cách
        spacing = max(12, int(w * self.spacing_ratio))

        # Tính vị trí căn giữa
        total_w = bw * 2 + spacing
        x0 = max(0, (w - total_w) // 2)
        y0 = max(0, (h - bh) // 2)

        # Đặt geometry
        self.btn1.setGeometry(x0, y0, bw, bh)
        self.btn2.setGeometry(x0 + bw + spacing, y0, bw, bh)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo Application")
        self.setWindowIcon(QIcon("icon.png"))
        # Kích thước cửa sổ = 80% màn hình, căn giữa
        w = int(sw * 0.8)
        h = int(sh * 0.8)
        x = screen.x + (sw - w) // 2
        y = screen.y + (sh - h) // 2
        self.setGeometry(x, y, w, h)

        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        # Trang 0: menu chính
        self.page_main = MainMenu()
        self.stack.addWidget(self.page_main)
        # Trang 1: xử lý ảnh
        self.page_image = Image_Processing()
        self.stack.addWidget(self.page_image)
        # Trang 2: chưa làm gì hết, tính nhập vô đề bài vô



        # event
        self.page_main.btn1.clicked.connect(self.event_button_1)
        self.page_main.btn2.clicked.connect(lambda: QMessageBox.information(self, "Thông báo", "Bấm Thằng cha mày"))

    def event_button_1(self):
        self.stack.setCurrentWidget(self.page_image)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
