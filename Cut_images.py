import csv
from pathlib import Path
import cv2

def crop_from_csv(image_path: Path, csv_path: Path, out_dir: Path) -> None:
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    assert img is not None, f"Không đọc được ảnh: {image_path}"
    h, w = img.shape[:2] 
    # Đọc CSV & cắt
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["index"])

            # Lấy bbox từ 4 đỉnh (giả định box thẳng trục, dữ liệu hợp lệ)
            xs = [int(float(row[k])) for k in ("tl_x", "tr_x", "br_x", "bl_x")]
            ys = [int(float(row[k])) for k in ("tl_y", "tr_y", "br_y", "bl_y")]
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)

            # Cắt (y trước x)
            crop = img[y1:y2, x1:x2]

            # Lưu file
            out_path = out_dir / f"cropped_{idx:03d}.png"
            cv2.imwrite(str(out_path), crop)

    print(f"Đã cắt xong. Ảnh lưu tại: {out_dir}")

def main():
    IMAGE_PATH = Path(r"C:\Users\HOANG MINH\Desktop\Final\exports\nice_20250827_180219\nice.png")
    CSV_PATH   = Path(r"C:\Users\HOANG MINH\Desktop\Final\exports\nice_20250827_180219\boxes.csv")
    OUT_DIR    = Path(r"C:\Users\HOANG MINH\Desktop\Final\exports\nice_20250827_180219")
    crop_from_csv(IMAGE_PATH, CSV_PATH, OUT_DIR)

if __name__ == "__main__":
    main()
