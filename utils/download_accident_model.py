"""
Utility to download Enos-123/traffic-accident-detection-yolo11x weights from HuggingFace.
"""

import os
import sys
import time
import urllib.request

HF_URL = "https://huggingface.co/Enos-123/traffic-accident-detection-yolo11x/resolve/main/weights/epoch61.pt"
DEST_PATH = os.path.join("models", "accident_yolo11x.pt")
EXPECTED_SIZE = 114368274  # bytes (~114.36 MB)


def download_model(url: str = HF_URL, dest: str = DEST_PATH) -> bool:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    temp_dest = dest + ".tmp"

    if os.path.exists(dest):
        actual_size = os.path.getsize(dest)
        if actual_size >= EXPECTED_SIZE:
            print(f"[OK] Model already exists at {dest} ({actual_size / (1024*1024):.1f} MB)")
            return True
        else:
            print(f"[INFO] Existing file is incomplete ({actual_size} bytes). Re-downloading...")
            try:
                os.remove(dest)
            except OSError:
                pass

    print(f"[DOWNLOADING] Fetching fine-tuned YOLO11x weights from Hugging Face...")
    print(f"Source: {url}")
    print(f"Destination: {dest}")

    start_time = time.time()
    last_print = start_time

    def reporthook(count, block_size, total_size):
        nonlocal last_print
        now = time.time()
        if now - last_print >= 1.0 or count * block_size >= total_size:
            downloaded = count * block_size
            pct = (downloaded / total_size * 100) if total_size > 0 else 0
            speed_mb = (downloaded / (1024 * 1024)) / (now - start_time) if (now - start_time) > 0 else 0
            print(f"Progress: {downloaded / (1024*1024):.1f} / {total_size / (1024*1024):.1f} MB ({pct:.1f}%) - {speed_mb:.2f} MB/s", flush=True)
            last_print = now

    headers = {"User-Agent": "SmartRoadVision/1.0"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response, open(temp_dest, "wb") as out_file:
            total_size = int(response.headers.get("Content-Length", EXPECTED_SIZE))
            downloaded = 0
            block_size = 64 * 1024
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                out_file.write(buffer)
                downloaded += len(buffer)
                reporthook(downloaded // block_size, block_size, total_size)

        if os.path.exists(dest):
            os.remove(dest)
        os.rename(temp_dest, dest)
        elapsed = time.time() - start_time
        final_size = os.path.getsize(dest)
        print(f"[SUCCESS] Download completed in {elapsed:.1f}s: {dest} ({final_size / (1024*1024):.1f} MB)")
        return True
    except Exception as e:
        if os.path.exists(temp_dest):
            try:
                os.remove(temp_dest)
            except OSError:
                pass
        print(f"[ERROR] Failed to download weights: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
