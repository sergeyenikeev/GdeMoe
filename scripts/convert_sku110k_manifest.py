"""
Convert SKU110K CSV annotations to manifest CSV.

Example:
  python scripts/convert_sku110k_manifest.py ^
    --annotations D:/datasets/sku110k/annotations/annotations_train.csv ^
    --images-dir D:/datasets/sku110k/images ^
    --split train ^
    --out D:/tmp/ds_sku/manifest_sku_train.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List


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


def convert_sku110k(
    annotations_path: Path,
    images_dir: Path,
    out_path: Path,
    split: str,
    map_all_to: str,
    source: str,
    limit: int | None,
    check_files: bool,
) -> None:
    if not annotations_path.exists():
        raise SystemExit(f"[error] annotations not found: {annotations_path}")
    if not images_dir.exists():
        raise SystemExit(f"[error] images dir not found: {images_dir}")

    rows: List[dict] = []
    count = 0
    with annotations_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if limit and count >= limit:
                break
            if not row or row[0] == "image_name":
                continue
            image_name, x1, y1, x2, y2, cls, width, height = row
            if check_files and not (images_dir / image_name).exists():
                continue
            bbox = [float(x1), float(y1), float(x2), float(y2)]
            rows.append(
                {
                    "dataset": "sku110k",
                    "split": split,
                    "image_id": image_name,
                    "file_name": image_name,
                    "mapped_class": map_all_to,
                    "original_class": cls,
                    "license_name": "CC BY-NC-SA 3.0 IGO",
                    "license_url": "",
                    "width": int(width),
                    "height": int(height),
                    "bbox": json.dumps(bbox),
                    "source": source,
                }
            )
            count += 1

    write_manifest(out_path, rows)
    print(f"[done] sku110k rows={len(rows)} written to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert SKU110K CSV annotations to manifest CSV.")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--map-all-to", default="item")
    parser.add_argument("--source", default="sku110k")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--check-files", action="store_true")
    args = parser.parse_args()

    convert_sku110k(
        annotations_path=args.annotations,
        images_dir=args.images_dir,
        out_path=args.out,
        split=args.split,
        map_all_to=args.map_all_to,
        source=args.source,
        limit=args.limit,
        check_files=bool(args.check_files),
    )


if __name__ == "__main__":
    main()
