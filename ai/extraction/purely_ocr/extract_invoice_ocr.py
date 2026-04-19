#!/usr/bin/env python3
"""OCR-first invoice field extraction for invoice images.

This script is a fallback to the YOLO-based workflow. It runs OCR on the full
invoice image, groups OCR tokens into lines, then extracts structured fields
using anchor-based rules and regex fallbacks.

Examples:
  python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image path/to/invoice.jpg
  python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image path/to/invoice.jpg --engine easyocr --pretty
  python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image path/to/invoice.jpg --dump-ocr ocr.json
  python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image path/to/invoice.jpg --preprocess --pretty
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from ai.extraction.purely_ocr.shared_ocr import (
    OCRLine,
    OCRToken,
    filter_tokens,
    group_lines,
    ocr_pil_tesseract,
    ocr_pil_tesseract_tokens,
)


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
ISSUER_SKIP_NOISE = (
    "invoice",
    "facture",
    "bill to",
    "billed to",
    "ship to",
    "shipping",
    "customer",
    "subtotal",
    "total",
    "tva",
    "vat",
    "discount",
    "tax",
    "amount due",
    "balance due",
)

# Maximum number of lines to scan below a "Products" header when collecting
# product rows. 30 is generous enough for invoices with many line items while
# still bounding the search.
_MAX_PRODUCT_LINES = 30

FIELD_LABELS = {
    "numero_facture": "Invoice_Number",
    "date_facturation": "Invoice_Date",
    "echeance": "Due_Date",
    "nom_emetteur": "Issuer_Name",
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
    "nom_emetteur": {
        "anchors": ["from", "from:", "issued by", "emis par", "emetteur", "vendeur", "fournisseur", "supplier", "seller", "societe"],
        "pattern": None,
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
        "--paddleocr-lang",
        default="fr",
        help="PaddleOCR language string, default 'fr'.",
    )
    parser.add_argument(
        "--tesseract-lang",
        default="eng+fra",
        help="pytesseract language string, default 'eng+fra'.",
    )
    parser.add_argument("--dump-ocr", type=Path, help="Optional path to dump raw OCR tokens as JSON.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Apply OpenCV pre-processing (deskew, denoise, binarize) before OCR.",
    )
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


def preprocess_image(image_path: Path) -> Path:
    """Deskew, denoise, and binarize an invoice image using OpenCV.

    Returns the path to a temporary pre-processed image that OCR engines
    can consume. The temporary file is cleaned up by the caller (load_ocr_tokens)
    in its finally block.
    """
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    import tempfile

    # Block size and constant for adaptive thresholding.
    # 31 is large enough to cover typical text stroke widths on invoice scans;
    # C=10 compensates for uneven illumination typical in scanned documents.
    _ADAPTIVE_BLOCK_SIZE = 31
    _ADAPTIVE_C = 10

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"OpenCV could not load image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Light denoising
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Deskew using the dominant angle of text lines
    coords = np.column_stack(np.where(denoised < 128))
    if coords.shape[0] > 50:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.3:
            (h, w) = denoised.shape
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            denoised = cv2.warpAffine(denoised, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Adaptive binarization
    binarized = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        _ADAPTIVE_BLOCK_SIZE, _ADAPTIVE_C,
    )

    suffix = Path(image_path).suffix or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    cv2.imwrite(tmp.name, binarized)
    return Path(tmp.name)


def load_ocr_tokens(args: argparse.Namespace) -> tuple[str, list[OCRToken]]:
    image_path = args.image
    tmp_path: Path | None = None
    if getattr(args, "preprocess", False):
        tmp_path = preprocess_image(image_path)
        image_path = tmp_path

    try:
        if args.engine == "auto":
            failures: list[str] = []
            for engine in ("paddleocr", "easyocr", "tesseract"):
                try:
                    return engine, run_ocr(engine, args, image_path)
                except Exception as exc:
                    failures.append(f"{engine}: {exc.__class__.__name__}: {exc}")
                    continue
            raise SystemExit(
                "No OCR engine available. Tried paddleocr, easyocr, and tesseract.\n"
                + "\n".join(failures)
            )
        return args.engine, run_ocr(args.engine, args, image_path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def run_ocr(engine: str, args: argparse.Namespace, image_path: Path) -> list[OCRToken]:
    if engine == "easyocr":
        return run_easyocr(image_path, args.easyocr_langs)
    if engine == "paddleocr":
        return run_paddleocr(image_path, args.paddleocr_lang)
    if engine == "tesseract":
        return run_tesseract(image_path, args.tesseract_lang)
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


def run_paddleocr(image_path: Path, lang: str = "fr") -> list[OCRToken]:
    from paddleocr import PaddleOCR  # type: ignore

    reader = PaddleOCR(use_angle_cls=True, lang=lang)
    try:
        # PaddleOCR 2.x style API.
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
    except TypeError:
        # PaddleOCR 3.x pipeline API. `predict()` returns result objects whose
        # JSON/dict payload includes recognized texts plus either polygons or boxes.
        results = reader.predict(str(image_path))
        tokens: list[OCRToken] = []
        for page in results:
            payload = getattr(page, "json", page)
            if isinstance(payload, str):
                payload = json.loads(payload)
            if isinstance(payload, dict) and "res" in payload:
                payload = payload["res"]
            if not isinstance(payload, dict):
                continue

            texts = payload.get("rec_texts", []) or []
            scores = payload.get("rec_scores", []) or []
            boxes = payload.get("rec_boxes")
            polys = payload.get("rec_polys") or payload.get("dt_polys")

            if boxes is not None:
                for text, confidence, box in zip(texts, scores, boxes):
                    xmin, ymin, xmax, ymax = [float(value) for value in box]
                    tokens.append(
                        OCRToken(
                            text=str(text).strip(),
                            confidence=float(confidence),
                            xmin=xmin,
                            ymin=ymin,
                            xmax=xmax,
                            ymax=ymax,
                        )
                    )
                continue

            if polys is not None:
                for text, confidence, bbox in zip(texts, scores, polys):
                    xs = [float(point[0]) for point in bbox]
                    ys = [float(point[1]) for point in bbox]
                    tokens.append(
                        OCRToken(
                            text=str(text).strip(),
                            confidence=float(confidence),
                            xmin=min(xs),
                            ymin=min(ys),
                            xmax=max(xs),
                            ymax=max(ys),
                        )
                    )

        return filter_tokens(tokens)


def run_tesseract(image_path: Path, lang: str) -> list[OCRToken]:
    from PIL import Image  # type: ignore

    return ocr_pil_tesseract_tokens(Image.open(image_path), lang)


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
    field_anchors = [normalize_text(a) for a in FIELD_RULES[field_name]["anchors"]]
    normalized_tokens = [normalize_text(token.text) for token in line.tokens]
    anchor_end_index = 0
    # Find the rightmost token whose text is part of any anchor phrase so that
    # we start looking for the value only after the full anchor label.
    for idx, token_text in enumerate(normalized_tokens):
        if token_text and any(token_text in anchor for anchor in field_anchors):
            anchor_end_index = idx
    for token in line.tokens[anchor_end_index + 1:]:
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
        if abs(line.center_y - anchor_line.center_y) > anchor_line.height * (1.5 + offset):
            continue
        candidates.append(line)
    return candidates


def pick_product_candidate(lines: list[OCRLine], anchor_index: int) -> ExtractedField | None:
    product_rows: list[str] = []
    for offset in range(1, _MAX_PRODUCT_LINES + 1):
        if anchor_index + offset >= len(lines):
            break
        neighbor = lines[anchor_index + offset]
        normalized = normalize_text(neighbor.text)
        # Stop collecting when we hit a summary/total line.
        if any(keyword in normalized for keyword in ("total", "sous-total", "subtotal", "montant total")):
            break
        if looks_like_table_header(normalized):
            continue
        if any(keyword in normalized for keyword in PRODUCT_NOISE):
            continue
        if len(re.findall(r"[A-Za-z]", neighbor.text)) < 5:
            continue
        value = strip_product_noise(neighbor.text)
        if value:
            product_rows.append(value)
    if not product_rows:
        return None
    # Return all rows joined by a separator; confidence from the first row's tokens.
    first_neighbor_idx = anchor_index + 1
    first_tokens = lines[first_neighbor_idx].tokens if first_neighbor_idx < len(lines) else []
    return ExtractedField(
        value=" | ".join(product_rows),
        method="anchor_product_rows",
        confidence=max((token.confidence for token in first_tokens), default=0.0),
        evidence=product_rows[0],
    )


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

    if "nom_emetteur" not in extracted:
        issuer = best_issuer(lines)
        if issuer:
            extracted["nom_emetteur"] = issuer

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


def best_issuer(lines: list[OCRLine]) -> ExtractedField | None:
    if not lines:
        return None

    page_top = min(line.ymin for line in lines)
    page_bottom = max(line.ymax for line in lines)
    top_cutoff = page_top + (page_bottom - page_top) * 0.35

    for line in lines:
        if line.center_y > top_cutoff:
            break

        text = line.text.strip()
        normalized = normalize_text(text)
        if len(re.findall(r"[A-Za-z]", text)) < 3:
            continue
        if any(noise in normalized for noise in ISSUER_SKIP_NOISE):
            continue
        if EMAIL_RE.search(text) or phone_from_text(text):
            continue
        if invoice_id_matches(text) or DATE_RE.search(text):
            continue

        return ExtractedField(
            value=text,
            method="top_of_page_fallback",
            confidence=max((token.confidence for token in line.tokens), default=0.0),
            evidence=text,
        )

    return None


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
