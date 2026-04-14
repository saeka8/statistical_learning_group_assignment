from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Feature_Extraction_Invoice.OCR_method.extract_invoice_ocr import (  # noqa: E402
    DATE_RE,
    EMAIL_RE,
    MONEY_RE,
    PERCENT_RE,
    PHONE_RE,
    normalize_text,
    parse_amount,
)


FIELD_NAMES = [
    "Invoice_Number",
    "Invoice_Date",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract invoice fields from paragraph/table grouped OCR output."
    )
    parser.add_argument("--region-json", type=Path, required=True, help="Path to region_ocr.json.")
    parser.add_argument("--pretty", action="store_true")
    return parser


def null_payload() -> dict[str, dict]:
    return {
        field: {"value": None, "method": "not_found", "evidence": None}
        for field in FIELD_NAMES
    }


def set_field(payload: dict[str, dict], field: str, value: str | None, method: str, evidence: str | None) -> None:
    if not value:
        return
    current = payload[field]
    if current["value"] is None:
        payload[field] = {"value": value, "method": method, "evidence": evidence}


def cleaned_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    if match:
        return match.group(0)

    compact = re.sub(r"\s+", "", text)
    compact = compact.replace(".con", ".com")
    compact = compact.replace("sitecom", "site.com")
    compact = compact.replace("gmailcom", "gmail.com")
    match = EMAIL_RE.search(compact)
    return match.group(0) if match else None


def cleaned_phone(text: str) -> str | None:
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 8:
            return candidate
    return None


def first_date(text: str) -> str | None:
    match = DATE_RE.search(text)
    return match.group(0) if match else None


def amounts_in_text(text: str) -> list[str]:
    return [m.group(0).strip() for m in MONEY_RE.finditer(text)]


def percent_in_text(text: str) -> str | None:
    match = PERCENT_RE.search(text)
    return match.group(0).strip() if match else None


