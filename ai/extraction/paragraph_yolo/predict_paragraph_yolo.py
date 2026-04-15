from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "best.pt"
OUTPUT_DIR = ROOT / "predictions"
CLASS_NAMES = {0: "paragraph", 1: "table"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run paragraph/table YOLO inference on a single invoice image."
    )
    parser.add_argument("--image", required=True, help="Path to the invoice image.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to YOLO checkpoint.")
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--name", default="paragraph_test")
    return parser.parse_args()


def main() -> int:
    from ultralytics import YOLO

    args = parse_args()
    image_path = Path(args.image).expanduser().resolve()
    model_path = Path(args.model).expanduser().resolve()

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(model_path))
    results = model.predict(
        source=str(image_path),
        imgsz=args.imgsz,
        conf=args.conf,
        device=args.device,
        save=True,
        project=str(OUTPUT_DIR),
        name=args.name,
    )

    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        for box in boxes:
            cls_id = int(box.cls.item())
            xyxy = [round(float(value), 2) for value in box.xyxy[0].tolist()]
            detections.append(
                {
                    "label": CLASS_NAMES.get(cls_id, str(cls_id)),
                    "confidence": round(float(box.conf.item()), 4),
                    "xyxy": xyxy,
                }
            )

    summary = {
        "image": str(image_path),
        "model": str(model_path),
        "detections": detections,
    }
    summary_path = OUTPUT_DIR / args.name / "detections.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Saved predictions to: {OUTPUT_DIR / args.name}")
    print(f"Saved detection summary to: {summary_path}")
    print(f"Detections: {len(detections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
