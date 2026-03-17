"""Конвертация RPC в manifest CSV.

RPC поставляется в COCO-подобном JSON-формате. Скрипт переводит его в общий
внутренний manifest, который дальше используется фильтрами, merge-скриптами
и сборкой единого YOLO-датасета.

Пример:
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
    """Записывает итоговый manifest в CSV-файл.

    Создаёт родительские директории при необходимости, записывает заголовок
    и все строки в формате CSV с кодировкой UTF-8.

    Args:
        out_path (Path): Путь к выходному CSV-файлу.
        rows (List[dict]): Список словарей с данными для записи.

    Returns:
        None

    Raises:
        OSError: При проблемах с созданием директорий или записью файла.
    """
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
    """Преобразует JSON-аннотации RPC в строки manifest CSV.

    Загружает COCO-подобный JSON, извлекает аннотации, преобразует bbox
    из формата COCO (x,y,w,h) в внутренний (x1,y1,x2,y2), маппит классы
    и записывает результат в CSV.

    Args:
        annotations_path (Path): Путь к JSON-файлу с аннотациями.
        images_dir (Path): Директория с изображениями.
        out_path (Path): Путь к выходному CSV-файлу.
        split (str): Тип сплита ('train', 'val' и т.д.).
        map_all_to (str): Класс, к которому маппятся все объекты (по умолчанию 'item').
        source (str): Источник данных (по умолчанию 'rpc2019').
        limit (int | None): Максимальное количество аннотаций (опционально).
        check_files (bool): Проверять существование файлов изображений.

    Returns:
        None

    Raises:
        SystemExit: Если файлы аннотаций или директория изображений не найдены.
        JSONDecodeError: При ошибках парсинга JSON.
    """
    if not annotations_path.exists():
        raise SystemExit(f"[error] annotations not found: {annotations_path}")
    if not images_dir.exists():
        raise SystemExit(f"[error] images dir not found: {images_dir}")

    data = json.loads(annotations_path.read_text(encoding="utf-8"))
    # COCO-подобная структура позволяет быстро собрать словари по изображениям,
    # категориям и лицензиям, чтобы дальше не искать их линейно для каждой bbox.
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
            # В COCO bbox хранится как x, y, width, height.
            # Внутренний manifest использует x1, y1, x2, y2.
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
    """Главная функция скрипта для конвертации RPC manifest.

    Парсит аргументы командной строки и вызывает convert_rpc.

    Аргументы командной строки:
    - --annotations: Путь к JSON-файлу с аннотациями (обязательно).
    - --images-dir: Директория с изображениями (обязательно).
    - --split: Тип сплита (по умолчанию 'train').
    - --out: Путь к выходному CSV-файлу (обязательно).
    - --map-all-to: Класс для маппинга (по умолчанию 'item').
    - --source: Источник данных (по умолчанию 'rpc2019').
    - --limit: Максимальное количество аннотаций (опционально).
    - --check-files: Проверять существование файлов изображений.

    Returns:
        None

    Raises:
        SystemExit: При ошибках парсинга или выполнения.
    """
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
