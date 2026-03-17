"""
Convert RPC (Retail Product Checkout) COCO-style annotations to manifest CSV.

Example:
  python scripts/convert_rpc_manifest.py ^
    --annotations D:/datasets/rpc/instances_train2019.json ^
    --images-dir D:/datasets/rpc/train2019 ^
    --split train ^
    --out D:/tmp/ds_rpc/manifest_rpc_train.csv
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


def convert_rpc(
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

    data = json.loads(annotations_path.read_text(encoding="utf-8"))
    images_by_id = {img["id"]: img for img in data.get("images", [])}
    cat_id_to_name = {cat["id"]: cat["name"] for cat in data.get("categories", [])}
    license_map = {lic["id"]: (lic.get("name") or "", lic.get("url") or "") for lic in data.get("licenses", [])}

    rows: List[dict] = []
    count = 0
    for ann in data.get("annotations", []):
        if limit and count >= limit:
            break
        image = images_by_id.get(ann.get("image_id"))
        if not image:
            continue
        file_name = image.get("file_name")
        if not file_name:
            continue
        if check_files and not (images_dir / file_name).exists():
            continue
        bbox = ann.get("bbox") or []
        if len(bbox) == 4:
            x1, y1, w, h = bbox
            bbox = [x1, y1, x1 + w, y1 + h]
        lic_name, lic_url = license_map.get(image.get("license"), ("", ""))
        cat_name = cat_id_to_name.get(ann.get("category_id"), "")
        rows.append(
            {
                "dataset": "rpc",
                "split": split,
                "image_id": image.get("id"),
                "file_name": file_name,
                "mapped_class": map_all_to,
                "original_class": cat_name,
                "license_name": lic_name,
                "license_url": lic_url,
                "width": image.get("width"),
                "height": image.get("height"),
                "bbox": json.dumps(bbox),
                "source": source,
            }
        )
        count += 1

    write_manifest(out_path, rows)
    print(f"[done] rpc rows={len(rows)} written to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert RPC COCO annotations to manifest CSV.")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--map-all-to", default="item")
    parser.add_argument("--source", default="rpc2019")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--check-files", action="store_true")
    args = parser.parse_args()

    convert_rpc(
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
