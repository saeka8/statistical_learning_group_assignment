#!/usr/bin/env python3
"""OCR-first invoice field extraction for invoice images.

This script is a fallback to the YOLO-based workflow. It runs OCR on the full
invoice image, groups OCR tokens into lines, then extracts structured fields
using anchor-based rules and regex fallbacks.

Examples:
  python3 Feature_Extraction_Invoice/extract_invoice_ocr.py --image path/to/invoice.jpg
  python3 Feature_Extraction_Invoice/extract_invoice_ocr.py --image path/to/invoice.jpg --engine easyocr --pretty
  python3 Feature_Extraction_Invoice/extract_invoice_ocr.py --image path/to/invoice.jpg --dump-ocr ocr.json
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,5}\d{2,4})")
MONEY_RE = re.compile(r"(?<!\w)(?:[A-Z]{0,3}\s*)?(?:\d{1,3}(?:[ ,.\u202f]\d{3})*|\d+)(?:[.,]\d{2})?(?:\s*(?:EUR|USD|GBP|CHF|€|\$|£))?(?!\w)")
PERCENT_RE = re.compile(r"\b\d{1,2}(?:[.,]\d{1,2})?\s*%")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\b",
    re.IGNORECASE,
)
INVOICE_ID_RE = re.compile(r"\b[A-Z0-9][A-Z0-9./_-]{3,}\b", re.IGNORECASE)
SUMMARY_NOISE = ("observations", "abonnement", "augmentera", "topnet")
PAYMENT_NOISE = ("virement", "banque", "reglement", "paiement", "piece", "cheque", "attijari")
PRODUCT_NOISE = ("total", "tva", "remise", "montant", "base", "taux", "reglement")

FIELD_LABELS = {
    "numero_facture": "Invoice_Number",
    "date_facturation": "Invoice_Date",
    "echeance": "Due_Date",
    "nom_client": "Client_Name",
    "email_client": "Client_Email",
    "tel_client": "Client_Phone",
    "adresse_facturation": "Billing_Address",
    "adresse_livraison": "Shipping_Address",
    "produits": "Products",
    "total_hors_tva": "Subtotal",
    "tva": "VAT",
    "total_ttc": "Total",
    "remise": "Discount",
    "pourcentage_tva": "VAT_Rate",
    "pourcentage_remise": "Discount_Rate",
}

FIELD_RULES = {
    "numero_facture": {
        "anchors": ["invoice no", "invoice number", "invoice #", "facture n", "numero facture", "num facture", "ref facture"],
        "pattern": INVOICE_ID_RE,
    },
    "date_facturation": {
        "anchors": ["invoice date", "date facture", "date facturation", "date"],
        "pattern": DATE_RE,
    },
    "echeance": {
        "anchors": ["due date", "echeance", "date d echeance", "date limite"],
        "pattern": DATE_RE,
    },
    "nom_client": {
        "anchors": ["bill to", "billed to", "client", "customer", "nom client", "sold to"],
        "pattern": None,
    },
    "email_client": {
        "anchors": ["email", "e-mail", "mail"],
        "pattern": EMAIL_RE,
    },
    "tel_client": {
        "anchors": ["tel", "telephone", "phone", "mobile"],
        "pattern": PHONE_RE,
    },
    "adresse_facturation": {
        "anchors": ["billing address", "adresse facturation", "adresse de facturation", "bill to", "address"],
        "pattern": None,
    },
    "adresse_livraison": {
        "anchors": ["shipping address", "adresse livraison", "adresse de livraison", "ship to", "delivery address"],
        "pattern": None,
    },
    "produits": {
        "anchors": ["description", "item", "items", "produits", "designation"],
        "pattern": None,
    },
    "total_hors_tva": {
        "anchors": ["subtotal", "total ht", "total h t", "total hors tva", "hors taxes", "net amount"],
        "pattern": MONEY_RE,
    },
    "tva": {
        "anchors": ["montant tva", "total tva", "vat amount", "tax amount", "tva"],
        "pattern": MONEY_RE,
    },
    "total_ttc": {
        "anchors": ["total ttc", "montant ttc", "ttc", "total due", "amount due", "balance due", "grand total"],
        "pattern": MONEY_RE,
    },
    "remise": {
        "anchors": ["discount", "remise"],
        "pattern": MONEY_RE,
    },
    "pourcentage_tva": {
        "anchors": ["vat rate", "tax rate", "pourcentage tva", "taux tva"],
        "pattern": PERCENT_RE,
    },
    "pourcentage_remise": {
        "anchors": ["discount rate", "pourcentage remise", "taux remise"],
        "pattern": PERCENT_RE,
    },
}


@dataclass
class OCRToken:
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
class OCRLine:
    text: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    tokens: list[OCRToken]

    @property
    def center_y(self) -> float:
        return (self.ymin + self.ymax) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.ymax - self.ymin)


@dataclass
class ExtractedField:
    value: str | None
    method: str
    confidence: float
    evidence: str | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OCR-first invoice field extraction.")
    parser.add_argument("--image", type=Path, required=True, help="Path to an invoice image.")
    parser.add_argument(
        "--engine",
        choices=["auto", "easyocr", "paddleocr", "tesseract"],
        default="auto",
        help="OCR engine to use. 'auto' tries paddleocr, then easyocr, then pytesseract.",
    )
    parser.add_argument(
        "--easyocr-langs",
        default="en,fr",
        help="Comma-separated EasyOCR languages, default 'en,fr'.",
    )
    parser.add_argument(
        "--tesseract-lang",
        default="eng+fra",
        help="pytesseract language string, default 'eng+fra'.",
    )
    parser.add_argument("--dump-ocr", type=Path, help="Optional path to dump raw OCR tokens as JSON.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9%@./,_#:$€£+\- ]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def score_regex_match(pattern: re.Pattern[str] | None, text: str) -> str | None:
    if pattern is None:
        stripped = text.strip(" :-")
        return stripped or None
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def contains_anchor(normalized_line: str, anchor: str) -> bool:
    padded_line = f" {normalized_line} "
    padded_anchor = f" {anchor} "
    return padded_anchor in padded_line or normalized_line.startswith(anchor + " ") or normalized_line.endswith(" " + anchor)


def monetary_matches(text: str) -> list[str]:
    return [match.group(0).strip() for match in MONEY_RE.finditer(text)]


def invoice_id_matches(text: str) -> list[str]:
    matches: list[str] = []
    for match in INVOICE_ID_RE.finditer(text):
        token = match.group(0).strip()
        digits = sum(character.isdigit() for character in token)
        if digits < 4:
            continue
        if normalize_text(token) in {"code", "facture", "invoice", "numero", "number", "ref"}:
            continue
        matches.append(token)
    return matches


def looks_like_table_header(normalized: str) -> bool:
    header_terms = (
        "designation",
        "date debut",
        "date fin",
        "quantite",
        "puht",
        "remise",
        "tva",
        "base tva",
        "montant tva",
        "total ht",
    )
    return sum(term in normalized for term in header_terms) >= 3


def pick_field_value(field_name: str, text: str) -> str | None:
    normalized = normalize_text(text)
    if field_name == "numero_facture":
        matches = invoice_id_matches(text)
        return matches[-1] if matches else None

    if field_name == "total_hors_tva":
        matches = monetary_matches(text)
        if not matches:
            return None
        return matches[-1]

    if field_name == "total_ttc":
        matches = monetary_matches(text)
        if not matches:
            return None
        if "ttc" not in normalized and "amount due" not in normalized and "balance due" not in normalized:
            return None
        return matches[-1]

    if field_name == "tva":
        matches = monetary_matches(text)
        if not matches:
            return None
        if "montant tva" in normalized or "total tva" in normalized or "vat amount" in normalized or "tax amount" in normalized:
            return matches[-1]
        if looks_like_table_header(normalized):
            return None
        if "total ht" in normalized and len(matches) == 1:
            return None
        return matches[-1] if len(matches) > 1 else None

    if field_name == "remise":
        matches = monetary_matches(text)
        if not matches:
            return None
        return matches[-1]

    if field_name in {"pourcentage_tva", "pourcentage_remise"}:
        matches = [match.group(0).strip() for match in PERCENT_RE.finditer(text)]
        return matches[-1] if matches else None

    if field_name in {"date_facturation", "echeance"}:
        matches = [match.group(0).strip() for match in DATE_RE.finditer(text)]
        return matches[-1] if matches else None

    if field_name == "tel_client":
        return phone_from_text(text)

    return score_regex_match(FIELD_RULES[field_name]["pattern"], text)


def phone_from_text(text: str) -> str | None:
    normalized = normalize_text(text)
    if any(noise in normalized for noise in ("facture", "invoice", "code ", "reference", "ref ")):
        return None
    if any(noise in normalized for noise in PAYMENT_NOISE):
        return None
    candidates: list[str] = []
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) < 8:
            continue
        if len(set(candidate) & set("+-(). ")) == 0 and len(digits) > 10:
            continue
        candidates.append(candidate)
    return candidates[0] if candidates else None


def load_ocr_tokens(args: argparse.Namespace) -> tuple[str, list[OCRToken]]:
    if args.engine == "auto":
        for engine in ("paddleocr", "easyocr", "tesseract"):
            try:
                return engine, run_ocr(engine, args)
            except ModuleNotFoundError:
                continue
        raise SystemExit(
            "No OCR engine available. Install one of: paddleocr, easyocr, or pytesseract+tesseract."
        )
    return args.engine, run_ocr(args.engine, args)


def run_ocr(engine: str, args: argparse.Namespace) -> list[OCRToken]:
    if engine == "easyocr":
        return run_easyocr(args.image, args.easyocr_langs)
    if engine == "paddleocr":
        return run_paddleocr(args.image)
    if engine == "tesseract":
        return run_tesseract(args.image, args.tesseract_lang)
    raise ValueError(f"Unsupported engine: {engine}")


def run_easyocr(image_path: Path, langs: str) -> list[OCRToken]:
    import easyocr  # type: ignore

    reader = easyocr.Reader([lang.strip() for lang in langs.split(",") if lang.strip()], gpu=False)
    results = reader.readtext(str(image_path), detail=1, paragraph=False)
    tokens: list[OCRToken] = []
    for bbox, text, confidence in results:
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        tokens.append(
            OCRToken(
                text=str(text).strip(),
                confidence=float(confidence),
                xmin=float(min(xs)),
                ymin=float(min(ys)),
                xmax=float(max(xs)),
                ymax=float(max(ys)),
            )
        )
    return filter_tokens(tokens)


def run_paddleocr(image_path: Path) -> list[OCRToken]:
    from paddleocr import PaddleOCR  # type: ignore

    reader = PaddleOCR(use_angle_cls=True, lang="fr")
    results = reader.ocr(str(image_path), cls=True)
    tokens: list[OCRToken] = []
    for page in results:
        for bbox, payload in page:
            text, confidence = payload
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            tokens.append(
                OCRToken(
                    text=str(text).strip(),
                    confidence=float(confidence),
                    xmin=float(min(xs)),
                    ymin=float(min(ys)),
                    xmax=float(max(xs)),
                    ymax=float(max(ys)),
                )
            )
    return filter_tokens(tokens)


def run_tesseract(image_path: Path, lang: str) -> list[OCRToken]:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore

    data = pytesseract.image_to_data(
        Image.open(image_path),
        lang=lang,
        output_type=pytesseract.Output.DICT,
    )
    tokens: list[OCRToken] = []
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
        tokens.append(
            OCRToken(
                text=text,
                confidence=confidence / 100.0,
                xmin=xmin,
                ymin=ymin,
                xmax=xmin + width,
                ymax=ymin + height,
            )
        )
    return filter_tokens(tokens)


def filter_tokens(tokens: Iterable[OCRToken]) -> list[OCRToken]:
    filtered = [token for token in tokens if token.text and token.confidence >= 0.0]
    filtered.sort(key=lambda token: (token.center_y, token.xmin))
    return filtered


def group_lines(tokens: list[OCRToken]) -> list[OCRLine]:
    if not tokens:
        return []

    lines: list[list[OCRToken]] = []
    for token in tokens:
        placed = False
        for line_tokens in lines:
            avg_center = sum(item.center_y for item in line_tokens) / len(line_tokens)
            avg_height = sum(item.height for item in line_tokens) / len(line_tokens)
            if abs(token.center_y - avg_center) <= max(10.0, avg_height * 0.6):
                line_tokens.append(token)
                placed = True
                break
        if not placed:
            lines.append([token])

    grouped: list[OCRLine] = []
    for line_tokens in lines:
        line_tokens.sort(key=lambda token: token.xmin)
        text = " ".join(token.text for token in line_tokens).strip()
        grouped.append(
            OCRLine(
                text=text,
                xmin=min(token.xmin for token in line_tokens),
                ymin=min(token.ymin for token in line_tokens),
                xmax=max(token.xmax for token in line_tokens),
                ymax=max(token.ymax for token in line_tokens),
                tokens=line_tokens,
            )
        )
    grouped.sort(key=lambda line: (line.center_y, line.xmin))
    return grouped


def find_regex_globally(lines: list[OCRLine], pattern: re.Pattern[str]) -> ExtractedField | None:
    candidates: list[tuple[float, str, str]] = []
    for line in lines:
        match = pattern.search(line.text)
        if match:
            candidates.append((max((token.confidence for token in line.tokens), default=0.0), match.group(0), line.text))
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: item[0])
    score, value, evidence = candidates[0]
    return ExtractedField(value=value, method="global_regex", confidence=score, evidence=evidence)


def pick_anchor_candidate(field_name: str, lines: list[OCRLine]) -> ExtractedField | None:
    rule = FIELD_RULES[field_name]
    anchors = [normalize_text(anchor) for anchor in rule["anchors"]]

    for index, line in enumerate(lines):
        normalized_line = normalize_text(line.text)
        if not any(contains_anchor(normalized_line, anchor) for anchor in anchors):
            continue

        if field_name == "produits":
            product_candidate = pick_product_candidate(lines, index)
            if product_candidate is not None:
                return product_candidate

        same_line_value = pick_field_value(field_name, strip_anchor_prefix(line.text, anchors))
        if same_line_value:
            return ExtractedField(
                value=same_line_value,
                method="anchor_same_line",
                confidence=max((token.confidence for token in line.tokens), default=0.0),
                evidence=line.text,
            )

        right_value = nearest_token_right_of_anchor(line, field_name)
        if right_value is not None:
            return right_value

        for neighbor in nearby_lines(lines, index):
            candidate = pick_field_value(field_name, neighbor.text)
            if candidate:
                return ExtractedField(
                    value=candidate,
                    method="anchor_nearby_line",
                    confidence=max((token.confidence for token in neighbor.tokens), default=0.0),
                    evidence=neighbor.text,
                )

            if FIELD_RULES[field_name]["pattern"] is None and neighbor.text.strip():
                return ExtractedField(
                    value=neighbor.text.strip(),
                    method="anchor_nearby_line",
                    confidence=max((token.confidence for token in neighbor.tokens), default=0.0),
                    evidence=neighbor.text,
                )
    return None


def strip_anchor_prefix(text: str, normalized_anchors: list[str]) -> str:
    parts = re.split(r"[:\-]", text, maxsplit=1)
    if len(parts) == 2 and any(anchor in normalize_text(parts[0]) for anchor in normalized_anchors):
        return parts[1].strip()
    return text


def nearest_token_right_of_anchor(line: OCRLine, field_name: str) -> ExtractedField | None:
    if len(line.tokens) < 2:
        return None
    normalized_tokens = [normalize_text(token.text) for token in line.tokens]
    anchor_end_index = 0
    for idx, token_text in enumerate(normalized_tokens):
        if token_text in {"invoice", "date", "total", "email", "tel", "phone", "vat", "tax", "client", "facture"}:
            anchor_end_index = idx
    for token in line.tokens[anchor_end_index + 1 :]:
        candidate = pick_field_value(field_name, token.text)
        if candidate:
            return ExtractedField(
                value=candidate,
                method="anchor_right_token",
                confidence=token.confidence,
                evidence=line.text,
            )
    return None


def nearby_lines(lines: list[OCRLine], anchor_index: int) -> list[OCRLine]:
    candidates: list[OCRLine] = []
    anchor_line = lines[anchor_index]
    for offset in (1, 2):
        if anchor_index + offset >= len(lines):
            break
        line = lines[anchor_index + offset]
        if abs(line.center_y - anchor_line.center_y) <= anchor_line.height * (1.5 + offset):
            continue
        candidates.append(line)
    return candidates


def pick_product_candidate(lines: list[OCRLine], anchor_index: int) -> ExtractedField | None:
    for offset in range(1, 9):
        if anchor_index + offset >= len(lines):
            break
        neighbor = lines[anchor_index + offset]
        normalized = normalize_text(neighbor.text)
        if looks_like_table_header(normalized):
            continue
        if any(keyword in normalized for keyword in PRODUCT_NOISE):
            continue
        if len(re.findall(r"[A-Za-z]", neighbor.text)) < 5:
            continue
        value = strip_product_noise(neighbor.text)
        if value:
            return ExtractedField(
                value=value,
                method="anchor_product_row",
                confidence=max((token.confidence for token in neighbor.tokens), default=0.0),
                evidence=neighbor.text,
            )
    return None


def strip_product_noise(text: str) -> str | None:
    cleaned = re.split(DATE_RE, text, maxsplit=1)[0].strip(" :-")
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"(?:\b\d+[.,]?\d*\b\s*){2,}$", "", cleaned).strip(" :-")
    return cleaned or None


def extract_fields(lines: list[OCRLine]) -> dict[str, ExtractedField]:
    extracted: dict[str, ExtractedField] = {}

    global_email = find_regex_globally(lines, EMAIL_RE)
    if global_email:
        extracted["email_client"] = global_email

    global_phone = best_phone(lines)
    if global_phone:
        extracted["tel_client"] = global_phone

    for field_name in FIELD_RULES:
        if field_name in extracted:
            continue
        anchored = pick_anchor_candidate(field_name, lines)
        if anchored:
            extracted[field_name] = anchored

    if "total_ttc" not in extracted:
        biggest_amount = largest_amount(lines)
        if biggest_amount:
            extracted["total_ttc"] = biggest_amount

    return extracted


def best_phone(lines: list[OCRLine]) -> ExtractedField | None:
    candidates: list[tuple[int, float, str, str]] = []
    for line in lines:
        normalized = normalize_text(line.text)
        if any(noise in normalized for noise in SUMMARY_NOISE):
            continue
        if any(noise in normalized for noise in PAYMENT_NOISE):
            continue
        anchored = any(keyword in normalized for keyword in ("tel", "telephone", "phone", "mobile", "gsm"))
        for match in PHONE_RE.finditer(line.text):
            candidate = match.group(0).strip()
            digits = re.sub(r"\D", "", candidate)
            if len(digits) < 7:
                continue
            if not anchored:
                continue
            candidates.append((len(digits), max((token.confidence for token in line.tokens), default=0.0), candidate, line.text))
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: (item[0], item[1]))
    _, score, value, evidence = candidates[0]
    return ExtractedField(value=value, method="global_regex", confidence=score, evidence=evidence)


def largest_amount(lines: list[OCRLine]) -> ExtractedField | None:
    best_value: tuple[float, str, str, float] | None = None
    for line in lines:
        for match in MONEY_RE.finditer(line.text):
            amount_text = match.group(0).strip()
            amount_numeric = parse_amount(amount_text)
            if amount_numeric is None:
                continue
            score = max((token.confidence for token in line.tokens), default=0.0)
            if best_value is None or amount_numeric > best_value[0]:
                best_value = (amount_numeric, amount_text, line.text, score)
    if best_value is None:
        return None
    _, text, evidence, score = best_value
    return ExtractedField(value=text, method="largest_amount_fallback", confidence=score, evidence=evidence)


def parse_amount(text: str) -> float | None:
    cleaned = re.sub(r"[A-Za-z€$£\s]", "", text)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def dump_ocr_tokens(path: Path, tokens: list[OCRToken]) -> None:
    payload = [asdict(token) for token in tokens]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()

    if not args.image.exists():
        raise SystemExit(f"Image not found: {args.image}")

    engine, tokens = load_ocr_tokens(args)
    lines = group_lines(tokens)
    extracted = extract_fields(lines)

    if args.dump_ocr:
        dump_ocr_tokens(args.dump_ocr, tokens)

    payload = {
        "engine": engine,
        "image": str(args.image.resolve()),
        "token_count": len(tokens),
        "line_count": len(lines),
        "extracted_fields": {
            FIELD_LABELS[key]: asdict(value) for key, value in extracted.items()
        },
    }

    if args.pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
