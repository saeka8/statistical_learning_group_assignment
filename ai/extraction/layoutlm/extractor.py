"""
LayoutLM-based invoice field extractor.

Uses the `impira/layoutlm-document-qa` checkpoint (LayoutLMv2) via the
HuggingFace `transformers` document-question-answering pipeline.

No fine-tuning is performed — the model is used zero-shot by asking one
targeted natural-language question per invoice field.

Usage
-----
from ai.extraction.layoutlm.extractor import extract_with_layoutlm

results = extract_with_layoutlm(pil_image)
# results = {"Invoice_Number": "INV-0042", "Total": "1 234,00 EUR", ...}
# Fields that could not be answered are absent from the dict.
"""

from __future__ import annotations

import logging
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton pipeline (loaded once on first call)
# ---------------------------------------------------------------------------

_PIPELINE: Any | None = None
_PIPELINE_FAILED = False  # set to True if import / model-load fails


def _load_pipeline():
    global _PIPELINE, _PIPELINE_FAILED
    if _PIPELINE is not None:
        return _PIPELINE
    if _PIPELINE_FAILED:
        return None
    try:
        from transformers import pipeline  # type: ignore

        logger.info("Loading LayoutLMv2 document-QA pipeline (impira/layoutlm-document-qa) …")
        _PIPELINE = pipeline(
            "document-question-answering",
            model="impira/layoutlm-document-qa",
        )
        logger.info("LayoutLMv2 pipeline ready.")
        return _PIPELINE
    except Exception as exc:
        logger.warning("LayoutLM pipeline load failed (%s) — LayoutLM extraction disabled.", exc)
        _PIPELINE_FAILED = True
        return None


# ---------------------------------------------------------------------------
# Questions per field
# ---------------------------------------------------------------------------

# Map from our canonical field name → list of questions to try (in order).
# We ask only the first question; the list allows fallback phrasing.
_FIELD_QUESTIONS: dict[str, list[str]] = {
    "Invoice_Number":   ["What is the invoice number?", "What is the invoice #?"],
    "Invoice_Date":     ["What is the invoice date?", "What is the date of the invoice?"],
    "Due_Date":         ["What is the due date?", "What is the payment due date?"],
    "Issuer_Name":      ["What is the name of the company issuing this invoice?", "Who issued this invoice?"],
    "Client_Name":      ["What is the name of the client or customer?", "Who is billed?"],
    "Client_Email":     ["What is the client email address?"],
    "Client_Phone":     ["What is the client phone number?"],
    "Billing_Address":  ["What is the billing address?"],
    "Shipping_Address": ["What is the shipping or delivery address?"],
    "Subtotal":         ["What is the subtotal amount?"],
    "VAT":              ["What is the VAT or tax amount?"],
    "VAT_Rate":         ["What is the VAT rate or tax rate?"],
    "Total":            ["What is the total amount due?", "What is the total?"],
    "Discount":         ["What is the discount amount?"],
    "Discount_Rate":    ["What is the discount rate?"],
    "Products":         ["What are the products or items listed on the invoice?"],
}

# Minimum score threshold below which an answer is discarded
_MIN_SCORE = 0.05


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_with_layoutlm(image: Image.Image) -> dict[str, str]:
    """Run LayoutLMv2 document-QA on *image* and return a dict of field→answer.

    Only fields with a confidence score above ``_MIN_SCORE`` are included.
    Fields where the model is not confident are omitted so that the
    anchor-based fallback can fill the gap.

    Parameters
    ----------
    image:
        Full invoice image as a PIL Image (any mode; converted to RGB internally).

    Returns
    -------
    dict[str, str]
        Mapping of canonical field name → raw string answer.
    """
    pipe = _load_pipeline()
    if pipe is None:
        return {}

    image = image.convert("RGB")
    results: dict[str, str] = {}

    for field, questions in _FIELD_QUESTIONS.items():
        for question in questions:
            try:
                answer = pipe(image, question)
                # pipeline returns a dict or list[dict]; normalise
                if isinstance(answer, list):
                    answer = answer[0] if answer else {}
                score = float(answer.get("score", 0.0))
                text = (answer.get("answer") or "").strip()
                if text and score >= _MIN_SCORE:
                    results[field] = text
                    logger.debug("LayoutLM  %-22s %r  (score=%.3f)", field, text, score)
                    break  # got a good answer, skip fallback questions
            except Exception as exc:
                logger.debug("LayoutLM question failed for %s: %s", field, exc)

    return results