def invoice_number_from_text(text: str) -> str | None:
    normalized = normalize_text(text)
    patterns = [
        r"(?:invoice\s*(?:no|number|#)?|facture\s*(?:n|no|numero)?)\s*[:#-]?\s*([A-Z0-9./_-]{3,})",
        r"\bno\.?\s*([A-Z0-9./_-]{3,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if sum(ch.isdigit() for ch in value) >= 3:
                return value

    for token in re.findall(r"\b[A-Z0-9./_-]{4,}\b", text, re.IGNORECASE):
        if sum(ch.isdigit() for ch in token) >= 4:
            return token
    return None


def extract_address_lines(lines: list[str]) -> str | None:
    kept: list[str] = []
    for line in lines:
        normalized = normalize_text(line)
        if not line.strip():
            continue
        if any(anchor in normalized for anchor in ("billed to", "bill to", "shipping", "ship to", "delivered to")):
            continue
        if cleaned_email(line) or cleaned_phone(line):
            continue
        kept.append(line.strip())
    if not kept:
        return None
    if len(kept) >= 2:
        return ", ".join(kept[1:]) if len(kept) > 1 else kept[0]
    return kept[0]


def extract_name(lines: list[str]) -> str | None:
    for line in lines:
        normalized = normalize_text(line)
        if any(anchor in normalized for anchor in ("billed to", "bill to", "shipping", "ship to", "delivered to")):
            continue
        if cleaned_email(line) or cleaned_phone(line):
            continue
        if any(char.isalpha() for char in line):
            return line.strip()
    return None


def extract_products(lines: list[str]) -> str | None:
    products: list[str] = []
    for line in lines:
        normalized = normalize_text(line)
        if not line.strip():
            continue
        if any(anchor in normalized for anchor in ("description", "designation", "item", "items", "products")):
            continue
        if any(anchor in normalized for anchor in ("subtotal", "discount", "tax", "vat", "total")):
            continue
        if len(re.findall(r"[A-Za-z]", line)) < 4:
            continue
        products.append(line.strip())
    return " | ".join(products) if products else None


def region_sort_key(region: dict) -> tuple[float, float]:
    x1, y1, _, _ = region["xyxy"]
    return (y1, x1)


def extract_fields_from_region_payload(data: dict) -> dict[str, dict]:
    regions = sorted(data.get("regions", []), key=region_sort_key)
    payload = null_payload()

    all_lines: list[tuple[str, str]] = []

    for region in regions:
        label = region.get("label", "")
        text = region.get("text", "") or ""
        lines = [line.strip() for line in region.get("lines", []) if line.strip()]
        normalized = normalize_text(text)

        for line in lines:
            all_lines.append((line, label))

        if label == "table":
            products = extract_products(lines)
            set_field(payload, "Products", products, "table_region", text)

        if any(anchor in normalized for anchor in ("description", "designation", "item", "items", "products")):
            products = extract_products(lines)
            set_field(payload, "Products", products, "paragraph_region_products", text)

        if any(anchor in normalized for anchor in ("billed to", "bill to", "invoice to", "customer")):
            set_field(payload, "Client_Name", extract_name(lines), "billing_region", text)
            set_field(payload, "Billing_Address", extract_address_lines(lines), "billing_region", text)
            for line in lines:
                set_field(payload, "Client_Email", cleaned_email(line), "billing_region", text)
                set_field(payload, "Client_Phone", cleaned_phone(line), "billing_region", text)

        if any(anchor in normalized for anchor in ("ship to", "shipping", "delivered to", "delivery address")):
            set_field(payload, "Shipping_Address", extract_address_lines(lines), "shipping_region", text)

        if any(anchor in normalized for anchor in ("invoice no", "invoice number", "invoice #", "date:", "due:", "due date", "terms", "amount due")):
            for line in lines:
                line_normalized = normalize_text(line)
                if "invoice" in line_normalized:
                    set_field(payload, "Invoice_Number", invoice_number_from_text(line), "metadata_region", text)
                if "date" in line_normalized and "due" not in line_normalized:
                    set_field(payload, "Invoice_Date", first_date(line), "metadata_region", text)
                if "due" in line_normalized:
                    set_field(payload, "Due_Date", first_date(line), "metadata_region", text)
                set_field(payload, "Client_Email", cleaned_email(line), "metadata_region", text)
                set_field(payload, "Client_Phone", cleaned_phone(line), "metadata_region", text)

        if any(anchor in normalized for anchor in ("subtotal", "tax", "vat", "discount", "total")):
            for line in lines:
                line_normalized = normalize_text(line)
                amounts = amounts_in_text(line)
                if "subtotal" in line_normalized and amounts:
                    set_field(payload, "Subtotal", amounts[-1], "totals_region", text)
                if ("vat" in line_normalized or "tax" in line_normalized) and amounts:
                    set_field(payload, "VAT", amounts[-1], "totals_region", text)
                    set_field(payload, "VAT_Rate", percent_in_text(line), "totals_region", text)
                if "discount" in line_normalized and amounts:
                    set_field(payload, "Discount", amounts[-1], "totals_region", text)
                    set_field(payload, "Discount_Rate", percent_in_text(line), "totals_region", text)
                if re.search(r"\btotal\b", line_normalized) and amounts:
                    set_field(payload, "Total", amounts[-1], "totals_region", text)

    for line, _label in all_lines:
        set_field(payload, "Client_Email", cleaned_email(line), "global_region_scan", line)
        if "Client_Email" in payload and payload["Client_Email"]["value"]:
            break

    for line, _label in all_lines:
        set_field(payload, "Client_Phone", cleaned_phone(line), "global_region_scan", line)
        if payload["Client_Phone"]["value"]:
            break

    for line, _label in all_lines:
        set_field(payload, "Invoice_Number", invoice_number_from_text(line), "global_region_scan", line)
        if payload["Invoice_Number"]["value"]:
            break

    for line, _label in all_lines:
        normalized = normalize_text(line)
        if "date" in normalized and "due" not in normalized:
            set_field(payload, "Invoice_Date", first_date(line), "global_region_scan", line)
        if "due" in normalized:
            set_field(payload, "Due_Date", first_date(line), "global_region_scan", line)

    return payload


def main() -> int:
    args = build_parser().parse_args()
    if not args.region_json.exists():
        raise SystemExit(f"Region JSON not found: {args.region_json}")

    data = json.loads(args.region_json.read_text(encoding="utf-8"))
    payload = extract_fields_from_region_payload(data)

    output = {
        "region_json": str(args.region_json.resolve()),
        "extracted_fields": payload,
    }

    if args.pretty:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
