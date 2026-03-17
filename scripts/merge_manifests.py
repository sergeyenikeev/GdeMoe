"""Объединение нескольких manifest CSV в один.

Скрипт специально очень простой: он не пытается дедуплицировать строки,
а только проверяет, что у всех файлов одинаковый заголовок.

Пример:
  python scripts/merge_manifests.py \
    --inputs D:/tmp/ds_subset/manifest_coco_train.csv D:/tmp/ds_subset_val/manifest_coco_val.csv \
    --out D:/tmp/ds_subset_all/manifest_all.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List


def merge_manifests(inputs: List[Path], out_path: Path) -> None:
    """Склеивает несколько manifest CSV с одинаковой схемой.

    Читает все входные CSV-файлы, проверяет совпадение заголовков
    и объединяет строки в один выходной файл. Не выполняет дедупликацию.

    Args:
        inputs: Список путей к входным manifest CSV.
        out_path: Путь к выходному объединённому CSV.

    Raises:
        SystemExit: Если файлы не найдены или заголовки не совпадают.
    """
    if not inputs:
        raise SystemExit("No input manifests provided")
    rows = []
    header = None
    for path in inputs:
        if not path.exists():
            raise SystemExit(f"Manifest not found: {path}")
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if header is None:
                header = reader.fieldnames
            elif reader.fieldnames != header:
                # Если колонки не совпали, безопаснее упасть сразу,
                # чем тихо получить битый общий manifest.
                raise SystemExit(f"Header mismatch in {path}")
            rows.extend(reader)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[done] merged {len(rows)} rows from {len(inputs)} manifests into {out_path}")
    if not inputs:
        raise SystemExit("No input manifests provided")
    rows = []
    header = None
    for path in inputs:
        if not path.exists():
            raise SystemExit(f"Manifest not found: {path}")
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if header is None:
                header = reader.fieldnames
            elif reader.fieldnames != header:
                # Если колонки не совпали, безопаснее упасть сразу,
                # чем тихо получить битый общий manifest.
                raise SystemExit(f"Header mismatch in {path}")
            rows.extend(reader)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[done] merged {len(rows)} rows from {len(inputs)} manifests into {out_path}")


def main() -> None:
    """Главная функция скрипта для объединения manifest-файлов.

    Парсит аргументы командной строки и вызывает merge_manifests
    для объединения указанных CSV-файлов.
    """
    parser = argparse.ArgumentParser(description="Merge manifest CSV files.")
    parser.add_argument("--inputs", nargs="+", type=Path, required=True, help="List of input manifest CSV files")
    parser.add_argument("--out", type=Path, required=True, help="Output merged CSV file")
    args = parser.parse_args()
    merge_manifests(args.inputs, args.out)


if __name__ == "__main__":
    main()
