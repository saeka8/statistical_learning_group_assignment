"""
Document classifier stub.

This module will contain the trained classifier once the ML pipeline
is confirmed. It has no Django dependency and can be tested independently.

Expected interface (to be implemented):

    from ml.classifier import classify

    result = classify(storage_key: str, content_type: str) -> ClassificationOutput

    ClassificationOutput = TypedDict {
        "predicted_label": str,   # one of: invoice, email, scientific_publication, resume, unknown
        "confidence": float,      # 0.0 – 1.0
        "all_scores": dict,       # {label: score}
        "model_version": str,
    }

Pipeline (planned):
    raw file
      └→ OCR (if image/scanned PDF)
      └→ Text extraction (if native PDF)
      └→ Text cleaning & normalization
      └→ TF-IDF feature extraction
      └→ SVM / Random Forest classifier
      └→ (label, confidence, all_scores)
"""

from typing import TypedDict


class ClassificationOutput(TypedDict):
    predicted_label: str
    confidence: float
    all_scores: dict
    model_version: str


def classify(storage_key: str, content_type: str) -> ClassificationOutput:
    """
    Classify a document stored at `storage_key` in MinIO.

    Not yet implemented — raises NotImplementedError until the ML
    pipeline is confirmed and models are trained.
    """
    raise NotImplementedError(
        "ML classifier is not yet implemented. "
        "See backend_plan.md §9 for the planned pipeline."
    )
