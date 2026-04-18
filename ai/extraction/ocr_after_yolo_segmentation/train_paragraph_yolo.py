from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
SOURCE_IMAGES = ROOT / "train" / "images"
SOURCE_LABELS = ROOT / "train" / "labels"
PREPARED_DIR = ROOT / "prepared"
RUNS_DIR = ROOT / "runs"
DATA_YAML = ROOT / "data.yaml"
CLASS_NAMES = ["paragraph", "table"]
AUGMENT_SUFFIXES = (
    "_affine_translation",
    "_brightness",
    "_gaussianblur",
    "_horizontallyflip",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and train YOLO for paragraph/table invoice detection."
    )
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--name", default="paragraph_table")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint", help="Path to a YOLO checkpoint to continue from.")
    return parser.parse_args()


def document_key(image_path: Path) -> str:
    name = image_path.name
    if ".rf." in name:
        name = name.split(".rf.", 1)[0]
    stem = Path(name).stem if "." in name else name
    for suffix in ("_jpg", "_png", "_jpeg"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    for suffix in AUGMENT_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def list_image_files(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Missing image folder: {folder}")
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def build_image_label_pairs() -> list[tuple[Path, Path]]:
    images = list_image_files(SOURCE_IMAGES)
    pairs: list[tuple[Path, Path]] = []

    for image_path in images:
        label_path = SOURCE_LABELS / f"{image_path.stem}.txt"
        if not label_path.exists():
            raise FileNotFoundError(f"Missing label for {image_path.name}: {label_path}")
        pairs.append((image_path, label_path))

    if not pairs:
        raise FileNotFoundError(f"No image/label pairs found in {SOURCE_IMAGES}")

    return pairs


def split_by_document(
    pairs: Iterable[tuple[Path, Path]], val_fraction: float, seed: int
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    grouped: dict[str, list[tuple[Path, Path]]] = {}
    for image_path, label_path in pairs:
        grouped.setdefault(document_key(image_path), []).append((image_path, label_path))

    document_ids = sorted(grouped)
    random.Random(seed).shuffle(document_ids)

    val_count = max(1, round(len(document_ids) * val_fraction))
    val_ids = set(document_ids[:val_count])

    train_pairs: list[tuple[Path, Path]] = []
    val_pairs: list[tuple[Path, Path]] = []
    for doc_id, items in grouped.items():
        target = val_pairs if doc_id in val_ids else train_pairs
        target.extend(items)

    return sorted(train_pairs), sorted(val_pairs)


def ensure_clean_prepared_dir(force: bool) -> None:
    if PREPARED_DIR.exists():
        if not force:
            return
        shutil.rmtree(PREPARED_DIR)

    for split in ("train", "val"):
        (PREPARED_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (PREPARED_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)


def copy_pairs(pairs: Iterable[tuple[Path, Path]], split: str) -> None:
    image_dir = PREPARED_DIR / "images" / split
    label_dir = PREPARED_DIR / "labels" / split
    for image_path, label_path in pairs:
        shutil.copy2(image_path, image_dir / image_path.name)
        shutil.copy2(label_path, label_dir / label_path.name)


def write_data_yaml() -> Path:
    yaml_text = "\n".join(
        [
            f"path: {PREPARED_DIR}",
            "train: images/train",
            "val: images/val",
            "",
            f"nc: {len(CLASS_NAMES)}",
            f"names: {CLASS_NAMES}",
            "",
        ]
    )
    DATA_YAML.write_text(yaml_text, encoding="utf-8")
    return DATA_YAML


def prepared_dataset_exists() -> bool:
    for split in ("train", "val"):
        image_dir = PREPARED_DIR / "images" / split
        label_dir = PREPARED_DIR / "labels" / split
        if not image_dir.exists() or not label_dir.exists():
            return False
        if not any(image_dir.iterdir()) or not any(label_dir.iterdir()):
            return False
    return True


def prepare_dataset(args: argparse.Namespace) -> Path:
    pairs = build_image_label_pairs()
    train_pairs, val_pairs = split_by_document(pairs, args.val_fraction, args.seed)

    ensure_clean_prepared_dir(args.force)
    if not args.force and prepared_dataset_exists():
        return write_data_yaml()

    copy_pairs(train_pairs, "train")
    copy_pairs(val_pairs, "val")
    yaml_path = write_data_yaml()

    print(f"Prepared dataset: {yaml_path}")
    print(f"Train images: {len(train_pairs)}")
    print(f"Val images: {len(val_pairs)}")
    print(f"Unique invoice documents: {len({document_key(p[0]) for p in pairs})}")
    return yaml_path


def run_training(args: argparse.Namespace, yaml_path: Path) -> int:
    from ultralytics import YOLO

    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if args.resume:
        checkpoint = RUNS_DIR / args.name / "weights" / "last.pt"
        if not checkpoint.exists():
            raise FileNotFoundError(f"Resume checkpoint not found: {checkpoint}")
        model = YOLO(str(checkpoint))
        train_kwargs = {"resume": True}
    else:
        model_path = args.checkpoint or args.model
        model = YOLO(model_path)
        train_kwargs = {
            "data": str(yaml_path),
            "epochs": args.epochs,
            "imgsz": args.imgsz,
            "batch": args.batch,
            "device": args.device,
            "project": str(RUNS_DIR),
            "name": args.name,
        }

    print("Training with:")
    for key, value in train_kwargs.items():
        print(f"  {key}={value}")

    model.train(**train_kwargs)
    return 0


def main() -> int:
    args = parse_args()
    yaml_path = prepare_dataset(args)
    if args.prepare_only:
        return 0
    return run_training(args, yaml_path)


if __name__ == "__main__":
    raise SystemExit(main())
