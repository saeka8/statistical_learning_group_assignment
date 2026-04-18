"""
Invoice field extractor — preprocessing + Tesseract OCR + LayoutLM pipeline.

Pipeline:
    1. Download file from MinIO
    2. Convert to PIL Image (handles PDF via PyMuPDF)
    3. Preprocess image (LAB-L, CLAHE, background normalisation)
    4. Full-page Tesseract OCR → tokens with bounding boxes
    5. Cluster tokens into spatial paragraph regions (by y-gap)
    6. LayoutLM document-QA on the original image (primary extraction)
    7. Anchor-based regex extraction on clustered regions (fallback / gap-fill)
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

from PIL import Image

logger = logging.getLogger(__name__)

ML_DIR = os.path.dirname(os.path.abspath(__file__))

# Make the repo-root `ai/` package importable inside Docker (/app/ai → /app is APP_ROOT)
import sys as _sys
_APP_ROOT = os.path.dirname(ML_DIR)
if _APP_ROOT not in _sys.path:
    _sys.path.insert(0, _APP_ROOT)

from ai.extraction.OCR_method.shared_ocr import (
    ocr_pil_tesseract_tokens as _ocr_pil_tesseract_tokens,
    group_lines as _group_lines,
)
from ai.extraction.preprocessing_invoice.pipeline import preprocess_invoice_image as _preprocess_invoice_image
from ai.extraction.layoutlm.extractor import extract_with_layoutlm as _extract_with_layoutlm


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


# ── Spatial clustering ────────────────────────────────────────────────────────

def _cluster_tokens_into_regions(tokens: list) -> list[dict]:
    """Group OCR tokens into paragraph-like regions by vertical gap.

    Tokens are sorted top-to-bottom.  A new region starts whenever the gap
    between the bottom of the previous token and the top of the next exceeds
    2× the median token height (minimum 30 px).  Each cluster is returned as
    a region dict compatible with ``_extract_fields_from_regions``.
    """
    if not tokens:
        return []

    tokens_sorted = sorted(tokens, key=lambda t: (t.ymin, t.xmin))
    heights = sorted(t.height for t in tokens_sorted)
    median_h = heights[len(heights) // 2] if heights else 20.0
    gap_threshold = max(median_h * 2.0, 30.0)

    clusters: list[list] = []
    current: list = []
    prev_ymax: float | None = None

    for token in tokens_sorted:
        if prev_ymax is not None and token.ymin - prev_ymax > gap_threshold:
            if current:
                clusters.append(current)
            current = []
        current.append(token)
        prev_ymax = token.ymax
    if current:
        clusters.append(current)

    regions = []
    for idx, cluster in enumerate(clusters):
        ocr_lines = _group_lines(cluster)
        region_text = "\n".join(ln.text for ln in ocr_lines if ln.text.strip())
        region_lines = [ln.text for ln in ocr_lines if ln.text.strip()]
        if not region_lines:
            continue
        regions.append({
            "label": "paragraph",
            "confidence": 0.0,
            "xyxy": [
                min(t.xmin for t in cluster),
                min(t.ymin for t in cluster),
                max(t.xmax for t in cluster),
                max(t.ymax for t in cluster),
            ],
            "region_index": idx,
            "text": region_text,
            "lines": region_lines,
            "line_count": len(region_lines),
        })

    return regions


# ── Field extraction ──────────────────────────────────────────────────────────

# Regex patterns
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
    "Invoice_Number",
    "Invoice_Date",
    "Issuer_Name",
    "Client_Name",
    "Client_Email",
    "Client_Phone",
    "Billing_Address",
    "Shipping_Address",
    "Products",
    "Subtotal",
    "VAT",
    "Total",
    "Discount",
    "VAT_Rate",
    "Discount_Rate",
    "Due_Date",
]

_ISSUER_ANCHORS = (
    "from:",
    "issued by",
    "emis par",
    "emetteur",
    "vendeur",
    "fournisseur",
    "societe",
    "supplier",
    "seller",
)

_CLIENT_ANCHORS = (
    "billed to",
    "bill to",
    "invoice to",
    "customer",
    "nombre:",
    "nombre ",
    "cliente",
    # NOTE: "payable to" intentionally excluded — appears in payment instructions
    # ("please make checks payable to: <issuer>") which is the issuer, not the client
)

_ADDRESS_ANCHORS = (
    "ship to",
    "shipping",
    "delivered to",
    "delivery address",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9%@./,_#:$€£+\- ]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _null_payload() -> dict:
    return {field: {"value": None, "method": "not_found", "evidence": None} for field in _FIELD_NAMES}


def _set_field(payload: dict, field: str, value, method: str, evidence) -> None:
    if not value:
        return
    if payload[field]["value"] is None:
        payload[field] = {"value": value, "method": method, "evidence": evidence}


def _first_date(text: str):
    match = _DATE_RE.search(text)
    return match.group(0) if match else None


def _amounts_in_text(text: str) -> list[str]:
    return [match.group(0).strip() for match in _MONEY_RE.finditer(text)]


def _percent_in_text(text: str):
    match = _PERCENT_RE.search(text)
    return match.group(0).strip() if match else None


def _cleaned_email(text: str):
    match = _EMAIL_RE.search(text)
    if match:
        value = match.group(0)
        if value.startswith("nfo@"):
            value = "i" + value
        return value.replace(".con", ".com")

    compact = re.sub(r"\s+", "", text)
    compact = compact.replace(".con", ".com")
    compact = compact.replace("sitecom", "site.com")
    compact = compact.replace("gmailcom", "gmail.com")
    if compact.startswith("nfo@"):
        compact = "i" + compact
    match = _EMAIL_RE.search(compact)
    return match.group(0) if match else None


def _cleaned_phone(text: str):
    normalized = _normalize(text)
    if "nif" in normalized:
        return None
    for match in _PHONE_RE.finditer(text):
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 8:
            return candidate
    return None


def _looks_like_phone_token(text: str) -> bool:
    compact = text.strip()
    if not compact:
        return False
    if compact.startswith("+"):
        return True
    digits = re.sub(r"\D", "", compact)
    if len(digits) < 8:
        return False
    return bool(re.fullmatch(r"[\d().+\-\s]+", compact))


_STREET_SUFFIXES = re.compile(
    r"\b(lane|ln|street|st|avenue|ave|road|rd|drive|dr|blvd|boulevard|court|ct|place|pl|way|circle|cir)\b",
    re.IGNORECASE,
)

# Common postal code patterns — should not be confused with invoice numbers
_POSTAL_CODE_RE = re.compile(
    r"^(?:"
    r"[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}"   # UK: W91AE, SW1A 2AA
    r"|\d{5}(?:-\d{4})?"                         # US: 12345 or 12345-6789
    r"|[A-Z]\d[A-Z]\s*\d[A-Z]\d"                # Canada: A1B 2C3
    r"|\d{4,5}"                                   # generic 4-5 digit zip
    r")$",
    re.IGNORECASE,
)


def _is_postal_code(token: str) -> bool:
    return bool(_POSTAL_CODE_RE.match(token.strip()))


def _invoice_number_from_text(text: str):
    normalized = _normalize(text)
    if "nif" in normalized:
        return None
    # Skip lines that look like postal addresses
    if _STREET_SUFFIXES.search(text):
        return None
    patterns = [
        r"(?:invoice\s*(?:no|number|#)?|facture\s*(?:n|no|numero)?|factura\s*(?:n|no|numero|n°)?)\s*[:#-]?\s*([A-Z0-9./_-]{3,})",
        r"\bno\.?\s*([A-Z0-9./_-]{3,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if sum(char.isdigit() for char in value) >= 3 and not _looks_like_phone_token(value) and not _is_postal_code(value):
                return value

    # Prefer alphanumeric tokens (mix of letters + digits) over pure numeric ones
    candidates = re.findall(r"\b[A-Z0-9./_-]{4,}\b", text, re.IGNORECASE)
    alphanumeric = [
        t for t in candidates
        if re.search(r"[A-Za-z]", t) and re.search(r"\d", t)
        and not _looks_like_phone_token(t) and not _is_postal_code(t)
    ]
    if alphanumeric:
        return alphanumeric[0]
    for token in candidates:
        if sum(char.isdigit() for char in token) >= 4 and not _looks_like_phone_token(token) and not _is_postal_code(token):
            return token
    return None


def _extract_address_lines(lines: list[str]) -> str | None:
    kept: list[str] = []
    for line in lines:
        normalized = _normalize(line)
        if not line.strip():
            continue
        if any(anchor in normalized for anchor in ("billed to", "bill to", "shipping", "ship to", "delivered to", "payable to", "contact info", "payment terms")):
            continue
        if normalized.startswith("nif"):
            continue
        if _cleaned_email(line) or _cleaned_phone(line):
            continue
        if "www." in normalized or "http" in normalized:
            continue
        line = re.sub(r"^(Dirección|Direccion|Ciudad)\s*:\s*", "", line).strip()
        kept.append(line)
    if not kept:
        return None
    if len(kept) >= 2 and not re.search(r"\d", kept[0]):
        kept = kept[1:]
    if not kept:
        return None
    if len(kept) >= 2:
        return ", ".join(kept)
    return kept[0]


def _is_header_line(line: str) -> bool:
    """Return True if the line looks like an all-caps label/header, not a name."""
    stripped = line.strip()
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    # More than 80 % of alphabetic chars are uppercase AND line has 2+ words → header
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio > 0.8 and len(stripped.split()) >= 2


def _extract_name(lines: list[str]) -> str | None:
    for line in lines:
        normalized = _normalize(line)
        if any(anchor in normalized for anchor in ("billed to", "bill to", "shipping", "ship to", "delivered to", "payable to", "contact info", "payment terms")):
            continue
        if _cleaned_email(line) or _cleaned_phone(line):
            continue
        if any(anchor in normalized for anchor in ("invoice", "date", "description", "subtotal", "discount", "tax", "vat", "total", "terms", "conditions", "payment", "amount", "quantity", "purchase", "price", "due")):
            continue
        if _is_header_line(line):
            continue
        line = re.sub(r"^(Nombre)\s*:\s*", "", line).strip()
        if any(char.isalpha() for char in line):
            return line
    return None


def _strip_trailing_price(text: str) -> str:
    stripped = re.sub(r"\s+(?:[$€£]?\d[\d,]*(?:\.\d{2})?)\s*$", "", text).strip()
    return stripped or text.strip()


def _extract_products(lines: list[str]) -> str | None:
    products: list[str] = []
    for line in lines:
        normalized = _normalize(line)
        if not line.strip():
            continue
        if any(anchor in normalized for anchor in ("description", "designation", "item", "items", "products")):
            continue
        if any(anchor in normalized for anchor in ("subtotal", "discount", "tax", "vat", "total")):
            continue
        if re.fullmatch(r"[\d\s$€£.,]+", line.strip()):
            continue
        if len(re.findall(r"[A-Za-z]", line)) < 4:
            continue
        products.append(_strip_trailing_price(line))
    return " | ".join(products) if products else None


def _extract_totals(payload: dict, lines: list[str], evidence: str, method: str) -> None:
    for line in lines:
        line_normalized = _normalize(line)
        amounts = _amounts_in_text(line)
        if ("subtotal" in line_normalized or line_normalized.startswith("base")) and amounts:
            _set_field(payload, "Subtotal", amounts[-1], method, evidence)
        if ("vat" in line_normalized or "tax" in line_normalized or "iva" in line_normalized) and amounts:
            _set_field(payload, "VAT", amounts[-1], method, evidence)
            _set_field(payload, "VAT_Rate", _percent_in_text(line), method, evidence)
        if "discount" in line_normalized and amounts:
            _set_field(payload, "Discount", amounts[-1], method, evidence)
            _set_field(payload, "Discount_Rate", _percent_in_text(line), method, evidence)
        if re.search(r"\btotal\b", line_normalized) and amounts:
            _set_field(payload, "Total", amounts[-1], method, evidence)


def _metadata_date_from_lines(lines: list[str], anchor: str) -> str | None:
    for index, line in enumerate(lines):
        normalized = _normalize(line)
        if anchor not in normalized:
            continue

        candidates = [line]
        if index > 0:
            candidates.append(f"{line} {lines[index - 1]}")
            candidates.append(f"{lines[index - 1]} {line}")
        if index + 1 < len(lines):
            candidates.append(f"{line} {lines[index + 1]}")
            candidates.append(f"{lines[index + 1]} {line}")

        for candidate in candidates:
            value = _first_date(candidate)
            if value:
                return value
    return None


def _metadata_value_by_anchor(lines: list[str], anchors: tuple[str, ...]) -> str | None:
    for index, line in enumerate(lines):
        normalized = _normalize(line)
        if not any(anchor in normalized for anchor in anchors):
            continue
        if "nif" in normalized:
            continue
        # The label and value are often on separate lines, sometimes several lines apart
        # (e.g. multi-column headers: "Invoice number | Amount Due | Date" then values below).
        # Scan ahead up to 4 lines, stopping early if we find a non-label, non-empty line.
        candidates = [line] + lines[index + 1: index + 5]
        for candidate in candidates:
            value = _invoice_number_from_text(candidate)
            if value:
                return value
    return None


def _best_contact_block(regions: list[dict]) -> dict | None:
    best_region = None
    best_score = -1

    for region in regions:
        lines = [line.strip() for line in region.get("lines", []) if line.strip()]
        if not lines:
            continue

        first_line = lines[0]
        first_normalized = _normalize(first_line)
        if _cleaned_email(first_line) or _cleaned_phone(first_line):
            continue
        if any(anchor in first_normalized for anchor in ("invoice", "factura", "description", "payment due", "date issued", "fecha")):
            continue

        email_count = sum(1 for line in lines if _cleaned_email(line))
        phone_count = sum(1 for line in lines if _cleaned_phone(line))
        website_count = sum(1 for line in lines if "www." in _normalize(line) or "http" in _normalize(line))
        address_count = sum(
            1 for line in lines
            if any(token in _normalize(line) for token in (" rd", " road", " st", " street", " ave", " avenue", " tampa", " fl"))
        )

        score = email_count + phone_count + website_count + address_count
        if len(re.findall(r"[A-Za-z]", first_line)) >= 8:
            score += 2
        if len(lines) >= 3:
            score += 1

        if score > best_score:
            best_score = score
            best_region = region

    return best_region if best_score >= 3 else None


def _extract_fields_from_regions(regions: list) -> dict:
    regions = sorted(regions, key=lambda region: (region["xyxy"][1], region["xyxy"][0]))
    payload = _null_payload()
    all_lines: list[tuple[str, str]] = []

    for region in regions:
        label = region.get("label", "paragraph")
        text = region.get("text", "") or ""
        lines = [line.strip() for line in region.get("lines", []) if line.strip()]
        normalized = _normalize(text)

        for line in lines:
            all_lines.append((line, label))

        if any(anchor in normalized for anchor in ("description", "designation", "item", "items", "products")):
            _set_field(payload, "Products", _extract_products(lines), "region_products", text)

        if any(anchor in normalized for anchor in _ISSUER_ANCHORS):
            _set_field(payload, "Issuer_Name", _extract_name(lines), "issuer_region", text)

        if any(anchor in normalized for anchor in _CLIENT_ANCHORS):
            _set_field(payload, "Client_Name", _extract_name(lines), "billing_region", text)
            _set_field(payload, "Billing_Address", _extract_address_lines(lines), "billing_region", text)
            for line in lines:
                _set_field(payload, "Client_Email", _cleaned_email(line), "billing_region", text)
                _set_field(payload, "Client_Phone", _cleaned_phone(line), "billing_region", text)

        if any(anchor in normalized for anchor in _ADDRESS_ANCHORS):
            _set_field(payload, "Shipping_Address", _extract_address_lines(lines), "shipping_region", text)

        if _metadata_value_by_anchor(lines, ("invoice", "factura")) or any(anchor in normalized for anchor in ("invoice", "factura", "invoice no", "nvoice no", "invoice number", "invoice #", "date issued", "fecha", "due date", "payment due", "terms", "amount due")):
            _set_field(payload, "Invoice_Number", _metadata_value_by_anchor(lines, ("invoice", "factura")), "metadata_region", text)
            _set_field(payload, "Invoice_Date", _metadata_date_from_lines(lines, "date") or _metadata_date_from_lines(lines, "fecha"), "metadata_region", text)
            for line in lines:
                line_normalized = _normalize(line)
                if "invoice" in line_normalized or "factura" in line_normalized:
                    _set_field(payload, "Invoice_Number", _invoice_number_from_text(line), "metadata_region", text)
                if ("date" in line_normalized or "fecha" in line_normalized) and "due" not in line_normalized:
                    _set_field(payload, "Invoice_Date", _metadata_date_from_lines(lines, "date") or _metadata_date_from_lines(lines, "fecha"), "metadata_region", text)
                if "due" in line_normalized:
                    _set_field(payload, "Due_Date", _metadata_date_from_lines(lines, "due"), "metadata_region", text)
                _set_field(payload, "Client_Email", _cleaned_email(line), "metadata_region", text)
                _set_field(payload, "Client_Phone", _cleaned_phone(line), "metadata_region", text)

        if any(anchor in normalized for anchor in ("subtotal", "tax", "vat", "discount", "total")):
            _extract_totals(payload, lines, text, "totals_region")

    contact_block = _best_contact_block(regions)
    if contact_block is not None:
        contact_lines = [line.strip() for line in contact_block.get("lines", []) if line.strip()]
        contact_text = contact_block.get("text", "") or ""
        _set_field(payload, "Client_Name", _extract_name(contact_lines), "contact_block_fallback", contact_text)
        _set_field(payload, "Billing_Address", _extract_address_lines(contact_lines), "contact_block_fallback", contact_text)
        for line in contact_lines:
            _set_field(payload, "Client_Email", _cleaned_email(line), "contact_block_fallback", contact_text)
            _set_field(payload, "Client_Phone", _cleaned_phone(line), "contact_block_fallback", contact_text)

    for line, _label in all_lines:
        _set_field(payload, "Client_Email", _cleaned_email(line), "global_scan", line)
        if payload["Client_Email"]["value"]:
            break

    for line, _label in all_lines:
        _set_field(payload, "Client_Phone", _cleaned_phone(line), "global_scan", line)
        if payload["Client_Phone"]["value"]:
            break

    for line, _label in all_lines:
        _set_field(payload, "Invoice_Number", _invoice_number_from_text(line), "global_scan", line)
        if payload["Invoice_Number"]["value"]:
            break

    for line, _label in all_lines:
        normalized = _normalize(line)
        if "date" in normalized and "due" not in normalized:
            _set_field(payload, "Invoice_Date", _first_date(line), "global_scan", line)
        if "due" in normalized:
            _set_field(payload, "Due_Date", _first_date(line), "global_scan", line)

    if payload["Issuer_Name"]["value"] is None:
        skip_anchors = (
            "invoice", "factura", "date", "fecha",
            "billed to", "bill to", "payable to", "contact info", "payment terms",
            "invoice to", "customer", "ship to", "shipping",
            "invoice no", "invoice number", "invoice #",
            "subtotal", "total", "vat", "tax", "discount",
        )
        contact_index = contact_block.get("region_index") if contact_block is not None else None
        for region in regions:
            if region.get("region_index") == contact_index:
                continue
            region_text = region.get("text", "") or ""
            region_normalized = _normalize(region_text)
            if any(anchor in region_normalized for anchor in skip_anchors):
                continue
            x1, y1, _, _ = region["xyxy"]
            if x1 > 2000 or y1 > 1600:
                continue
            if region_normalized.startswith("factura") or region_normalized.startswith("fecha"):
                continue
            name = _extract_name([line.strip() for line in region.get("lines", []) if line.strip()])
            if name is None or len(name) < 2:
                continue
            _set_field(payload, "Issuer_Name", name, "top_region_fallback", region_text)
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

    Pipeline: preprocess → full-page Tesseract OCR (for raw_text) → LayoutLM.
    LayoutLM is the sole extraction method; it uses the original image with its
    own internal OCR to answer one question per field.
    """
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
