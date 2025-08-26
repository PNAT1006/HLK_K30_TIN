import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt6.QtGui import QIcon, QFont
from screeninfo import get_monitors

screen = get_monitors()[0]
sw, sh = screen.width, screen.height

class Image_Processing(QMainWindow):
    def __init__(self):
        super().__init__()
        pass
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Tên + icon
        self.setWindowTitle("Demo Application")
        self.setWindowIcon(QIcon("icon.png"))

        # Kích thước cửa sổ = 80% màn hình, căn giữa
        w = int(sw * 0.8)
        h = int(sh * 0.8)
        x = screen.x + (sw - w) // 2
        y = screen.y + (sh - h) // 2
        self.setGeometry(x, y, w, h)

        # 2 nút
        self.btn1 = QPushButton("Ảnh", self)
        self.btn2 = QPushButton("Viết thủ công", self)

        # tỉ lệ nút theo kích thước cửa sổ
        self.btn_w_ratio = 0.18   # nút rộng ~18% chiều rộng cửa sổ
        self.btn_h_ratio = 0.10   # nút cao  ~10% chiều cao cửa sổ
        self.spacing_ratio = 0.04 # khoảng cách giữa 2 nút ~4% chiều rộng

        # giới hạn min/max để không quá to/nhỏ
        self.min_btn_w, self.min_btn_h = 80, 36
        self.max_btn_w, self.max_btn_h = 280, 80

        self.update_button_positions()

        # events
        self.btn1.clicked.connect(self.event_buton_1())
        self.btn2.clicked.connect(lambda: print("Bạn bấm Nút 2"))
    # Giao diện nút (tự động thay đổi khi resize)
    def resizeEvent(self, event):
        self.update_button_positions()
        super().resizeEvent(event)

    def update_button_positions(self):
        w = self.width()
        h = self.height()

        # TÍNH KÍCH THƯỚC NÚT THEO TỈ LỆ + GIỚI HẠN
        bw = int(w * self.btn_w_ratio)
        bh = int(h * self.btn_h_ratio)
        bw = max(self.min_btn_w, min(bw, self.max_btn_w))
        bh = max(self.min_btn_h, min(bh, self.max_btn_h))

        # font cũng scale theo chiều cao nút (tùy chọn)
        fs = max(9, int(bh * 0.4))  # 40% chiều cao nút
        f = QFont()
        f.setPointSize(fs)
        self.btn1.setFont(f)
        self.btn2.setFont(f)

        # khoảng cách giữa 2 nút theo tỉ lệ
        spacing = max(12, int(w * self.spacing_ratio))

        # TỔNG RỘNG CỤM 2 NÚT + KHOẢNG CÁCH
        total_w = bw * 2 + spacing

        # TOẠ ĐỘ CĂN GIỮA
        x0 = max(0, (w - total_w) // 2)
        y0 = max(0, (h - bh) // 2)

        # ÁP DỤNG KÍCH THƯỚC & VỊ TRÍ
        self.btn1.setGeometry(x0, y0, bw, bh)
        self.btn2.setGeometry(x0 + bw + spacing, y0, bw, bh)
    def event_buton_1 (self):
        self.ws = Image_Processing()
        self.ws.show()
        
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()

if __name__ == "__main__":
    main()
