"""
Invoice field extractor — paragraph/table YOLO + Tesseract OCR pipeline.

Pipeline:
    1. Download file from MinIO
    2. Convert to PIL Image (handles PDF via PyMuPDF)
    3. Run YOLOv8 to detect paragraph/table regions (2 classes)
    4. Deduplicate overlapping boxes of the same class
    5. Crop each kept region
    6. OCR each crop with Tesseract
    7. Extract structured invoice fields from grouped region text
"""
from __future__ import annotations

import io
import os
import re
import unicodedata
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TypedDict

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ML_DIR, "models")

CLASS_NAMES = {0: "paragraph", 1: "table"}

# Lazy-loaded YOLO model singleton
_yolo_model = None


def _load_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        path = os.path.join(MODELS_DIR, "yolo_paragraph.pt")
        _yolo_model = YOLO(path)
        logger.info("Paragraph YOLO model loaded from %s", path)
    return _yolo_model


# ── MinIO helper ──────────────────────────────────────────────────────────────

def _download_from_minio(storage_key: str) -> bytes:
    from apps.documents.storage import _s3_client
    from django.conf import settings
    client = _s3_client()
    response = client.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=storage_key)
    return response["Body"].read()


# ── File → image conversion ───────────────────────────────────────────────────

def _to_image(file_bytes: bytes, content_type: str) -> Image.Image:
    """Convert raw file bytes to a PIL RGB Image."""
    if content_type == "application/pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            doc.close()
            return img
        except ImportError:
            from pdf2image import convert_from_bytes
            return convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=200)[0]
    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


# ── Bounding box helpers ──────────────────────────────────────────────────────

def _box_iou(box_a: list, box_b: list) -> float:
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
    return inter_area / union if union > 0 else 0.0


def _containment_ratio(box_a: list, box_b: list) -> float:
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
    return inter_area / smaller if smaller > 0 else 0.0


def _filter_detections(
    detections: list,
    dedup_iou: float = 0.6,
    containment_threshold: float = 0.85,
    max_paragraphs: int = 12,
    max_tables: int = 3,
) -> list:
    """Deduplicate same-label boxes and cap counts per label."""
    kept = []
    counts = {"paragraph": 0, "table": 0}

    for det in sorted(detections, key=lambda d: d["confidence"], reverse=True):
        label = det["label"]
        limit = max_tables if label == "table" else max_paragraphs
        if counts[label] >= limit:
            continue

        duplicate = False
        for existing in kept:
            if existing["label"] != label:
                continue
            if _box_iou(existing["xyxy"], det["xyxy"]) >= dedup_iou:
                duplicate = True
                break
            if _containment_ratio(existing["xyxy"], det["xyxy"]) >= containment_threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(det)
            counts[label] += 1

    kept.sort(key=lambda d: (d["xyxy"][1], d["xyxy"][0]))
    return kept


def _padded_box(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    image_width: int,
    image_height: int,
    pad_ratio: float = 0.02,
    min_pad: int = 12,
) -> tuple[int, int, int, int]:
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    pad_x = max(min_pad, int(round(width * pad_ratio)))
    pad_y = max(min_pad, int(round(height * pad_ratio)))
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(image_width, x2 + pad_x),
        min(image_height, y2 + pad_y),
    )


# ── OCR helpers ───────────────────────────────────────────────────────────────

def _ocr_crop_tesseract(crop: Image.Image, lang: str = "eng+fra") -> list[_OCRLine]:
    """Run Tesseract on a PIL image crop and return grouped OCR lines."""
    return _group_lines(_shared_ocr_pil_tesseract(crop, lang))


_MIN_TOKEN_CONFIDENCE = 0.3


@dataclass
class _OCRToken:
    text: str
    confidence: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def center_x(self) -> float:
        return (self.xmin + self.xmax) / 2.0

    @property
    def center_y(self) -> float:
        return (self.ymin + self.ymax) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.ymax - self.ymin)


@dataclass
class _OCRLine:
    text: str
    tokens: list[_OCRToken]


def _shared_ocr_pil_tesseract(image: Image.Image, lang: str = "eng+fra") -> list[_OCRToken]:
    """Run Tesseract on a PIL image and return filtered OCR tokens."""
    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    tokens: list[_OCRToken] = []
    for index, text in enumerate(data["text"]):
        text = str(text).strip()
        if not text:
            continue
        confidence = float(data["conf"][index])
        if confidence < 0:
            continue
        xmin = float(data["left"][index])
        ymin = float(data["top"][index])
        width = float(data["width"][index])
        height = float(data["height"][index])
        tokens.append(_OCRToken(
            text=text,
            confidence=confidence / 100.0,
            xmin=xmin,
            ymin=ymin,
            xmax=xmin + width,
            ymax=ymin + height,
        ))
    tokens = [t for t in tokens if t.confidence > _MIN_TOKEN_CONFIDENCE]
    tokens.sort(key=lambda t: (t.center_y, t.xmin))
    return tokens


_COLUMN_GAP_FACTOR = 4.0  # horizontal gap > this × median height = different column


