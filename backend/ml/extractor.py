"""
Invoice field extractor stub.

This module will contain the extraction pipeline once the ML pipeline
is confirmed. It has no Django dependency and can be tested independently.

Expected interface (to be implemented):

    from ml.extractor import extract_invoice_fields

    result = extract_invoice_fields(storage_key: str, content_type: str) -> ExtractionOutput

    ExtractionOutput = TypedDict {
        "invoice_number": str,
        "invoice_date": date | None,
        "due_date": date | None,
        "issuer_name": str,
        "recipient_name": str,
        "total_amount": Decimal | None,
        "currency": str,
        "raw_text": str,
        "confidence_map": dict,
    }

Pipeline (planned):
    raw text
      └→ spaCy NER → candidate entities (ORG, DATE, MONEY)
      └→ Regex patterns → invoice_number, dates, amounts
      └→ Heuristic scoring → confidence_map per field
"""

from typing import TypedDict
from decimal import Decimal
from datetime import date


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
    Extract structured fields from an invoice document stored at `storage_key`.

    Not yet implemented — raises NotImplementedError until the ML
    pipeline is confirmed.
    """
    raise NotImplementedError(
        "Invoice extractor is not yet implemented. "
        "See backend_plan.md §9 for the planned pipeline."
    )
