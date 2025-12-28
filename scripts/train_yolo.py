"""
Train a YOLO detector using Ultralytics on the unified dataset.yaml.

Example:
  python scripts/train_yolo.py ^
    --data D:/tmp/yolo_all/dataset.yaml ^
    --model yolov8n.pt ^
    --epochs 50 ^
    --imgsz 640 ^
    --batch 16 ^
    --device 0
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLO with Ultralytics.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", type=str, default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--project", type=str, default="runs/detect")
    parser.add_argument("--name", type=str, default="train")
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--export", action="store_true", help="Export best.pt to ONNX after training.")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:  # noqa: BLE001
        raise SystemExit("ultralytics not installed. Run: pip install ultralytics") from exc

    model = YOLO(args.model)
    results = model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=args.patience,
    )
    if args.export:
        model.export(format="onnx", imgsz=args.imgsz)
    return results


if __name__ == "__main__":
    main()
