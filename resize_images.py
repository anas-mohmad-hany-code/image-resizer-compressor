"""
Image Resizer & Compressor

Resizes every image in a folder to a fixed size and saves it as a JPG with the
highest quality that still keeps the file size at or below a chosen limit.

WARNING: the original files are OVERWRITTEN in place. Images in other formats
(PNG, WEBP, ...) are converted to JPG and the original file is deleted.
Back up your folder before the first run.

Install:  pip install pillow
Run:      python resize_images.py

Settings (edit the constants below):
    FOLDER_PATH       Folder that contains the images (raw string on Windows).
    TARGET_SIZE       Output size in pixels as (width, height).
    MAX_BYTES         Maximum allowed file size in bytes (limit is inclusive).
    IMAGE_EXTENSIONS  File extensions that will be processed.
    MODE              How to fit images to TARGET_SIZE: "pad", "crop" or "stretch".
"""

import io
import os
import sys
from pathlib import Path

from PIL import Image, ImageOps

# ----------------------------- Settings -----------------------------
# Folder to process (images are overwritten in place).
FOLDER_PATH = r"D:\Downloads\Covers"

# Output size in pixels: (width, height).
TARGET_SIZE = (1500, 1500)

# Max file size in bytes. 1024 * 1024 = 1 MiB (1,048,576 bytes).
# Use 1_000_000 if you need 1 MB in decimal units.
MAX_BYTES = 1024 * 1024

# Extensions that will be processed (lowercase, with a leading dot).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif", ".gif"}

# How images are fitted to TARGET_SIZE:
#   "pad"     keep aspect ratio, fill the rest with white (no crop, no distortion)
#   "crop"    keep aspect ratio, center-crop to fill the whole area
#   "stretch" ignore aspect ratio (may distort the image)
MODE = "pad"
# --------------------------------------------------------------------


def to_rgb(img: Image.Image) -> Image.Image:
    """Convert to RGB. Transparency is flattened onto a white background."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        return background
    return img.convert("RGB")


def resize_image(img: Image.Image) -> Image.Image:
    if MODE == "crop":
        return ImageOps.fit(img, TARGET_SIZE, Image.LANCZOS, centering=(0.5, 0.5))
    if MODE == "stretch":
        return img.resize(TARGET_SIZE, Image.LANCZOS)
    # pad
    img = ImageOps.contain(img, TARGET_SIZE, Image.LANCZOS)
    canvas = Image.new("RGB", TARGET_SIZE, (255, 255, 255))
    x = (TARGET_SIZE[0] - img.width) // 2
    y = (TARGET_SIZE[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


_BASE_TABLES = None


def _base_tables(img: Image.Image):
    """Standard JPEG quantization tables (the unscaled tables at quality=50)."""
    global _BASE_TABLES
    if _BASE_TABLES is None:
        buf = io.BytesIO()
        img.resize((16, 16)).save(buf, format="JPEG", quality=50)
        buf.seek(0)
        with Image.open(buf) as j:
            q = j.quantization
        _BASE_TABLES = [list(q[0]), list(q[1])]
    return _BASE_TABLES


def _scaled_tables(img: Image.Image, quality: float):
    """libjpeg's quality-to-table formula, extended to accept fractional quality."""
    if quality < 50:
        scale = 5000.0 / quality
    else:
        scale = 200.0 - 2.0 * quality
    tables = []
    for base in _base_tables(img):
        tables.append([min(255, max(1, int((v * scale + 50.0) / 100.0))) for v in base])
    return tables


def encode(img: Image.Image, quality: float) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", qtables=_scaled_tables(img, quality),
             optimize=True, progressive=True)
    return buf.getvalue()


def compress_best_quality(img: Image.Image) -> tuple[bytes, float]:
    """
    Find the highest JPEG quality (1-100, in 0.05 steps) whose file size is
    <= MAX_BYTES, so the result lands as close to the limit as possible.

    1) Binary search to get near the limit quickly.
    2) Scan a few quality points above the result, because file size does not
       always grow monotonically with quality.
    """
    STEP = 0.05
    MAX_STEPS = int(round(99 / STEP))  # index 0 -> quality 1.00, last -> 100.00
    cache: dict[int, bytes] = {}

    def q_of(i: int) -> float:
        return 1.0 + i * STEP

    def size_at(i: int) -> int:
        if i not in cache:
            cache[i] = encode(img, q_of(i))
        return len(cache[i])

    # 1) Binary search
    low, high = 0, MAX_STEPS
    best = -1
    while low <= high:
        mid = (low + high) // 2
        if size_at(mid) <= MAX_BYTES:
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    # 2) Scan 3 quality points above the binary search result
    scan_to = min(MAX_STEPS, best + int(3 / STEP)) if best >= 0 else -1
    for i in range(best + 1, scan_to + 1):
        if size_at(i) <= MAX_BYTES:
            best = i

    if best < 0:  # Even the lowest quality exceeds the limit (very rare)
        best = 0
        size_at(0)
    return cache[best], round(q_of(best), 2)


def clear_screen():
    """Clear old terminal output (works on Windows, macOS and Linux)."""
    os.system("cls" if os.name == "nt" else "clear")


def main():
    clear_screen()

    folder = Path(FOLDER_PATH)
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        sys.exit(1)

    files = [
        p for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not files:
        print("No images found in this folder.")
        return

    print(f"Found {len(files)} images. Processing...\n")
    ok, failed = 0, 0

    for i, path in enumerate(files, 1):
        try:
            with Image.open(path) as img:
                img = ImageOps.exif_transpose(img)  # Apply EXIF rotation
                img = to_rgb(img)
                img = resize_image(img)
                data, quality = compress_best_quality(img)

            out_path = path.with_suffix(".jpg")
            # Avoid overwriting a different file that already has the target name
            if out_path != path and out_path.exists() and out_path not in files:
                out_path = out_path.with_name(out_path.stem + "_1.jpg")
            elif out_path != path and out_path.exists():
                out_path = out_path.with_name(out_path.stem + "_converted.jpg")

            # Write to a temp file first so the original survives a failed write
            tmp_path = out_path.with_name(out_path.stem + ".tmp_resize")
            tmp_path.write_bytes(data)
            os.replace(tmp_path, out_path)
            if out_path != path:
                path.unlink()  # Delete the original (PNG/WEBP/...) after saving the JPG
            print(f"[{i}/{len(files)}] {path.name} -> {out_path.name} "
                  f"| quality={quality:.2f} | {len(data) / 1024:.0f} KB")
            ok += 1
        except Exception as e:
            print(f"[{i}/{len(files)}] FAILED {path.name}: {e}")
            failed += 1

    print(f"\nDone. Success: {ok} | Failed: {failed}")
    print(f"Images updated in: {folder}")


if __name__ == "__main__":
    main()