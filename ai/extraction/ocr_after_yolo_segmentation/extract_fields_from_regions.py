from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.extraction.purely_ocr.extract_invoice_ocr import (  # noqa: E402
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

ISSUER_ANCHORS = (
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

CLIENT_ANCHORS = (
    "billed to",
    "bill to",
    "invoice to",
    "customer",
    "nombre:",
    "nombre ",
    "cliente",
    "payable to",
)

ADDRESS_ANCHORS = (
    "ship to",
    "shipping",
    "delivered to",
    "delivery address",
)


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
    match = EMAIL_RE.search(compact)
    return match.group(0) if match else None


def cleaned_phone(text: str) -> str | None:
    normalized = normalize_text(text)
    if "nif" in normalized:
        return None
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 8:
            return candidate
    return None


def looks_like_phone_token(text: str) -> bool:
    compact = text.strip()
    if not compact:
        return False
    if compact.startswith("+"):
        return True
    digits = re.sub(r"\D", "", compact)
    if len(digits) < 8:
        return False
    return bool(re.fullmatch(r"[\d().+\-\s]+", compact))


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
    if "nif" in normalized:
        return None
    patterns = [
        r"(?:invoice\s*(?:no|number|#)?|facture\s*(?:n|no|numero)?|factura\s*(?:n|no|numero|n°)?)\s*[:#-]?\s*([A-Z0-9./_-]{3,})",
        r"\bno\.?\s*([A-Z0-9./_-]{3,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if sum(ch.isdigit() for ch in value) >= 3 and not looks_like_phone_token(value):
                return value

    for token in re.findall(r"\b[A-Z0-9./_-]{4,}\b", text, re.IGNORECASE):
        if sum(ch.isdigit() for ch in token) >= 4 and not looks_like_phone_token(token):
            return token
    return None


def extract_address_lines(lines: list[str]) -> str | None:
    kept: list[str] = []
    for line in lines:
        normalized = normalize_text(line)
        if not line.strip():
            continue
        if any(anchor in normalized for anchor in ("billed to", "bill to", "shipping", "ship to", "delivered to", "payable to", "contact info", "payment terms")):
            continue
        if normalized.startswith("nif"):
            continue
        if cleaned_email(line) or cleaned_phone(line):
            continue
        if "www." in normalized or "http" in normalized:
            continue
        normalized = re.sub(r"^(direccion|dirección|ciudad)\s*:\s*", "", normalized).strip()
        line = re.sub(r"^(Dirección|Direccion|Ciudad)\s*:\s*", "", line).strip()
        kept.append(line.strip())
    if not kept:
        return None
    if len(kept) >= 2 and not re.search(r"\d", kept[0]):
        kept = kept[1:]
    if not kept:
        return None
    if len(kept) >= 2:
        return ", ".join(kept)
    return kept[0]


def extract_name(lines: list[str]) -> str | None:
    for line in lines:
        normalized = normalize_text(line)
        if any(anchor in normalized for anchor in ("billed to", "bill to", "shipping", "ship to", "delivered to", "payable to", "contact info", "payment terms")):
            continue
        if cleaned_email(line) or cleaned_phone(line):
            continue
        if any(anchor in normalized for anchor in ("invoice", "date", "description", "subtotal", "discount", "tax", "vat", "total")):
            continue
        line = re.sub(r"^(Nombre)\s*:\s*", "", line).strip()
        if any(char.isalpha() for char in line):
            return line.strip()
    return None


def strip_trailing_price(text: str) -> str:
    stripped = re.sub(r"\s+(?:[$€£]?\d[\d,]*(?:\.\d{2})?)\s*$", "", text).strip()
    return stripped or text.strip()


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
        if re.fullmatch(r"[\d\s$€£.,]+", line.strip()):
            continue
        if len(re.findall(r"[A-Za-z]", line)) < 4:
            continue
        products.append(strip_trailing_price(line))
    return " | ".join(products) if products else None


def extract_totals(payload: dict[str, dict], lines: list[str], evidence: str, method: str) -> None:
    for line in lines:
        line_normalized = normalize_text(line)
        amounts = amounts_in_text(line)
        if ("subtotal" in line_normalized or line_normalized.startswith("base")) and amounts:
            set_field(payload, "Subtotal", amounts[-1], method, evidence)
        if ("vat" in line_normalized or "tax" in line_normalized or "iva" in line_normalized) and amounts:
            set_field(payload, "VAT", amounts[-1], method, evidence)
            set_field(payload, "VAT_Rate", percent_in_text(line), method, evidence)
        if "discount" in line_normalized and amounts:
            set_field(payload, "Discount", amounts[-1], method, evidence)
            set_field(payload, "Discount_Rate", percent_in_text(line), method, evidence)
        if re.search(r"\btotal\b", line_normalized) and amounts:
            set_field(payload, "Total", amounts[-1], method, evidence)


def metadata_date_from_lines(lines: list[str], anchor: str) -> str | None:
    for index, line in enumerate(lines):
        normalized = normalize_text(line)
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
            value = first_date(candidate)
            if value:
                return value
    return None


def metadata_value_by_anchor(lines: list[str], anchors: tuple[str, ...]) -> str | None:
    for line in lines:
        normalized = normalize_text(line)
        if not any(anchor in normalized for anchor in anchors):
            continue
        if "nif" in normalized:
            continue
        value = invoice_number_from_text(line)
        if value:
            return value
    return None


def best_contact_block(regions: list[dict]) -> dict | None:
    best_region = None
    best_score = -1

    for region in regions:
        if region.get("label") != "paragraph":
            continue

        lines = [line.strip() for line in region.get("lines", []) if line.strip()]
        if not lines:
            continue

        first_line = lines[0]
        first_normalized = normalize_text(first_line)
        if cleaned_email(first_line) or cleaned_phone(first_line):
            continue
        if any(anchor in first_normalized for anchor in ("invoice", "factura", "description", "payment due", "date issued", "fecha")):
            continue

        email_count = sum(1 for line in lines if cleaned_email(line))
        phone_count = sum(1 for line in lines if cleaned_phone(line))
        website_count = sum(1 for line in lines if "www." in normalize_text(line) or "http" in normalize_text(line))
        address_count = sum(
            1
            for line in lines
            if any(token in normalize_text(line) for token in (" rd", " road", " st", " street", " ave", " avenue", " tampa", " fl"))
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
            extract_totals(payload, lines, text, "table_totals_region")

        if any(anchor in normalized for anchor in ("description", "designation", "item", "items", "products")):
            products = extract_products(lines)
            set_field(payload, "Products", products, "paragraph_region_products", text)

        if any(anchor in normalized for anchor in ISSUER_ANCHORS):
            set_field(payload, "Issuer_Name", extract_name(lines), "issuer_region", text)

        if any(anchor in normalized for anchor in CLIENT_ANCHORS):
            set_field(payload, "Client_Name", extract_name(lines), "billing_region", text)
            set_field(payload, "Billing_Address", extract_address_lines(lines), "billing_region", text)
            for line in lines:
                set_field(payload, "Client_Email", cleaned_email(line), "billing_region", text)
                set_field(payload, "Client_Phone", cleaned_phone(line), "billing_region", text)

        if any(anchor in normalized for anchor in ADDRESS_ANCHORS):
            set_field(payload, "Shipping_Address", extract_address_lines(lines), "shipping_region", text)

        if metadata_value_by_anchor(lines, ("invoice", "factura")) or any(anchor in normalized for anchor in ("invoice", "factura", "invoice no", "nvoice no", "invoice number", "invoice #", "date issued", "fecha", "due date", "payment due", "terms", "amount due")):
            set_field(payload, "Invoice_Number", metadata_value_by_anchor(lines, ("invoice", "factura")), "metadata_region", text)
            set_field(payload, "Invoice_Date", metadata_date_from_lines(lines, "date") or metadata_date_from_lines(lines, "fecha"), "metadata_region", text)
            for line in lines:
                line_normalized = normalize_text(line)
                if "invoice" in line_normalized or "factura" in line_normalized:
                    set_field(payload, "Invoice_Number", invoice_number_from_text(line), "metadata_region", text)
                if ("date" in line_normalized or "fecha" in line_normalized) and "due" not in line_normalized:
                    set_field(payload, "Invoice_Date", metadata_date_from_lines(lines, "date") or metadata_date_from_lines(lines, "fecha"), "metadata_region", text)
                if "due" in line_normalized:
                    set_field(payload, "Due_Date", metadata_date_from_lines(lines, "due"), "metadata_region", text)
                set_field(payload, "Client_Email", cleaned_email(line), "metadata_region", text)
                set_field(payload, "Client_Phone", cleaned_phone(line), "metadata_region", text)

        if label != "table" and any(anchor in normalized for anchor in ("subtotal", "tax", "vat", "discount", "total")):
            extract_totals(payload, lines, text, "paragraph_totals_fallback")

    contact_block = best_contact_block(regions)
    if contact_block is not None:
        contact_lines = [line.strip() for line in contact_block.get("lines", []) if line.strip()]
        contact_text = contact_block.get("text", "") or ""
        set_field(payload, "Client_Name", extract_name(contact_lines), "contact_block_fallback", contact_text)
        set_field(payload, "Billing_Address", extract_address_lines(contact_lines), "contact_block_fallback", contact_text)
        for line in contact_lines:
            set_field(payload, "Client_Email", cleaned_email(line), "contact_block_fallback", contact_text)
            set_field(payload, "Client_Phone", cleaned_phone(line), "contact_block_fallback", contact_text)

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

    if payload["Issuer_Name"]["value"] is None:
        skip_anchors = (
            "invoice",
            "factura",
            "date",
            "fecha",
            "billed to",
            "bill to",
            "payable to",
            "contact info",
            "payment terms",
            "invoice to",
            "customer",
            "ship to",
            "shipping",
            "invoice no",
            "invoice number",
            "invoice #",
            "subtotal",
            "total",
            "vat",
            "tax",
            "discount",
        )
        for region in regions:
            if region.get("label") != "paragraph":
                continue
            if contact_block is not None and region.get("region_index") == contact_block.get("region_index"):
                continue
            region_text = region.get("text", "") or ""
            region_normalized = normalize_text(region_text)
            if any(anchor in region_normalized for anchor in skip_anchors):
                continue
            x1, y1, _, _ = region["xyxy"]
            if x1 > 2000 or y1 > 1600:
                continue
            if region_normalized.startswith("factura") or region_normalized.startswith("fecha"):
                continue
            name = extract_name([line.strip() for line in region.get("lines", []) if line.strip()])
            if name is None or len(name.split()) < 2:
                continue
            if name:
                set_field(payload, "Issuer_Name", name, "top_paragraph_fallback", region_text)
                break

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
