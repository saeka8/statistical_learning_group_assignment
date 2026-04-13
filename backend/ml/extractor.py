"""
Invoice field extractor — regex/rules-based pipeline.

Retrieves a document from MinIO, runs OCR (if needed), and applies
cascading regex patterns to extract structured invoice fields.

Interface:
    from ml.extractor import extract_invoice_fields
    result = extract_invoice_fields(storage_key, content_type)
"""

import io
import os
import re
import logging
from typing import TypedDict
from decimal import Decimal, InvalidOperation
from datetime import date

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


# ── MinIO helper (shared with classifier) ────────────────────────
def _download_from_minio(storage_key: str) -> bytes:
    """Download a file from MinIO and return its bytes."""
    from apps.documents.storage import _s3_client
    from django.conf import settings

    client = _s3_client()
    response = client.get_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=storage_key
    )
    return response["Body"].read()


def _get_text_and_image(storage_key: str, content_type: str):
    """Download file from MinIO, extract OCR text and PIL Image."""
    file_bytes = _download_from_minio(storage_key)

    is_pdf = content_type == "application/pdf" or storage_key.lower().endswith(".pdf")

    if is_pdf:
        # Reuse classifier's PDF handling
        from ml.classifier import _ocr_from_pdf
        text, img = _ocr_from_pdf(file_bytes)
    else:
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)

    return text, img


# ── date patterns ────────────────────────────────────────────────
_DATE_PATTERNS = [
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b",
    r"\b(\d{4}-\d{2}-\d{2})\b",
]


