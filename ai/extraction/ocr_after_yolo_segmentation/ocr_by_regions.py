from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.Feature_Extraction_Invoice.OCR_method.extract_invoice_ocr import (
    OCRLine,
    filter_tokens,
    group_lines,
    run_easyocr,
    run_paddleocr,
    run_tesseract,
)
from ai.Feature_Extraction_Invoice.paragraph_yolo.extract_fields_from_regions import (
    extract_fields_from_region_payload,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "best.pt"
OUTPUT_DIR = ROOT / "region_ocr"
CLASS_NAMES = {0: "paragraph", 1: "table"}


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


def box_iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def containment_ratio(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    smaller = min(area_a, area_b)
    if smaller <= 0:
        return 0.0
    return inter_area / smaller


def filter_detections(
    detections: list[dict],
    dedup_iou: float,
    containment_threshold: float,
    max_paragraphs: int,
    max_tables: int,
) -> list[dict]:
    kept: list[dict] = []
    counts = {"paragraph": 0, "table": 0}

    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        label = detection["label"]
        limit = max_tables if label == "table" else max_paragraphs
        if counts[label] >= limit:
            continue

        duplicate = False
        for existing in kept:
            if existing["label"] != label:
                continue
            if box_iou(existing["xyxy"], detection["xyxy"]) >= dedup_iou:
                duplicate = True
                break
            if containment_ratio(existing["xyxy"], detection["xyxy"]) >= containment_threshold:
                duplicate = True
                break
        if duplicate:
            continue

        kept.append(detection)
        counts[label] += 1

    kept.sort(key=lambda item: (item["xyxy"][1], item["xyxy"][0]))
    for index, detection in enumerate(kept, start=1):
        detection["region_index"] = index
    return kept


def run_region_ocr(
    engine: str,
    image_path: Path,
    easyocr_langs: str,
    tesseract_lang: str,
) -> tuple[str, list[OCRLine]]:
    if engine == "auto":
        for backend in ("paddleocr", "easyocr", "tesseract"):
            try:
                return backend, ocr_lines_for_engine(backend, image_path, easyocr_langs, tesseract_lang)
            except ModuleNotFoundError:
                continue
        raise SystemExit(
            "No OCR engine available. Install one of: paddleocr, easyocr, or pytesseract+tesseract."
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
    )

    image = Image.open(image_path)
    regions = []
    chosen_engine: str | None = None

    for detection in detections:
        x1, y1, x2, y2 = [int(round(value)) for value in detection["xyxy"]]
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
