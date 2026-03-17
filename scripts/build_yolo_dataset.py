"""Сборка единого YOLO-датасета из manifest CSV.

Скрипт берёт уже нормализованные manifest-файлы, подтягивает исходные картинки
из разных датасетов и раскладывает всё в структуру, которую понимает Ultralytics:

- `images/train`, `images/val`
- `labels/train`, `labels/val`
- `dataset.yaml`

Пример:
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
    """Безопасно преобразует строку в число с плавающей точкой.

    Если преобразование невозможно (например, пустая строка или нечисловое значение),
    возвращает 0.0 вместо вызова исключения. Это полезно при обработке
    CSV-файлов с потенциально повреждёнными данными.

    Args:
        value: Строка для преобразования.

    Returns:
        Число с плавающей точкой или 0.0 в случае ошибки.
    """
    try:
        return float(value)
    except Exception:
        return 0.0


def _load_manifest(path: Path) -> List[dict]:
    """Загружает manifest-файл в формате CSV в список словарей.

    Функция читает CSV-файл с заголовками, где каждая строка
    представляет собой запись с аннотациями для датасета.
    Возвращает список словарей для дальнейшей обработки.

    Args:
        path: Путь к manifest CSV-файлу.

    Returns:
        Список словарей с данными из CSV.
    """
    rows: List[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _ensure_dir(path: Path) -> None:
    """Создаёт директорию и все необходимые родительские директории.

    Если директория уже существует, ничего не делает.
    Используется для подготовки структуры папок перед копированием файлов.

    Args:
        path: Путь к директории для создания.
    """
    path.mkdir(parents=True, exist_ok=True)


def _link_or_copy(src: Path, dst: Path, mode: str) -> None:
    """Копирует файл или создаёт hardlink в зависимости от режима.

    В режиме 'link' пытается создать hardlink для экономии дискового пространства.
    Если hardlink невозможен (например, на разных файловых системах),
    откатывается к обычному копированию файла. Если файл назначения уже существует,
    ничего не делает.

    Args:
        src: Путь к исходному файлу.
        dst: Путь к файлу назначения.
        mode: Режим ('link' для hardlink, иначе копирование).
    """
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
    """Определяет корневую директорию с изображениями для данной записи.

    На основе dataset и split из manifest-строки возвращает путь
    к папке с исходными изображениями. Поддерживает датасеты:
    COCO, RPC, SKU110k, Grozi.

    Args:
        row: Словарь с данными строки manifest.
        paths: Словарь с путями к директориям изображений.

    Returns:
        Путь к корневой директории изображений или None, если dataset неизвестен.
    """
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
    """Группирует строки manifest по уникальным изображениям.

    В исходных manifest-файлах одно изображение может иметь несколько
    аннотаций (bbox), поэтому строки группируются по ключу
    (dataset, split, image_id, file_name). Это позволяет собрать
    все bbox для одного изображения перед записью YOLO label-файла.

    Args:
        rows: Итератор по строкам manifest.

    Returns:
        Словарь, где ключ - кортеж (dataset, split, image_id, file_name),
        значение - список строк для этого изображения.
    """
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
    """Записывает YOLO label-файл для одного изображения.

    Преобразует абсолютные координаты bbox из manifest в нормализованный
    формат YOLO (центр и размеры относительно ширины/высоты изображения).
    Пропускает классы, не входящие в список classes.

    Args:
        label_path: Путь к выходному label-файлу (.txt).
        rows: Список строк manifest для одного изображения.
        class_to_idx: Словарь соответствия названий классов их индексам.
    """
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
    """Создаёт структуру YOLO-датасета из manifest-файлов.

    Загружает train и val manifest, группирует аннотации по изображениям,
    копирует или линкует изображения в соответствующие папки, записывает
    label-файлы в формате YOLO и создаёт dataset.yaml для Ultralytics.

    Args:
        train_manifest: Путь к manifest для тренировочных данных.
        val_manifest: Путь к manifest для валидационных данных.
        out_dir: Выходная директория для датасета.
        paths: Словарь путей к исходным изображениям по датасетам.
        classes: Список названий классов.
        mode: Режим копирования ('link' или 'copy').
        max_images_per_dataset: Максимум изображений на датасет (опционально).
        seed: Seed для случайности.
    """
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
            # Одинаковые имена файлов могут приехать из разных датасетов,
            # поэтому раскладываем их по подпапкам dataset.
            rel_img_dir = Path(dataset)
            out_img = out_img_dir / rel_img_dir / file_name
            out_lbl = out_lbl_dir / rel_img_dir / f"{Path(file_name).stem}.txt"

            _link_or_copy(src_img, out_img, mode)
            _write_labels(out_lbl, items, class_to_idx)

    # Финальный `dataset.yaml` — входная точка для обучения через Ultralytics.
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
    """Главная функция скрипта для сборки YOLO-датасета.

    Парсит аргументы командной строки, подготавливает пути и классы,
    затем вызывает build_dataset для создания датасета.
    """
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
