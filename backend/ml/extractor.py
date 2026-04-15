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

# YOLO class names for the paragraph/table model
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


# ── OCR helpers ───────────────────────────────────────────────────────────────

@dataclass
class _OCRToken:
    text: str
    confidence: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def center_y(self) -> float:
        return (self.ymin + self.ymax) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.ymax - self.ymin)


@dataclass
class _OCRLine:
    text: str
    tokens: list


def _ocr_crop_tesseract(crop: Image.Image, lang: str = "eng+fra") -> list[_OCRLine]:
    """Run Tesseract on a PIL image crop and return grouped OCR lines."""
    data = pytesseract.image_to_data(crop, lang=lang, output_type=pytesseract.Output.DICT)
    tokens = []
    for i, text in enumerate(data["text"]):
        text = str(text).strip()
        if not text:
            continue
        conf = float(data["conf"][i]) / 100.0
        if conf <= 0.3:
            continue
        xmin = float(data["left"][i])
        ymin = float(data["top"][i])
        w = float(data["width"][i])
        h = float(data["height"][i])
        tokens.append(_OCRToken(
            text=text,
            confidence=conf,
            xmin=xmin, ymin=ymin,
            xmax=xmin + w, ymax=ymin + h,
        ))

    tokens.sort(key=lambda t: (t.center_y, t.xmin))
    return _group_lines(tokens)


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

# Regex patterns (same as paragraph_yolo/extract_fields_from_regions.py)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,5}\d{2,4})")
_MONEY_RE = re.compile(
    r"(?<!\w)(?:[A-Z]{0,3}\s*)?(?:\d{1,3}(?:[ ,.\u202f]\d{3})*|\d+)(?:[.,]\d{2})?(?:\s*(?:EUR|USD|GBP|CHF|€|\$|£))?(?!\w)"
)
_PERCENT_RE = re.compile(r"\b\d{1,2}(?:[.,]\d{1,2})?\s*%")
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\b",
    re.IGNORECASE,
)

_FIELD_NAMES = [
    "Invoice_Number", "Invoice_Date", "Client_Name", "Client_Email",
    "Client_Phone", "Billing_Address", "Shipping_Address", "Products",
    "Subtotal", "VAT", "Total", "Discount", "VAT_Rate", "Discount_Rate", "Due_Date",
    "Issuer_Name",
]

