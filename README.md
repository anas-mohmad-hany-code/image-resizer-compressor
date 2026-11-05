# Image Resizer & Compressor

A Python automation tool that batch resizes images in a folder to a fixed resolution and optimizes JPEG quality to ensure file sizes stay strictly under a specified limit (e.g., 1 MB).

## Features

- **Batch Processing:** Automatically scans and converts images in formats like `PNG`, `WEBP`, `BMP`, `TIFF`, and `GIF` into `JPG`.
- **Smart Quality Compression:** Employs a binary search algorithm over JPEG quantization tables to achieve the highest possible image quality while strictly honoring the file size cap.
- **Fitting Modes:**
  - `pad`: Maintains aspect ratio and fills empty spaces with a clean white background.
  - `crop`: Center-crops the image to fill exact dimensions.
  - `stretch`: Fits the target size directly (may alter aspect ratio).
- **Safe Execution:** Writes processed images to a temporary file (`.tmp`) first to ensure your originals are not corrupted if the process is interrupted.

## Requirements

- Python 3.8+
- [Pillow](https://python-pillow.org/)

## Installation & Setup

1. Install the required dependency:
   ```bash
   pip install -r requirements.txt