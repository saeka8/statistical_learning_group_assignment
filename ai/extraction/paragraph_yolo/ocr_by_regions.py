from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.extraction.OCR_method.extract_invoice_ocr import (
    OCRLine,
    filter_tokens,
    group_lines,
    run_easyocr,
    run_paddleocr,
    run_tesseract,
)
from ai.extraction.paragraph_yolo.extract_fields_from_regions import (
    extract_fields_from_region_payload,
)
from ai.extraction.paragraph_yolo.shared_pipeline import (
    CLASS_NAMES,
    filter_detections,
    padded_box,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "best.pt"
OUTPUT_DIR = ROOT / "region_ocr"
DEFAULT_PAD_RATIO = 0.02
DEFAULT_PAD_MIN = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect paragraph/table regions, then OCR each kept region separately."
    )
    parser.add_argument("--image", required=True, help="Path to the invoice image.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to YOLO checkpoint.")
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--conf", type=float, default=0.45)
    parser.add_argument("--iou", type=float, default=0.35, help="YOLO NMS IoU threshold.")
    parser.add_argument("--dedup-iou", type=float, default=0.6, help="Extra same-label suppression threshold.")
    parser.add_argument(
        "--containment-threshold",
        type=float,
        default=0.85,
        help="Suppress same-label boxes when one is mostly contained in another.",
    )
    parser.add_argument("--device", default="mps")
    parser.add_argument("--name", default="region_ocr_test")
    parser.add_argument(
        "--engine",
        choices=["auto", "easyocr", "paddleocr", "tesseract"],
        default="auto",
        help="OCR engine to use for each detected region.",
    )
    parser.add_argument("--easyocr-langs", default="en,fr")
    parser.add_argument("--tesseract-lang", default="eng+fra")
    parser.add_argument("--max-paragraphs", type=int, default=12)
    parser.add_argument("--max-tables", type=int, default=3)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()

def run_region_ocr(
    engine: str,
    image_path: Path,
    easyocr_langs: str,
    tesseract_lang: str,
) -> tuple[str, list[OCRLine]]:
    if engine == "auto":
        failures: list[str] = []
        for backend in ("paddleocr", "easyocr", "tesseract"):
            try:
                return backend, ocr_lines_for_engine(backend, image_path, easyocr_langs, tesseract_lang)
            except Exception as exc:
                failures.append(f"{backend}: {exc.__class__.__name__}: {exc}")
                continue
        raise SystemExit(
            "No OCR engine available. Tried paddleocr, easyocr, and tesseract.\n"
            + "\n".join(failures)
        )

    return engine, ocr_lines_for_engine(engine, image_path, easyocr_langs, tesseract_lang)


def ocr_lines_for_engine(
    engine: str,
    image_path: Path,
    easyocr_langs: str,
    tesseract_lang: str,
) -> list[OCRLine]:
    if engine == "easyocr":
        tokens = run_easyocr(image_path, easyocr_langs)
    elif engine == "paddleocr":
        tokens = run_paddleocr(image_path)
    elif engine == "tesseract":
        tokens = run_tesseract(image_path, tesseract_lang)
    else:
        raise ValueError(f"Unsupported OCR engine: {engine}")
    return group_lines(filter_tokens(tokens))


def padded_box(x1: int, y1: int, x2: int, y2: int, image_width: int, image_height: int) -> tuple[int, int, int, int]:
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    pad_x = max(DEFAULT_PAD_MIN, int(round(width * DEFAULT_PAD_RATIO)))
    pad_y = max(DEFAULT_PAD_MIN, int(round(height * DEFAULT_PAD_RATIO)))
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(image_width, x2 + pad_x),
        min(image_height, y2 + pad_y),
    )


def main() -> int:
    from ultralytics import YOLO

    args = parse_args()
    image_path = Path(args.image).expanduser().resolve()
    model_path = Path(args.model).expanduser().resolve()

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    output_root = OUTPUT_DIR / args.name
    crops_dir = output_root / "crops"
    output_root.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(model_path))
    results = model.predict(
        source=str(image_path),
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        save=True,
        project=str(OUTPUT_DIR),
        name=args.name,
        exist_ok=True,
    )

    raw_detections: list[dict] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        for box in boxes:
            cls_id = int(box.cls.item())
            label = CLASS_NAMES.get(cls_id, str(cls_id))
            raw_detections.append(
                {
                    "label": label,
                    "confidence": round(float(box.conf.item()), 4),
                    "xyxy": [round(float(value), 2) for value in box.xyxy[0].tolist()],
                }
            )

    detections = filter_detections(
        raw_detections,
        dedup_iou=args.dedup_iou,
        containment_threshold=args.containment_threshold,
        max_paragraphs=args.max_paragraphs,
        max_tables=args.max_tables,
        add_region_index=True,
    )

    image = Image.open(image_path)
    image_width, image_height = image.size
    regions = []
    chosen_engine: str | None = None

    for detection in detections:
        x1, y1, x2, y2 = [int(round(value)) for value in detection["xyxy"]]
        x1, y1, x2, y2 = padded_box(x1, y1, x2, y2, image_width, image_height)
        crop_path = crops_dir / f"{detection['region_index']:02d}_{detection['label']}.png"
        image.crop((x1, y1, x2, y2)).save(crop_path)

        engine, lines = run_region_ocr(
            args.engine,
            crop_path,
            args.easyocr_langs,
            args.tesseract_lang,
        )
        chosen_engine = chosen_engine or engine

        regions.append(
            {
                **detection,
                "crop_path": str(crop_path),
                "line_count": len(lines),
                "text": "\n".join(line.text for line in lines if line.text.strip()),
                "lines": [line.text for line in lines if line.text.strip()],
            }
        )

    payload = {
        "image": str(image_path),
        "model": str(model_path),
        "ocr_engine": chosen_engine,
        "raw_detection_count": len(raw_detections),
        "kept_detection_count": len(detections),
        "regions": regions,
    }
    payload["extracted_fields"] = extract_fields_from_region_payload(payload)

    json_path = output_root / "region_ocr.json"
    json_path.write_text(
        json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False),
        encoding="utf-8",
    )
    extracted_path = output_root / "extracted_fields.json"
    extracted_path.write_text(
        json.dumps(
            {
                "image": str(image_path),
                "model": str(model_path),
                "ocr_engine": chosen_engine,
                "extracted_fields": payload["extracted_fields"],
            },
            indent=2 if args.pretty else None,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Saved grouped OCR output to: {json_path}")
    print(f"Saved extracted fields to: {extracted_path}")
    print(f"Saved region crops to: {crops_dir}")
    print(f"Raw detections: {len(raw_detections)}")
    print(f"Kept detections: {len(detections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
