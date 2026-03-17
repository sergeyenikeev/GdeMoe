"""
Convert a YOLO-format dataset (images + labels) to manifest CSV.

Example (GroZi):
  python scripts/convert_yolo_manifest.py ^
    --images-dir D:/datasets/grozi/images ^
    --labels-dir D:/datasets/grozi/labels ^
    --split train ^
    --out D:/tmp/ds_grozi/manifest_grozi_train.csv ^
    --dataset grozi ^
    --source grozi-yolo
"""

from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path
from typing import List, Optional, Tuple


FIELDNAMES = [
    "dataset",
    "split",
    "image_id",
    "file_name",
    "mapped_class",
    "original_class",
    "license_name",
    "license_url",
    "width",
    "height",
    "bbox",
    "source",
]


def write_manifest(out_path: Path, rows: List[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _get_png_size(f) -> Optional[Tuple[int, int]]:
    f.seek(0)
    sig = f.read(8)
    if sig != b"\x89PNG\r\n\x1a\n":
        return None
    f.seek(16)
    width, height = struct.unpack(">II", f.read(8))
    return int(width), int(height)


def _get_jpeg_size(f) -> Optional[Tuple[int, int]]:
    f.seek(0)
    if f.read(2) != b"\xff\xd8":
        return None
    while True:
        marker = f.read(2)
        if len(marker) != 2:
            return None
        while marker[0] != 0xFF:
            marker = marker[1:] + f.read(1)
        marker_type = marker[1]
        if marker_type in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            _ = f.read(2)
            _ = f.read(1)
            height, width = struct.unpack(">HH", f.read(4))
            return int(width), int(height)
        length_bytes = f.read(2)
        if len(length_bytes) != 2:
            return None
        seg_len = struct.unpack(">H", length_bytes)[0]
        f.seek(seg_len - 2, 1)


def get_image_size(path: Path) -> Tuple[int, int]:
    with path.open("rb") as f:
        size = _get_png_size(f)
        if size:
            return size
        size = _get_jpeg_size(f)
        if size:
            return size
    raise ValueError(f"Unsupported image format: {path}")


def find_image_file(images_dir: Path, stem: str) -> Optional[Path]:
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = images_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def convert_yolo(
    images_dir: Path,
    labels_dir: Path,
    out_path: Path,
    split: str,
    dataset: str,
    source: str,
    map_all_to: str,
    limit_images: int | None,
) -> None:
    if not images_dir.exists():
        raise SystemExit(f"[error] images dir not found: {images_dir}")
    if not labels_dir.exists():
        raise SystemExit(f"[error] labels dir not found: {labels_dir}")

    rows: List[dict] = []
    processed = 0
    for label_file in labels_dir.glob("*.txt"):
        if limit_images and processed >= limit_images:
            break
        stem = label_file.stem
        image_path = find_image_file(images_dir, stem)
        if not image_path:
            continue
        try:
            width, height = get_image_size(image_path)
        except Exception:
            continue
        with label_file.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            continue
        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            cls_id = parts[0]
            xc, yc, w, h = map(float, parts[1:5])
            x1 = (xc - w / 2.0) * width
            y1 = (yc - h / 2.0) * height
            x2 = (xc + w / 2.0) * width
            y2 = (yc + h / 2.0) * height
            bbox = [x1, y1, x2, y2]
            rows.append(
                {
                    "dataset": dataset,
                    "split": split,
                    "image_id": stem,
                    "file_name": image_path.name,
                    "mapped_class": map_all_to,
                    "original_class": str(cls_id),
                    "license_name": "",
                    "license_url": "",
                    "width": width,
                    "height": height,
                    "bbox": json.dumps(bbox),
                    "source": source,
                }
            )
        processed += 1

    write_manifest(out_path, rows)
    print(f"[done] yolo rows={len(rows)} written to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert YOLO dataset to manifest CSV.")
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dataset", default="yolo")
    parser.add_argument("--source", default="yolo")
    parser.add_argument("--map-all-to", default="item")
    parser.add_argument("--limit-images", type=int, default=None)
    args = parser.parse_args()

    convert_yolo(
        images_dir=args.images_dir,
        labels_dir=args.labels_dir,
        out_path=args.out,
        split=args.split,
        dataset=args.dataset,
        source=args.source,
        map_all_to=args.map_all_to,
        limit_images=args.limit_images,
    )


if __name__ == "__main__":
    main()