def _group_lines(tokens: list[_OCRToken]) -> list[_OCRLine]:
    if not tokens:
        return []

    heights = sorted(t.height for t in tokens)
    median_height = heights[len(heights) // 2]
    y_tolerance = max(6.0, median_height * 0.5)
    gap_threshold = median_height * _COLUMN_GAP_FACTOR

    lines: list[list[_OCRToken]] = []
    for token in tokens:
        placed = False
        for line_tokens in lines:
            avg_y = sum(t.center_y for t in line_tokens) / len(line_tokens)
            if abs(token.center_y - avg_y) > y_tolerance:
                continue
            line_xmin = min(t.xmin for t in line_tokens)
            line_xmax = max(t.xmax for t in line_tokens)
            if token.xmin > line_xmax + gap_threshold or token.xmax < line_xmin - gap_threshold:
                continue
            line_tokens.append(token)
            placed = True
            break
        if not placed:
            lines.append([token])

    result = []
    for line_tokens in lines:
        line_tokens.sort(key=lambda t: t.xmin)
        text = " ".join(t.text for t in line_tokens).strip()
        result.append(_OCRLine(text=text, tokens=line_tokens))
    result.sort(key=lambda ln: (min(t.center_y for t in ln.tokens), min(t.xmin for t in ln.tokens)))
    return result


# ── Field extraction ──────────────────────────────────────────────────────────
# Extraction is delegated to ai.extraction.ocr_after_yolo_segmentation.extract_fields_from_regions


# ── Post-processing ───────────────────────────────────────────────────────────

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
    "%d/%m/%y", "%d-%m-%y",
    "%B %d, %Y", "%b %d, %Y",
    "%d %B %Y", "%d %b %Y",
]


def _parse_date(text: str):
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(text: str):
    if not text:
        return None
    cleaned = re.sub(r"[€$£\s]", "", text)
    if re.match(r"^\d[\d\s]*,\d{2}$", cleaned):
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _infer_currency(text: str) -> str:
    if not text:
        return ""
    if "€" in text or "EUR" in text.upper():
        return "EUR"
    if "$" in text or "USD" in text.upper():
        return "USD"
    if "£" in text or "GBP" in text.upper():
        return "GBP"
    return ""


# ── Public interface ──────────────────────────────────────────────────────────

class ExtractionOutput(TypedDict):
    invoice_number: str
    invoice_date: object    # date | None
    due_date: object        # date | None
    issuer_name: str
    recipient_name: str
    total_amount: object    # Decimal | None
    currency: str
    raw_text: str
    confidence_map: dict


def extract_invoice_fields(storage_key: str, content_type: str) -> ExtractionOutput:
    """
    Extract structured invoice fields from a document stored in MinIO.

    Uses paragraph/table region detection + Tesseract OCR on each region,
    followed by anchor-based field extraction.
    """
    model = _load_yolo()

    file_bytes = _download_from_minio(storage_key)
    img = _to_image(file_bytes, content_type)

    results = model.predict(img, imgsz=960, conf=0.45, iou=0.35, verbose=False)

    raw_detections = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            cls_id = int(box.cls.item())
            raw_detections.append({
                "label": CLASS_NAMES.get(cls_id, str(cls_id)),
                "confidence": round(float(box.conf.item()), 4),
                "xyxy": [round(float(v), 2) for v in box.xyxy[0].tolist()],
            })

    detections = _filter_detections(raw_detections)
    logger.info("Paragraph YOLO: %d raw → %d kept detections", len(raw_detections), len(detections))

    regions = []
    for region_index, det in enumerate(detections):
        x1, y1, x2, y2 = [int(round(v)) for v in det["xyxy"]]
        x1, y1, x2, y2 = _padded_box(x1, y1, x2, y2, img.width, img.height)

        crop = img.crop((x1, y1, x2, y2))
        ocr_lines = _ocr_crop_tesseract(crop)

        region_text = "\n".join(ln.text for ln in ocr_lines if ln.text.strip())
        region_lines = [ln.text for ln in ocr_lines if ln.text.strip()]

        regions.append({
            **det,
            "region_index": region_index,
            "text": region_text,
            "lines": region_lines,
            "line_count": len(region_lines),
        })

    from ai.extraction.ocr_after_yolo_segmentation.extract_fields_from_regions import extract_fields_from_region_payload
    extracted = extract_fields_from_region_payload({"regions": regions})

    def fval(field: str) -> str:
        return extracted.get(field, {}).get("value") or ""

    total_text = fval("Total")
    raw_text = "\n\n".join(
        f"[{r['label']}]\n{r['text']}" for r in regions if r.get("text")
    )

    logger.info(
        "Extraction result — invoice_number=%r date=%r due=%r issuer=%r recipient=%r total=%r currency=%r",
        fval("Invoice_Number"),
        fval("Invoice_Date"),
        fval("Due_Date"),
        fval("Issuer_Name"),
        fval("Client_Name"),
        fval("Total"),
        _infer_currency(total_text),
    )

    return ExtractionOutput(
        invoice_number=fval("Invoice_Number"),
        invoice_date=_parse_date(fval("Invoice_Date")),
        due_date=_parse_date(fval("Due_Date")),
        issuer_name=fval("Issuer_Name"),
        recipient_name=fval("Client_Name"),
        total_amount=_parse_amount(total_text),
        currency=_infer_currency(total_text),
        raw_text=raw_text,
        confidence_map={
            "invoice_number": 0.8 if fval("Invoice_Number") else 0.0,
            "invoice_date": 0.8 if fval("Invoice_Date") else 0.0,
            "due_date": 0.8 if fval("Due_Date") else 0.0,
            "issuer_name": 0.8 if fval("Issuer_Name") else 0.0,
            "recipient_name": 0.8 if fval("Client_Name") else 0.0,
            "total_amount": 0.8 if total_text else 0.0,
        },
    )
