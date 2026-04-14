"""
Invoice field extractor — YOLO detection + OCR pipeline.

Pipeline:
    1. Download file from MinIO
    2. Convert to PIL Image (handles PDF via PyMuPDF)
    3. Run YOLOv8 to detect field bounding boxes
    4. OCR each detected region with Tesseract
    5. Map YOLO class names to InvoiceExtraction model fields
    6. Post-process: parse dates, amounts, currency
"""

import io
import os
import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import TypedDict

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ML_DIR, "models")

# YOLO class index → label name (matches yolo_dataset/data.yaml)
YOLO_CLASSES = {
    0: "Adresse_Facturation",
    1: "Adresse_Livraison",
    2: "Date_Facturation",
    3: "Echéance",
    4: "Email_Client",
    5: "Nom_Client",
    6: "Numéro_Facture",
    7: "Pourcentage_Remise",
    8: "Pourcentage_TVA",
    9: "Produits",
    10: "Remise",
    11: "TVA",
    12: "Tel_Client",
    13: "Total_Hors_TVA",
    14: "Total_TTC",
}

# Lazy-loaded YOLO model singleton
_yolo_model = None


def _load_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        path = os.path.join(MODELS_DIR, "yolo_invoice.pt")
        _yolo_model = YOLO(path)
        logger.info("YOLO invoice model loaded from %s", path)
    return _yolo_model


# ── MinIO helper ─────────────────────────────────────────────────────────────

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


# ── OCR helpers ───────────────────────────────────────────────────────────────

def _ocr_crop(img: Image.Image, xyxy: list) -> str:
    """Crop the image to a bounding box and run Tesseract OCR on it."""
    pad = 4
    x1 = max(0, int(xyxy[0]) - pad)
    y1 = max(0, int(xyxy[1]) - pad)
    x2 = min(img.width,  int(xyxy[2]) + pad)
    y2 = min(img.height, int(xyxy[3]) + pad)
    crop = img.crop((x1, y1, x2, y2))
    # PSM 6 = single uniform block of text (better for field regions)
    return pytesseract.image_to_string(crop, config="--psm 6").strip()


# ── Post-processing ───────────────────────────────────────────────────────────

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
    "%d/%m/%y", "%d-%m-%y",
    "%B %d, %Y", "%b %d, %Y",
    "%d %B %Y", "%d %b %Y",
]


def _parse_date(text: str):
    text = re.sub(r"\s+", " ", text).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(text: str):
    cleaned = re.sub(r"[€$£\s]", "", text)
    # Handle comma-as-decimal (e.g. "1 450,00")
    if re.match(r"^\d[\d\s]*,\d{2}$", cleaned):
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _infer_currency(text: str) -> str:
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
    invoice_date: object   # date | None
    due_date: object       # date | None
    issuer_name: str
    recipient_name: str
    total_amount: object   # Decimal | None
    currency: str
    raw_text: str
    confidence_map: dict


def extract_invoice_fields(storage_key: str, content_type: str) -> ExtractionOutput:
    """
    Extract structured invoice fields from a document in MinIO.

    Returns an ExtractionOutput dict that maps directly onto the
    InvoiceExtraction model fields.
    """
    model = _load_yolo()

    file_bytes = _download_from_minio(storage_key)
    img = _to_image(file_bytes, content_type)

    detections = model(img, verbose=False)

    # Build {class_name: (ocr_text, confidence)} keeping best detection per class
    fields: dict[str, tuple[str, float]] = {}
    raw_lines = []

    for result in detections:
        for box in result.boxes:
            cls_idx = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = YOLO_CLASSES.get(cls_idx, f"class_{cls_idx}")
            text = _ocr_crop(img, box.xyxy[0].tolist())

            raw_lines.append(f"{class_name}: {text}")

            if class_name not in fields or conf > fields[class_name][1]:
                fields[class_name] = (text, conf)

    def text(cls: str) -> str:
        return fields.get(cls, ("", 0.0))[0]

    def conf(cls: str) -> float:
        return fields.get(cls, ("", 0.0))[1]

    # ── Map YOLO classes → InvoiceExtraction fields ───────────────────────────
    total_text = text("Total_TTC")

    return ExtractionOutput(
        invoice_number=text("Numéro_Facture"),
        invoice_date=_parse_date(text("Date_Facturation")),
        due_date=_parse_date(text("Echéance")),
        issuer_name="",  # No YOLO class for issuer in this dataset
        recipient_name=text("Nom_Client"),
        total_amount=_parse_amount(total_text),
        currency=_infer_currency(total_text),
        raw_text="\n".join(raw_lines),
        confidence_map={
            "invoice_number": conf("Numéro_Facture"),
            "invoice_date":   conf("Date_Facturation"),
            "due_date":       conf("Echéance"),
            "recipient_name": conf("Nom_Client"),
            "total_amount":   conf("Total_TTC"),
        },
    )