# Anchors that indicate a region belongs to the issuer/sender block
_ISSUER_ANCHORS = (
    "from:", "issued by", "emis par", "emetteur", "vendeur",
    "fournisseur", "societe", "supplier", "seller",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9%@./,_#:$€£+\- ]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _null_payload() -> dict:
    return {f: {"value": None, "method": "not_found", "evidence": None} for f in _FIELD_NAMES}


def _set_field(payload: dict, field: str, value, method: str, evidence) -> None:
    if not value:
        return
    if payload[field]["value"] is None:
        payload[field] = {"value": value, "method": method, "evidence": evidence}


def _first_date(text: str):
    m = _DATE_RE.search(text)
    return m.group(0) if m else None


def _amounts_in_text(text: str) -> list:
    return [m.group(0).strip() for m in _MONEY_RE.finditer(text)]


def _percent_in_text(text: str):
    m = _PERCENT_RE.search(text)
    return m.group(0).strip() if m else None


def _cleaned_email(text: str):
    m = _EMAIL_RE.search(text)
    if m:
        return m.group(0)
    compact = re.sub(r"\s+", "", text).replace(".con", ".com")
    m = _EMAIL_RE.search(compact)
    return m.group(0) if m else None


def _cleaned_phone(text: str):
    for m in _PHONE_RE.finditer(text):
        candidate = m.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 8:
            return candidate
    return None


def _invoice_number_from_text(text: str):
    norm = _normalize(text)
    patterns = [
        r"(?:invoice\s*(?:no|number|#)?|facture\s*(?:n|no|numero)?)\s*[:#-]?\s*([A-Z0-9./_-]{3,})",
        r"\bno\.?\s*([A-Z0-9./_-]{3,})",
    ]
    for pat in patterns:
        m = re.search(pat, norm, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if sum(c.isdigit() for c in val) >= 3:
                return val
    for token in re.findall(r"\b[A-Z0-9./_-]{4,}\b", text, re.IGNORECASE):
        if sum(c.isdigit() for c in token) >= 4:
            return token
    return None


def _extract_name(lines: list) -> str | None:
    for line in lines:
        norm = _normalize(line)
        if any(a in norm for a in ("billed to", "bill to", "shipping", "ship to", "delivered to")):
            continue
        if _cleaned_email(line) or _cleaned_phone(line):
            continue
        if any(c.isalpha() for c in line):
            return line.strip()
    return None


def _extract_address_lines(lines: list) -> str | None:
    kept = []
    for line in lines:
        norm = _normalize(line)
        if not line.strip():
            continue
        if any(a in norm for a in ("billed to", "bill to", "shipping", "ship to", "delivered to")):
            continue
        if _cleaned_email(line) or _cleaned_phone(line):
            continue
        kept.append(line.strip())
    if not kept:
        return None
    return ", ".join(kept[1:]) if len(kept) > 1 else kept[0]


def _extract_products(lines: list) -> str | None:
    products = []
    for line in lines:
        norm = _normalize(line)
        if not line.strip():
            continue
        if any(a in norm for a in ("description", "designation", "item", "items", "products")):
            continue
        if any(a in norm for a in ("subtotal", "discount", "tax", "vat", "total")):
            continue
        if len(re.findall(r"[A-Za-z]", line)) < 4:
            continue
        products.append(line.strip())
    return " | ".join(products) if products else None


def _extract_fields_from_regions(regions: list) -> dict:
    """
    Anchor-based field extraction from paragraph/table OCR regions.
    Mirrors the logic of paragraph_yolo/extract_fields_from_regions.py.
    """
    regions = sorted(regions, key=lambda r: (r["xyxy"][1], r["xyxy"][0]))
    payload = _null_payload()
    all_lines: list[tuple[str, str]] = []

    for region in regions:
        label = region.get("label", "")
        text = region.get("text", "") or ""
        lines = [ln.strip() for ln in region.get("lines", []) if ln.strip()]
        norm = _normalize(text)

        for line in lines:
            all_lines.append((line, label))

        if label == "table":
            _set_field(payload, "Products", _extract_products(lines), "table_region", text)

        if any(a in norm for a in ("description", "designation", "item", "items", "products")):
            _set_field(payload, "Products", _extract_products(lines), "paragraph_region_products", text)

        if any(a in norm for a in _ISSUER_ANCHORS):
            _set_field(payload, "Issuer_Name", _extract_name(lines), "issuer_region", text)

        if any(a in norm for a in ("billed to", "bill to", "invoice to", "customer")):
            _set_field(payload, "Client_Name", _extract_name(lines), "billing_region", text)
            _set_field(payload, "Billing_Address", _extract_address_lines(lines), "billing_region", text)
            for line in lines:
                _set_field(payload, "Client_Email", _cleaned_email(line), "billing_region", text)
                _set_field(payload, "Client_Phone", _cleaned_phone(line), "billing_region", text)

        if any(a in norm for a in ("ship to", "shipping", "delivered to", "delivery address")):
            _set_field(payload, "Shipping_Address", _extract_address_lines(lines), "shipping_region", text)

        if any(a in norm for a in ("invoice no", "invoice number", "invoice #", "date:", "due:", "due date", "terms", "amount due")):
            for line in lines:
                ln = _normalize(line)
                if "invoice" in ln:
                    _set_field(payload, "Invoice_Number", _invoice_number_from_text(line), "metadata_region", text)
                if "date" in ln and "due" not in ln:
                    _set_field(payload, "Invoice_Date", _first_date(line), "metadata_region", text)
                if "due" in ln:
                    _set_field(payload, "Due_Date", _first_date(line), "metadata_region", text)
                _set_field(payload, "Client_Email", _cleaned_email(line), "metadata_region", text)
                _set_field(payload, "Client_Phone", _cleaned_phone(line), "metadata_region", text)

        if any(a in norm for a in ("subtotal", "tax", "vat", "discount", "total")):
            for line in lines:
                ln = _normalize(line)
                amounts = _amounts_in_text(line)
                if "subtotal" in ln and amounts:
                    _set_field(payload, "Subtotal", amounts[-1], "totals_region", text)
                if ("vat" in ln or "tax" in ln) and amounts:
                    _set_field(payload, "VAT", amounts[-1], "totals_region", text)
                    _set_field(payload, "VAT_Rate", _percent_in_text(line), "totals_region", text)
                if "discount" in ln and amounts:
                    _set_field(payload, "Discount", amounts[-1], "totals_region", text)
                    _set_field(payload, "Discount_Rate", _percent_in_text(line), "totals_region", text)
                if re.search(r"\btotal\b", ln) and amounts:
                    _set_field(payload, "Total", amounts[-1], "totals_region", text)

    # Global fallback scans
    for line, _ in all_lines:
        _set_field(payload, "Client_Email", _cleaned_email(line), "global_scan", line)
        if payload["Client_Email"]["value"]:
            break

    for line, _ in all_lines:
        _set_field(payload, "Client_Phone", _cleaned_phone(line), "global_scan", line)
        if payload["Client_Phone"]["value"]:
            break

    for line, _ in all_lines:
        _set_field(payload, "Invoice_Number", _invoice_number_from_text(line), "global_scan", line)
        if payload["Invoice_Number"]["value"]:
            break

    for line, _ in all_lines:
        ln = _normalize(line)
        if "date" in ln and "due" not in ln:
            _set_field(payload, "Invoice_Date", _first_date(line), "global_scan", line)
        if "due" in ln:
            _set_field(payload, "Due_Date", _first_date(line), "global_scan", line)

    # Issuer fallback: topmost paragraph region that isn't a billing/metadata/totals block
    if payload["Issuer_Name"]["value"] is None:
        _skip = (
            "billed to", "bill to", "invoice to", "ship to", "shipping",
            "invoice no", "invoice number", "invoice #",
            "subtotal", "total", "vat", "tax", "discount",
        )
        for region in regions:
            if region.get("label") != "paragraph":
                continue
            rn = _normalize(region.get("text", ""))
            if any(a in rn for a in _skip):
                continue
            name = _extract_name(region.get("lines", []))
            if name:
                _set_field(payload, "Issuer_Name", name, "top_paragraph_fallback", region.get("text", ""))
                break

    return payload


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
    for det in detections:
        x1, y1, x2, y2 = [int(round(v)) for v in det["xyxy"]]
        # Add small padding for OCR quality
        pad = 4
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(img.width, x2 + pad)
        y2 = min(img.height, y2 + pad)

        crop = img.crop((x1, y1, x2, y2))
        ocr_lines = _ocr_crop_tesseract(crop)

        region_text = "\n".join(ln.text for ln in ocr_lines if ln.text.strip())
        region_lines = [ln.text for ln in ocr_lines if ln.text.strip()]

        regions.append({
            **det,
            "text": region_text,
            "lines": region_lines,
            "line_count": len(region_lines),
        })

    extracted = _extract_fields_from_regions(regions)

    def fval(field: str) -> str:
        return extracted.get(field, {}).get("value") or ""

    total_text = fval("Total")
    raw_text = "\n\n".join(
        f"[{r['label']}]\n{r['text']}" for r in regions if r.get("text")
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
