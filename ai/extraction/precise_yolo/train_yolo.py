#!/usr/bin/env python3
"""Prepare the invoice dataset for YOLO and optionally launch training.

Examples:
  python3 ai/extraction/precise_yolo/train_yolo.py --prepare-only
  python3 ai/extraction/precise_yolo/train_yolo.py --epochs 100 --model yolov8n.pt
  python3 ai/extraction/precise_yolo/train_yolo.py --resume
  python3 ai/extraction/precise_yolo/train_yolo.py --checkpoint ai/extraction/precise_yolo/runs/invoice_fields/weights/last.pt --imgsz 640 --epochs 20 --name invoice_fields_640
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
SOURCE_DIR = PROJECT_ROOT / "dataset"
ANNOTATIONS_CSV = SOURCE_DIR / "_annotations.csv"
YOLO_DIR = ROOT / "yolo_dataset"
RUNS_DIR = ROOT / "runs"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare YOLO dataset and optionally train Ultralytics YOLO.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction, between 0 and 1")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for train/val split")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO base model")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=1280, help="Training image size")
    parser.add_argument("--batch", type=int, default=8, help="Training batch size")
    parser.add_argument("--project", default=str(RUNS_DIR), help="Ultralytics project directory")
    parser.add_argument("--name", default="invoice_fields", help="Ultralytics run name")
    parser.add_argument("--device", default=None, help="Device passed to YOLO, e.g. cpu, 0, mps")
    parser.add_argument("--resume", action="store_true", help="Resume the latest run from weights/last.pt")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Start training from a saved .pt checkpoint")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare dataset, do not start training")
    parser.add_argument("--force", action="store_true", help="Delete and rebuild output dataset directory if it exists")
    return parser


def load_annotations(csv_path: Path) -> tuple[dict[str, list[dict[str, float | str]]], list[str]]:
    grouped: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    class_names: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"filename", "width", "height", "class", "xmin", "ymin", "xmax", "ymax"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        for row in reader:
            filename = row["filename"]
            grouped[filename].append(
                {
                    "width": float(row["width"]),
                    "height": float(row["height"]),
                    "class": row["class"],
                    "xmin": float(row["xmin"]),
                    "ymin": float(row["ymin"]),
                    "xmax": float(row["xmax"]),
                    "ymax": float(row["ymax"]),
                }
            )
            class_names.add(row["class"])

    return grouped, sorted(class_names)


def clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def to_yolo_line(annotation: dict[str, float | str], class_to_id: dict[str, int]) -> str:
    width = float(annotation["width"])
    height = float(annotation["height"])
    xmin = float(annotation["xmin"])
    ymin = float(annotation["ymin"])
    xmax = float(annotation["xmax"])
    ymax = float(annotation["ymax"])
    label = str(annotation["class"])

    x_center = clamp(((xmin + xmax) / 2.0) / width)
    y_center = clamp(((ymin + ymax) / 2.0) / height)
    box_width = clamp((xmax - xmin) / width)
    box_height = clamp((ymax - ymin) / height)

    return f"{class_to_id[label]} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def recreate_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_split(
    split_name: str,
    filenames: list[str],
    annotations_by_image: dict[str, list[dict[str, float | str]]],
    class_to_id: dict[str, int],
    source_dir: Path,
    output_dir: Path,
) -> tuple[int, list[str]]:
    images_dir = output_dir / "images" / split_name
    labels_dir = output_dir / "labels" / split_name
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing_files: list[str] = []

    for filename in filenames:
        source_path = source_dir / filename
        if not source_path.exists():
            missing_files.append(filename)
            continue

        shutil.copy2(source_path, images_dir / filename)
        label_path = labels_dir / f"{Path(filename).stem}.txt"
        lines = [
            to_yolo_line(annotation, class_to_id)
            for annotation in annotations_by_image[filename]
        ]
        label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        copied += 1

    return copied, missing_files


def write_data_yaml(output_dir: Path, class_names: list[str]) -> Path:
    yaml_path = output_dir / "data.yaml"
    lines = [
        f"path: {output_dir.resolve()}",
        "train: images/train",
        "val: images/val",
        "",
        "names:",
    ]
    lines.extend(f"  {idx}: {name}" for idx, name in enumerate(class_names))
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return yaml_path


def get_last_checkpoint(project_dir: Path, run_name: str) -> Path:
    return project_dir / run_name / "weights" / "last.pt"


def prepared_dataset_is_usable(output_dir: Path) -> bool:
    yaml_path = output_dir / "data.yaml"
    if not yaml_path.exists():
        return False

    for split_name in ("train", "val"):
        labels_dir = output_dir / "labels" / split_name
        images_dir = output_dir / "images" / split_name
        if not labels_dir.exists() or not images_dir.exists():
            return False

        for label_path in labels_dir.glob("*.txt"):
            stem = label_path.stem
            has_image = any((images_dir / f"{stem}{suffix}").exists() for suffix in (".jpg", ".jpeg", ".png"))
            if not has_image:
                return False

    return True


def prepare_dataset(args: argparse.Namespace) -> tuple[Path, list[str], dict[str, int]]:
    annotations_by_image, class_names = load_annotations(ANNOTATIONS_CSV)
    class_to_id = {name: idx for idx, name in enumerate(class_names)}

    if YOLO_DIR.exists():
        if args.force:
            recreate_dir(YOLO_DIR)
        else:
            yaml_path = YOLO_DIR / "data.yaml"
            if prepared_dataset_is_usable(YOLO_DIR):
                yaml_path = write_data_yaml(YOLO_DIR, class_names)
                print(f"Reusing prepared YOLO dataset at {YOLO_DIR}")
                print(f"Classes ({len(class_names)}): {class_names}")
                print(f"data.yaml: {yaml_path}")
                return yaml_path, class_names, class_to_id
            print(f"Prepared dataset at {YOLO_DIR} is incomplete. Rebuilding it.")
            recreate_dir(YOLO_DIR)
    else:
        YOLO_DIR.mkdir(parents=True, exist_ok=True)

    filenames = sorted(annotations_by_image)
    random.Random(args.seed).shuffle(filenames)
    val_count = max(1, int(len(filenames) * args.val_fraction))
    if val_count >= len(filenames):
        val_count = max(1, len(filenames) - 1)

    val_files = sorted(filenames[:val_count])
    train_files = sorted(filenames[val_count:])

    train_count, missing_train = copy_split(
        "train", train_files, annotations_by_image, class_to_id, SOURCE_DIR, YOLO_DIR
    )
    val_count_actual, missing_val = copy_split(
        "val", val_files, annotations_by_image, class_to_id, SOURCE_DIR, YOLO_DIR
    )
    yaml_path = write_data_yaml(YOLO_DIR, class_names)

    missing_files = missing_train + missing_val
    print(f"Prepared YOLO dataset at {YOLO_DIR}")
    print(f"Classes ({len(class_names)}): {class_names}")
    print(f"Train images copied: {train_count}")
    print(f"Val images copied: {val_count_actual}")
    print(f"data.yaml: {yaml_path}")
    if missing_files:
        print(f"Missing image files skipped: {len(missing_files)}")
        for filename in missing_files[:20]:
            print(f"  - {filename}")
    return yaml_path, class_names, class_to_id


def run_training(args: argparse.Namespace, yaml_path: Path) -> int:
    try:
        from ultralytics import YOLO
    except ModuleNotFoundError:
        print("Ultralytics is not installed.")
        print("Install it with: pip install ultralytics")
        return 1

    kwargs = {
        "data": str(yaml_path),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": args.project,
        "name": args.name,
    }
    if args.device:
        kwargs["device"] = args.device

    project_dir = Path(args.project)
    checkpoint = args.checkpoint
    if args.resume:
        checkpoint = get_last_checkpoint(project_dir, args.name)
        if not checkpoint.exists():
            print(f"No checkpoint found at {checkpoint}")
            print("Train once first, or use --checkpoint <path/to/weights.pt>.")
            return 1
        print("Resuming YOLO training with:")
        print(f"  checkpoint={checkpoint}")
        model = YOLO(str(checkpoint))
        model.train(resume=True)
        return 0

    if checkpoint is not None:
        checkpoint = checkpoint.resolve()
        if not checkpoint.exists():
            print(f"Checkpoint not found: {checkpoint}")
            return 1
        model_source = str(checkpoint)
        print("Continuing YOLO training from checkpoint with new settings:")
        print(f"  checkpoint={checkpoint}")
    else:
        model_source = args.model
        print("Running YOLO training with:")
        print(f"  model={args.model}")

    print(f"  data={yaml_path}")
    print(f"  epochs={args.epochs}")
    print(f"  imgsz={args.imgsz}")
    print(f"  batch={args.batch}")
    print(f"  project={args.project}")
    print(f"  name={args.name}")
    if args.device:
        print(f"  device={args.device}")

    model = YOLO(model_source)
    model.train(**kwargs)
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not 0.0 < args.val_fraction < 1.0:
        parser.error("--val-fraction must be between 0 and 1")

    yaml_path, _, _ = prepare_dataset(args)
    if args.prepare_only:
        return 0
    return run_training(args, yaml_path)


if __name__ == "__main__":
    raise SystemExit(main())
