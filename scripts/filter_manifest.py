"""
Filter a manifest CSV by dataset/class and optionally cap rows per class.

Example:
  python scripts/filter_manifest.py ^
    --input C:/tmp/ds_all/manifest_train.csv ^
    --out C:/tmp/ds_all/manifest_ft_train.csv ^
    --exclude-dataset rpc,sku110k ^
    --max-per-class 5000 ^
    --seed 42
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import Dict, List, Optional


def _parse_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def filter_manifest(
    input_path: Path,
    out_path: Path,
    include_dataset: List[str],
    exclude_dataset: List[str],
    include_class: List[str],
    exclude_class: List[str],
    max_per_class: Optional[int],
    seed: int,
    shuffle: bool,
    max_rows: Optional[int],
) -> None:
    if not input_path.exists():
        raise SystemExit(f"[error] manifest not found: {input_path}")

    rows: List[dict] = []
    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            dataset = row.get("dataset", "")
            cls = row.get("mapped_class", "")
            if include_dataset and dataset not in include_dataset:
                continue
            if exclude_dataset and dataset in exclude_dataset:
                continue
            if include_class and cls not in include_class:
                continue
            if exclude_class and cls in exclude_class:
                continue
            rows.append(row)

    rnd = random.Random(seed)
    if shuffle:
        rnd.shuffle(rows)

    if max_per_class is not None:
        buckets: Dict[str, List[dict]] = {}
        for row in rows:
            buckets.setdefault(row.get("mapped_class", ""), []).append(row)
        rows = []
        for cls, items in buckets.items():
            if shuffle:
                rnd.shuffle(items)
            rows.extend(items[:max_per_class])

    if max_rows is not None:
        if shuffle:
            rnd.shuffle(rows)
        rows = rows[:max_rows]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[done] filtered rows={len(rows)} written to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter manifest CSV.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--include-dataset", type=str, default="")
    parser.add_argument("--exclude-dataset", type=str, default="")
    parser.add_argument("--include-class", type=str, default="")
    parser.add_argument("--exclude-class", type=str, default="")
    parser.add_argument("--max-per-class", type=int, default=None)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shuffle", action="store_true")
    args = parser.parse_args()

    filter_manifest(
        input_path=args.input,
        out_path=args.out,
        include_dataset=_parse_list(args.include_dataset),
        exclude_dataset=_parse_list(args.exclude_dataset),
        include_class=_parse_list(args.include_class),
        exclude_class=_parse_list(args.exclude_class),
        max_per_class=args.max_per_class,
        seed=args.seed,
        shuffle=bool(args.shuffle),
        max_rows=args.max_rows,
    )


if __name__ == "__main__":
    main()