# ── field extraction functions ───────────────────────────────────
def _extract_invoice_number(text: str) -> str:
    patterns = [
        r"(?:invoice\s*(?:no|number|#|num))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})",
        r"(?:inv\s*(?:no|#))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})",
        r"(?:doc(?:ument)?\s*(?:no|#|number))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})",
        r"(?:receipt\s*(?:no|#|number))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})",
        r"INVOICE\s*NO[.\s]*(\d{3,15})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = match.group(1).strip()
            if len(num) >= 3 and num.lower() not in ("the", "and", "for", "date", "erence"):
                return num
    return ""


def _extract_invoice_date(text: str) -> str:
    date_context = re.search(
        r"(?:^|\n)\s*(?:invoice\s*)?date[:\s]+(.{6,30})", text, re.IGNORECASE
    )
    if date_context:
        for pattern in _DATE_PATTERNS:
            match = re.search(pattern, date_context.group(1))
            if match:
                return match.group(1).strip()
    date_line = re.search(
        r"date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text, re.IGNORECASE
    )
    if date_line:
        return date_line.group(1).strip()
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def _extract_due_date(text: str) -> str:
    patterns = [
        r"(?:due\s*date|payment\s*due|pay\s*by|payable\s*by)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:due\s*date|payment\s*due|pay\s*by)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
        r"(?:due\s*date|payment\s*due)[:\s]*(.{6,25})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            for dp in _DATE_PATTERNS:
                dm = re.search(dp, result)
                if dm:
                    return dm.group(1)
            if len(result) > 3:
                return result
    return ""


def _parse_amount(s: str):
    s = re.sub(r"\s+", "", s.strip())
    if re.match(r"^\d+,\d{2}$", s):
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _extract_total(text: str) -> str:
    lines = text.split("\n")

    # Pass 1: Grand Total
    for line in reversed(lines):
        match = re.search(
            r"grand\s*total[:\s]*[\$\xA3\u20AC\xA5RM\s]*([\d,\s]+\.?\d*)",
            line, re.IGNORECASE,
        )
        if match:
            val = _parse_amount(match.group(1))
            if val and val > 0:
                return f"{val:.2f}"

    # Pass 2: Total Rounded / Total (incl GST)
    for line in reversed(lines):
        match = re.search(
            r"(?:total\s*rounded|total\s*\(?\s*incl|round\w*\s*total)[:\s]*[\$\xA3\u20AC\xA5RM\s]*([\d,\s]+\.\d{2})",
            line, re.IGNORECASE,
        )
        if match:
            val = _parse_amount(match.group(1))
            if val and val > 0:
                return f"{val:.2f}"

    # Pass 3: Total with amount (skip subtotal)
    for line in reversed(lines):
        if re.search(r"sub\s*total", line, re.IGNORECASE):
            continue
        match = re.search(
            r"\btotal(?:\s*\w*)?[:\s]*[\$\xA3\u20AC\xA5RM\s]*([\d,\s]+\.\d{2})",
            line, re.IGNORECASE,
        )
        if match:
            val = _parse_amount(match.group(1))
            if val and val > 0:
                return f"{val:.2f}"

    # Pass 4: Comma-decimal format
    for line in reversed(lines):
        if re.search(r"sub\s*total", line, re.IGNORECASE):
            continue
        match = re.search(
            r"\btotal(?:\s*\w*)?[:\s]*[\$\xA3\u20AC\xA5RM\s]*([\d,\s]+,\d{2})\b",
            line, re.IGNORECASE,
        )
        if match:
            val = _parse_amount(match.group(1))
            if val and val > 0:
                return f"{val:.2f}"

    # Pass 5: Total with any number
    for line in reversed(lines):
        if re.search(r"sub\s*total", line, re.IGNORECASE):
            continue
        match = re.search(r"\btotal\b.*?([\d,]+\.?\d+)", line, re.IGNORECASE)
        if match:
            val = _parse_amount(match.group(1))
            if val and val > 0:
                return f"{val:.2f}"

    # Pass 6: Last dollar/currency amount
    amounts = re.findall(r"[\$\xA3\u20AC]\s*([\d,]+\.\d{2})", text)
    if amounts:
        val = _parse_amount(amounts[-1])
        if val and val > 0:
            return f"{val:.2f}"

    return ""


def _extract_issuer(text: str) -> str:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    skip_patterns = [r"^tan\s", r"^page\s", r"^\d+$", r"^[\s\W]+$"]
    clean_lines = []
    for line in lines[:15]:
        if not any(re.match(sp, line, re.IGNORECASE) for sp in skip_patterns):
            clean_lines.append(line)

    company_suffixes = (
        r"(?:Inc|LLC|Ltd|Corp|Co\b|Company|Enterprise|SDN\s*BHD|Sdn\s*Bhd"
        r"|PLC|GmbH|AG\b|S\.?A\b|SRL|BV|NV|Restaurants?|Trading|Motor|Machinery)"
    )
    for line in clean_lines[:10]:
        if re.search(company_suffixes, line, re.IGNORECASE) and len(line) > 3:
            return line

    for line in clean_lines[:5]:
        if (
            len(line) > 5
            and not re.match(r"^[\d\s/\-\.,:]+$", line)
            and not re.search(r"invoice|receipt|date|total|page", line, re.IGNORECASE)
        ):
            return line
    return ""


def _extract_recipient(text: str) -> str:
    patterns = [
        r"(?:bill\s*to|sold\s*to|ship\s*to|deliver\s*to)[:\s]*\n?\s*(.+?)(?:\n|$)",
        r"(?:attn|attention)[:\s]*\n?\s*(.+?)(?:\n|$)",
        r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})",
        r"(?:customer|client)[:\s]*\n?\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = re.sub(r"\s+", " ", match.group(1).strip())
            if 2 < len(name) < 80:
                return name
    to_match = re.search(r"^(?:to)[:\s]+(.+?)$", text, re.IGNORECASE | re.MULTILINE)
    if to_match:
        name = to_match.group(1).strip()
        if 2 < len(name) < 80:
            return name
    return ""


def _detect_currency(text: str) -> str:
    """Detect currency from the OCR text using symbol and code patterns."""
    # Check for explicit currency symbols near amounts
    if re.search(r"\$\s*[\d,]+", text):
        return "USD"
    if re.search(r"\u20AC\s*[\d,]+|[\d,]+\s*\u20AC", text):
        return "EUR"
    if re.search(r"\xA3\s*[\d,]+", text):
        return "GBP"
    if re.search(r"\xA5\s*[\d,]+", text):
        return "JPY"
    if re.search(r"RM\s*[\d,]+", text):
        return "MYR"

    # Check for ISO currency codes
    currency_codes = ["USD", "EUR", "GBP", "JPY", "CNY", "MYR", "SGD", "AUD", "CAD", "CHF"]
    for code in currency_codes:
        if re.search(rf"\b{code}\b", text, re.IGNORECASE):
            return code

    return ""


def _compute_confidence_map(fields: dict) -> dict:
    """
    Compute heuristic confidence scores for each extracted field.
    Higher confidence when the extraction used a strong, specific pattern.
    """
    confidence = {}

    # Invoice number: high if matched a specific pattern, 0 if empty
    val = fields.get("invoice_number", "")
    if val:
        confidence["invoice_number"] = 0.85 if re.match(r"[A-Z]{2,}", val) else 0.70
    else:
        confidence["invoice_number"] = 0.0

    # Invoice date: high if it looks like a complete date
    val = fields.get("invoice_date", "")
    if val:
        if re.match(r"\d{4}-\d{2}-\d{2}", val):
            confidence["invoice_date"] = 0.90
        elif re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", val):
            confidence["invoice_date"] = 0.80
        else:
            confidence["invoice_date"] = 0.60
    else:
        confidence["invoice_date"] = 0.0

    # Due date: lower confidence since fewer invoices have explicit due dates
    val = fields.get("due_date", "")
    if val:
        confidence["due_date"] = 0.70 if re.search(r"\d", val) else 0.40
    else:
        confidence["due_date"] = 0.0

    # Issuer name: high if contains company suffix
    val = fields.get("issuer_name", "")
    if val:
        has_suffix = bool(re.search(r"(?:Inc|LLC|Ltd|Corp|Co\b|GmbH|AG\b)", val, re.IGNORECASE))
        confidence["issuer_name"] = 0.85 if has_suffix else 0.55
    else:
        confidence["issuer_name"] = 0.0

    # Recipient name: moderate confidence
    val = fields.get("recipient_name", "")
    if val:
        confidence["recipient_name"] = 0.65
    else:
        confidence["recipient_name"] = 0.0

    # Total amount: high if found with decimal places
    val = fields.get("total_amount", "")
    if val:
        confidence["total_amount"] = 0.80
    else:
        confidence["total_amount"] = 0.0

    return confidence


def _parse_date_string(date_str: str):
    """Try to parse a date string into a Python date object. Returns None on failure."""
    if not date_str:
        return None

    import re as _re
    from datetime import datetime

    # ISO format: 2025-01-15
    m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Common formats: DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY
    m = _re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", date_str)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        # Try DD/MM/YYYY first, fall back to MM/DD/YYYY
        for day, month in [(d, mo), (mo, d)]:
            try:
                return date(y, month, day)
            except ValueError:
                continue

    # Month name formats: Jan 15, 2025 / 15 Jan 2025
    try:
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
    except Exception:
        pass

    return None


# ── public interface ─────────────────────────────────────────────
class ExtractionOutput(TypedDict):
    invoice_number: str
    invoice_date: "date | None"
    due_date: "date | None"
    issuer_name: str
    recipient_name: str
    total_amount: "Decimal | None"
    currency: str
    raw_text: str
    confidence_map: dict


def extract_invoice_fields(storage_key: str, content_type: str) -> ExtractionOutput:
    """
    Extract structured fields from an invoice document stored in MinIO.

    1. Downloads the file from MinIO.
    2. Runs OCR to extract text.
    3. Applies cascading regex patterns for each field.
    4. Detects currency from text.
    5. Computes heuristic per-field confidence scores.
    6. Returns all fields + raw_text + confidence_map.
    """
    # Get OCR text
    ocr_text, _ = _get_text_and_image(storage_key, content_type)
    logger.info("Extraction: OCR extracted %d characters from %s", len(ocr_text), storage_key)

    # Extract all fields
    raw_fields = {
        "invoice_number": _extract_invoice_number(ocr_text),
        "invoice_date": _extract_invoice_date(ocr_text),
        "due_date": _extract_due_date(ocr_text),
        "issuer_name": _extract_issuer(ocr_text),
        "recipient_name": _extract_recipient(ocr_text),
        "total_amount": _extract_total(ocr_text),
    }

    # Detect currency
    currency = _detect_currency(ocr_text)

    # Compute confidence scores
    confidence_map = _compute_confidence_map(raw_fields)

    # Parse total_amount to Decimal
    total_decimal = None
    if raw_fields["total_amount"]:
        try:
            total_decimal = Decimal(raw_fields["total_amount"])
        except (InvalidOperation, ValueError):
            total_decimal = None

    # Parse dates to date objects
    invoice_date = _parse_date_string(raw_fields["invoice_date"])
    due_date = _parse_date_string(raw_fields["due_date"])

    logger.info(
        "Extraction complete: %d/%d fields found",
        sum(1 for v in raw_fields.values() if v),
        len(raw_fields),
    )

    return ExtractionOutput(
        invoice_number=raw_fields["invoice_number"],
        invoice_date=invoice_date,
        due_date=due_date,
        issuer_name=raw_fields["issuer_name"],
        recipient_name=raw_fields["recipient_name"],
        total_amount=total_decimal,
        currency=currency,
        raw_text=ocr_text,
        confidence_map=confidence_map,
    )
