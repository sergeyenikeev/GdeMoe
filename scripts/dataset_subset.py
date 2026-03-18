"""Сборка небольшого, лицензированно-прозрачного подмножества датасета.

Скрипт нужен на раннем этапе, когда не хочется сразу тащить весь COCO или
Open Images в эксперимент. Он:

- ограничивает число примеров на класс;
- отображает исходные классы в проектные классы;
- сохраняет информацию о лицензии и источнике;
- при необходимости копирует сами изображения.

Пример (COCO):
  python scripts/dataset_subset.py \
    --dataset coco \
    --split train \
    --coco-annotations /data/coco/annotations/instances_train2017.json \
    --images-dir /data/coco/train2017 \
    --out-dir /tmp/ds_subset \
    --limit-per-class 500

Пример (Open Images):
  python scripts/dataset_subset.py \
    --dataset openimages \
    --split train \
    --openimages-annotations /data/open_images/train-annotations-bbox.csv \
    --openimages-class-descriptions /data/open_images/class-descriptions-boxable.csv \
    --openimages-images-file /data/open_images/train-images-boxable-with-rotation.csv \
    --out-dir /tmp/ds_subset \
    --limit-per-class 500
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Проектные целевые классы, к которым мы сводим разные внешние датасеты.
TARGET_CLASSES = [
    "item",
    "box",
    "shelf",
    "closet",
    "bag",
    "hand",
    "document",
    "table",
    "background",
]

# Соответствие "класс проекта -> набор похожих COCO-категорий".
COCO_CLASS_MAP: Dict[str, List[str]] = {
    "box": ["suitcase", "skateboard"],
    "bag": ["handbag", "backpack", "tie", "suitcase"],
    "hand": ["person"],  # use person to pick hand crops later if needed
    "document": ["book", "laptop", "tv", "cell phone", "remote"],
    "shelf": ["bed", "couch", "bench"],
    "closet": ["refrigerator", "oven", "microwave", "toaster"],  # closest indoor storage analogues
    "table": ["dining table"],
    "item": [
        "bottle",
        "cup",
        "bowl",
        "chair",
        "potted plant",
        "remote",
        "keyboard",
        "mouse",
        "sink",
    ],
}

# Аналогичное соответствие для Open Images по человекочитаемым именам.
OPENIMAGES_CLASS_MAP: Dict[str, List[str]] = {
    "box": ["Cardboard box", "Packaging that contains food"],
    "bag": ["Backpack", "Handbag", "Suitcase", "Briefcase"],
    "hand": ["Human hand"],
    "document": ["Document", "Binder", "Whiteboard"],
    "shelf": ["Shelf", "Bookcase"],
    "closet": ["Wardrobe", "Cabinetry", "Drawer"],
    "table": ["Table", "Coffee table", "Countertop"],
    "item": [
        "Bottle",
        "Laptop",
        "Mobile phone",
        "Cup",
        "Keyboard",
        "Computer monitor",
        "Food",
    ],
}


def _ensure_out_dir(path: Path) -> None:
    """Создаёт выходную директорию с родительскими папками при необходимости.

    Args:
        path (Path): Путь к директории для создания.

    Returns:
        None

    Raises:
        OSError: При проблемах с созданием директории.
    """
    path.mkdir(parents=True, exist_ok=True)


def _require_paths_exist(paths: Iterable[Path], context: str) -> None:
    """Проверяет, что все обязательные пути действительно существуют.

    Args:
        paths (Iterable[Path]): Итерируемый объект с путями для проверки.
        context (str): Контекст ошибки для сообщения.

    Returns:
        None

    Raises:
        SystemExit: Если хотя бы один путь не существует.
    """
    missing = [str(p) for p in paths if p and not p.exists()]
    if missing:
        raise SystemExit(f"[error] {context}: missing paths -> {', '.join(missing)}")


def _write_manifest(out_path: Path, rows: List[dict]) -> None:
    """Пишет общий manifest CSV с данными аннотаций.

    Создаёт директорию при необходимости, записывает заголовок и строки
    в формате CSV с кодировкой UTF-8.

    Args:
        out_path (Path): Путь к выходному CSV-файлу.
        rows (List[dict]): Список словарей с данными аннотаций.

    Returns:
        None

    Raises:
        OSError: При проблемах с записью файла.
    """
    _ensure_out_dir(out_path.parent)
    fieldnames = [
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
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _maybe_copy_image(src_dir: Path, file_name: str, dest_dir: Path) -> None:
    """При необходимости копирует изображение в выходную папку.

    Создаёт родительские директории при необходимости, копирует файл
    с метаданными (время модификации и т.д.), или предупреждает если файл отсутствует.

    Args:
        src_dir (Path): Исходная директория с изображениями.
        file_name (str): Имя файла изображения.
        dest_dir (Path): Целевая директория для копирования.

    Returns:
        None

    Raises:
        OSError: При проблемах с копированием файла.
    """
    src = src_dir / file_name
    dst = dest_dir / file_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
    else:
        print(f"[warn] missing image file, skip copy: {src}")


def process_coco(
    annotations_path: Path,
    images_dir: Path,
    out_dir: Path,
    split: str,
    limit_per_class: int,
    copy_images: bool,
) -> None:
    """Строит подмножество COCO и приводит его к проектным классам.

    Загружает COCO JSON, фильтрует аннотации по классам, ограничивает
    количество примеров на класс, преобразует bbox в абсолютные координаты,
    маппит классы на проектные и записывает manifest. При необходимости копирует изображения.

    Args:
        annotations_path (Path): Путь к JSON-файлу с аннотациями COCO.
        images_dir (Path): Директория с изображениями COCO.
        out_dir (Path): Выходная директория для manifest и изображений.
        split (str): Тип сплита ('train', 'val' и т.д.).
        limit_per_class (int): Максимальное количество примеров на класс.
        copy_images (bool): Копировать ли изображения в выходную директорию.

    Returns:
        None

    Raises:
        SystemExit: Если входные файлы не найдены.
        JSONDecodeError: При ошибках парсинга JSON.
    """
    _require_paths_exist([annotations_path, images_dir], "COCO input")
    _ensure_out_dir(out_dir)
    data = json.loads(annotations_path.read_text(encoding="utf-8"))
    cat_id_to_name = {c["id"]: c["name"] for c in data["categories"]}
    name_to_project: Dict[str, str] = {}
    for project_cls, coco_names in COCO_CLASS_MAP.items():
        for name in coco_names:
            name_to_project[name] = project_cls

    images_by_id = {img["id"]: img for img in data["images"]}
    license_map = {lic["id"]: (lic.get("name") or "", lic.get("url") or "") for lic in data.get("licenses", [])}
    per_class_counter = defaultdict(int)
    rows: List[dict] = []
    copied_dir = out_dir / "images" if copy_images else None

    for ann in data["annotations"]:
        cat_name = cat_id_to_name.get(ann["category_id"])
        if not cat_name:
            continue
        mapped = name_to_project.get(cat_name)
        if not mapped:
            continue
        if per_class_counter[mapped] >= limit_per_class:
            continue

        image = images_by_id.get(ann["image_id"])
        if not image:
            continue

        lic_name, lic_url = license_map.get(image.get("license"), ("", ""))
        bbox = ann.get("bbox") or []
        if len(bbox) == 4:
            # COCO: x, y, width, height -> x1, y1, x2, y2
            x1, y1, w, h = bbox
            bbox = [x1, y1, x1 + w, y1 + h]
        row = {
            "dataset": "coco",
            "split": split,
            "image_id": image["id"],
            "file_name": image["file_name"],
            "mapped_class": mapped,
            "original_class": cat_name,
            "license_name": lic_name,
            "license_url": lic_url,
            "width": image.get("width"),
            "height": image.get("height"),
            "bbox": json.dumps(bbox),
            "source": "coco2017",
        }
        rows.append(row)
        per_class_counter[mapped] += 1
        if copy_images and copied_dir:
            _maybe_copy_image(images_dir, image["file_name"], copied_dir)

    manifest_path = out_dir / f"manifest_coco_{split}.csv"
    _write_manifest(manifest_path, rows)
    print(f"[done] coco subset rows={len(rows)} written to {manifest_path}")


def _load_openimages_label_map(class_desc_path: Path) -> Dict[str, str]:
    """Строит словарь `читаемое имя -> код класса` для Open Images.

    Args:
        class_desc_path (Path): Путь к CSV-файлу с описаниями классов Open Images.

    Returns:
        Dict[str, str]: Словарь соответствия имён классов их кодам.

    Raises:
        FileNotFoundError: Если файл не найден.
        UnicodeDecodeError: При ошибках чтения файла.
    """
    mapping: Dict[str, str] = {}
    with class_desc_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for label_code, name in reader:
            mapping[name] = label_code
    return mapping


def _load_openimages_image_meta(images_file: Path) -> Dict[str, Tuple[str, str]]:
    """Возвращает `ImageID -> (license, original_url)` для Open Images.

    Args:
        images_file (Path): Путь к CSV-файлу с метаданными изображений Open Images.

    Returns:
        Dict[str, Tuple[str, str]]: Словарь с лицензией и URL для каждого ImageID.

    Raises:
        FileNotFoundError: Если файл не найден.
        UnicodeDecodeError: При ошибках чтения файла.
    """
    meta: Dict[str, Tuple[str, str]] = {}
    with images_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            meta[row["ImageID"]] = (row.get("License", ""), row.get("OriginalURL", ""))
    return meta


def process_openimages(
    annotations_path: Path,
    class_descriptions: Path,
    images_file: Path,
    out_dir: Path,
    split: str,
    limit_per_class: int,
) -> None:
    """Строит подмножество Open Images и приводит его к проектным классам.

    Загружает CSV с аннотациями Open Images, фильтрует по классам,
    ограничивает количество примеров на класс, преобразует bbox в абсолютные координаты,
    маппит классы на проектные и записывает manifest.

    Args:
        annotations_path (Path): Путь к CSV-файлу с аннотациями bbox Open Images.
        class_descriptions (Path): Путь к CSV-файлу с описаниями классов.
        images_file (Path): Путь к CSV-файлу с метаданными изображений.
        out_dir (Path): Выходная директория для manifest.
        split (str): Тип сплита ('train', 'val' и т.д.).
        limit_per_class (int): Максимальное количество примеров на класс.

    Returns:
        None

    Raises:
        SystemExit: Если входные файлы не найдены.
        UnicodeDecodeError: При ошибках чтения CSV.
    """
    _require_paths_exist(
        [annotations_path, class_descriptions, images_file],
        "OpenImages input",
    )
    _ensure_out_dir(out_dir)
    name_to_label = _load_openimages_label_map(class_descriptions)
    label_to_project: Dict[str, str] = {}
    for project_cls, oi_names in OPENIMAGES_CLASS_MAP.items():
        for name in oi_names:
            label_code = name_to_label.get(name)
            if not label_code:
                print(f"[warn] class '{name}' not found in class-descriptions")
                continue
            label_to_project[label_code] = project_cls

    image_meta = _load_openimages_image_meta(images_file)
    per_class_counter = defaultdict(int)
    rows: List[dict] = []

    with annotations_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label_code = row["LabelName"]
            mapped = label_to_project.get(label_code)
            if not mapped:
                continue
            if per_class_counter[mapped] >= limit_per_class:
                continue
            image_id = row["ImageID"]
            bbox = [
                float(row["XMin"]),
                float(row["YMin"]),
                float(row["XMax"]),
                float(row["YMax"]),
            ]
            lic, url = image_meta.get(image_id, ("", ""))
            manifest_row = {
                "dataset": "openimages",
                "split": split,
                "image_id": image_id,
                "file_name": f"{image_id}.jpg",
                "mapped_class": mapped,
                "original_class": label_code,
                "license_name": lic,
                "license_url": url,
                "width": "",
                "height": "",
                "bbox": json.dumps(bbox),
                "source": "openimages-v6",
            }
            rows.append(manifest_row)
            per_class_counter[mapped] += 1
            # Если для всех проектных классов лимит уже набран, можно завершать раньше.
            if all(per_class_counter[c] >= limit_per_class for c in label_to_project.values()):
                break

    manifest_path = out_dir / f"manifest_openimages_{split}.csv"
    _write_manifest(manifest_path, rows)
    print(f"[done] openimages subset rows={len(rows)} written to {manifest_path}")


def main() -> None:
    """Главная функция скрипта для сборки подмножества датасета.

    Парсит аргументы командной строки и вызывает соответствующую функцию
    обработки (COCO или Open Images) на основе выбранного датасета.

    Аргументы командной строки:
    - --dataset: Тип датасета ('coco' или 'openimages', обязательно).
    - --split: Тип сплита (по умолчанию 'train').
    - --limit-per-class: Максимум примеров на класс (по умолчанию 500).
    - --out-dir: Выходная директория (обязательно).
    - --copy-images: Копировать изображения (только для COCO).
    - --coco-annotations: Путь к JSON COCO (для COCO).
    - --images-dir: Директория изображений COCO (для COCO).
    - --openimages-annotations: Путь к CSV аннотаций Open Images.
    - --openimages-class-descriptions: Путь к описаниям классов Open Images.
    - --openimages-images-file: Путь к метаданным изображений Open Images.

    Returns:
        None

    Raises:
        SystemExit: При ошибках парсинга аргументов или отсутствии обязательных файлов.
    """
    parser = argparse.ArgumentParser(description="Build a small subset from COCO or Open Images with class mapping.")
    parser.add_argument("--dataset", choices=["coco", "openimages"], required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument("--limit-per-class", type=int, default=500)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--copy-images", action="store_true", help="Copy matched images into out-dir/images (COCO only).")
    # COCO args
    parser.add_argument("--coco-annotations", type=Path, help="Path to COCO instances_<split>.json")
    parser.add_argument("--images-dir", type=Path, help="Path to COCO images directory (for copy).")
    # Open Images args
    parser.add_argument("--openimages-annotations", type=Path, help="Path to train/val/test-annotations-bbox.csv")
    parser.add_argument("--openimages-class-descriptions", type=Path, help="Path to class-descriptions-boxable.csv")
    parser.add_argument(
        "--openimages-images-file",
        type=Path,
        help="Path to *-images-boxable-with-rotation.csv (for licenses/urls).",
    )
    args = parser.parse_args()

    if args.dataset == "coco":
        if not args.coco_annotations or not args.images_dir:
            raise SystemExit("COCO requires --coco-annotations and --images-dir")
        process_coco(
            annotations_path=args.coco_annotations,
            images_dir=args.images_dir,
            out_dir=args.out_dir,
            split=args.split,
            limit_per_class=args.limit_per_class,
            copy_images=bool(args.copy_images),
        )
    else:
        if not (args.openimages_annotations and args.openimages_class_descriptions and args.openimages_images_file):
            raise SystemExit(
                "Open Images requires --openimages-annotations, --openimages-class-descriptions, and --openimages-images-file"
            )
        process_openimages(
            annotations_path=args.openimages_annotations,
            class_descriptions=args.openimages_class_descriptions,
            images_file=args.openimages_images_file,
            out_dir=args.out_dir,
            split=args.split,
            limit_per_class=args.limit_per_class,
        )


if __name__ == "__main__":
    main()
