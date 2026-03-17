"""
Build a unified YOLO dataset from manifest CSV files.

Example:
  python scripts/build_yolo_dataset.py ^
    --train-manifest D:/tmp/ds_all/manifest_train.csv ^
    --val-manifest D:/tmp/ds_all/manifest_val.csv ^
    --out-dir D:/tmp/yolo_all ^
    --coco-train-images D:/datasets/coco/train2017 ^
    --coco-val-images D:/datasets/coco/val2017 ^
    --rpc-train-images D:/datasets/rpc/train2019 ^
    --rpc-val-images D:/datasets/rpc/val2019 ^
    --sku-images D:/datasets/sku110k/images ^
    --grozi-images D:/datasets/grozi/images ^
    --mode link
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _load_manifest(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _link_or_copy(src: Path, dst: Path, mode: str) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "link":
        try:
            os.link(src, dst)
            return
        except Exception:
            pass
    dst.write_bytes(src.read_bytes())


def _image_root_for(row: dict, paths: dict) -> Path | None:
    dataset = row["dataset"]
    split = row["split"]
    if dataset == "coco":
        return Path(paths["coco_train_images"] if split == "train" else paths["coco_val_images"])
    if dataset == "rpc":
        return Path(paths["rpc_train_images"] if split == "train" else paths["rpc_val_images"])
    if dataset == "sku110k":
        return Path(paths["sku_images"])
    if dataset == "grozi":
        return Path(paths["grozi_images"])
    return None


def _group_rows(rows: Iterable[dict]) -> Dict[Tuple[str, str, str, str], List[dict]]:
    grouped: Dict[Tuple[str, str, str, str], List[dict]] = {}
    for row in rows:
        key = (row["dataset"], row["split"], row["image_id"], row["file_name"])
        grouped.setdefault(key, []).append(row)
    return grouped


def _write_labels(
    label_path: Path,
    rows: List[dict],
    class_to_idx: Dict[str, int],
) -> None:
    lines: List[str] = []
    for row in rows:
        label = row.get("mapped_class", "")
        if label not in class_to_idx:
            continue
        bbox = json.loads(row.get("bbox") or "[]")
        if len(bbox) != 4:
            continue
        width = _safe_float(row.get("width", "0"))
        height = _safe_float(row.get("height", "0"))
        if width <= 0 or height <= 0:
            continue
        x1, y1, x2, y2 = bbox
        xc = (x1 + x2) / 2.0 / width
        yc = (y1 + y2) / 2.0 / height
        w = (x2 - x1) / width
        h = (y2 - y1) / height
        lines.append(f"{class_to_idx[label]} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
    if not lines:
        return
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("\n".join(lines), encoding="utf-8")


def build_dataset(
    train_manifest: Path,
    val_manifest: Path,
    out_dir: Path,
    paths: dict,
    classes: List[str],
    mode: str,
    max_images_per_dataset: int | None,
    seed: int,
) -> None:
    out_images_train = out_dir / "images" / "train"
    out_images_val = out_dir / "images" / "val"
    out_labels_train = out_dir / "labels" / "train"
    out_labels_val = out_dir / "labels" / "val"

    _ensure_dir(out_images_train)
    _ensure_dir(out_images_val)
    _ensure_dir(out_labels_train)
    _ensure_dir(out_labels_val)

    class_to_idx = {name: idx for idx, name in enumerate(classes)}
    random.seed(seed)

    for manifest_path in [train_manifest, val_manifest]:
        rows = _load_manifest(manifest_path)
        grouped = _group_rows(rows)
        per_dataset_count: Dict[str, int] = {}

        for (dataset, split, image_id, file_name), items in grouped.items():
            if max_images_per_dataset is not None:
                count = per_dataset_count.get(dataset, 0)
                if count >= max_images_per_dataset:
                    continue
                per_dataset_count[dataset] = count + 1

            root = _image_root_for(items[0], paths)
            if root is None:
                continue
            src_img = root / file_name
            if not src_img.exists():
                continue

            out_img_dir = out_images_train if split == "train" else out_images_val
            out_lbl_dir = out_labels_train if split == "train" else out_labels_val
            # avoid collisions by scoping by dataset
            rel_img_dir = Path(dataset)
            out_img = out_img_dir / rel_img_dir / file_name
            out_lbl = out_lbl_dir / rel_img_dir / f"{Path(file_name).stem}.txt"

            _link_or_copy(src_img, out_img, mode)
            _write_labels(out_lbl, items, class_to_idx)

    # dataset.yaml for Ultralytics
    yaml_path = out_dir / "dataset.yaml"
    yaml_content = "\n".join(
        [
            f"path: {out_dir.as_posix()}",
            "train: images/train",
            "val: images/val",
            f"nc: {len(classes)}",
            f"names: {classes}",
        ]
    )
    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"[done] YOLO dataset built at {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build YOLO dataset from manifests.")
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--val-manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--coco-train-images", type=Path, required=True)
    parser.add_argument("--coco-val-images", type=Path, required=True)
    parser.add_argument("--rpc-train-images", type=Path, required=True)
    parser.add_argument("--rpc-val-images", type=Path, required=True)
    parser.add_argument("--sku-images", type=Path, required=True)
    parser.add_argument("--grozi-images", type=Path, required=True)
    parser.add_argument("--classes", type=str, default="item,box,shelf,closet,bag,hand,document,table")
    parser.add_argument("--mode", choices=["link", "copy"], default="link")
    parser.add_argument("--max-images-per-dataset", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    paths = {
        "coco_train_images": args.coco_train_images,
        "coco_val_images": args.coco_val_images,
        "rpc_train_images": args.rpc_train_images,
        "rpc_val_images": args.rpc_val_images,
        "sku_images": args.sku_images,
        "grozi_images": args.grozi_images,
    }

    classes = [c.strip() for c in args.classes.split(",") if c.strip()]

    build_dataset(
        train_manifest=args.train_manifest,
        val_manifest=args.val_manifest,
        out_dir=args.out_dir,
        paths=paths,
        classes=classes,
        mode=args.mode,
        max_images_per_dataset=args.max_images_per_dataset,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
