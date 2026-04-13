import logging

logger = logging.getLogger(__name__)


def run_classification(document_id: str) -> None:
    """
    Async task: classify a document and persist the result.

    Called automatically after upload and can be re-triggered via
    POST /api/documents/{id}/classify/
    """
    from .models import Document, DocumentStatus, ClassificationResult

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error("Classification task: document %s not found.", document_id)
        return

    doc.status = DocumentStatus.PROCESSING
    doc.save(update_fields=["status"])

    try:
        # TODO: replace stub with actual ML pipeline once confirmed
        # from ml.classifier import classify
        # result = classify(doc.storage_key, doc.content_type)

        # --- Stub result ---
        predicted_label = "unknown"
        confidence = 0.0
        all_scores = {
            "invoice": 0.0,
            "email": 0.0,
            "scientific_publication": 0.0,
            "resume": 0.0,
            "unknown": 1.0,
        }
        model_version = "stub"
        # -------------------

        ClassificationResult.objects.update_or_create(
            document=doc,
            defaults={
                "predicted_label": predicted_label,
                "confidence": confidence,
                "all_scores": all_scores,
                "model_version": model_version,
            },
        )

        doc.status = DocumentStatus.DONE
        doc.save(update_fields=["status"])

        logger.info(
            "Document %s classified as '%s' (confidence %.2f).",
            document_id, predicted_label, confidence,
        )

    except Exception as exc:
        logger.exception("Classification failed for document %s: %s", document_id, exc)
        doc.status = DocumentStatus.ERROR
        doc.save(update_fields=["status"])
        raise


def run_extraction(document_id: str) -> None:
    """
    Async task: extract structured fields from an invoice document.

    Automatically enqueued by run_classification when predicted_label == 'invoice'.
    """
    from .models import Document, DocumentStatus, InvoiceExtraction

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error("Extraction task: document %s not found.", document_id)
        return

    try:
        # TODO: replace stub with actual extraction pipeline once confirmed
        # from ml.extractor import extract_invoice_fields
        # fields = extract_invoice_fields(doc.storage_key, doc.content_type)

        # --- Stub result ---
        fields = {
            "invoice_number": "",
            "invoice_date": None,
            "due_date": None,
            "issuer_name": "",
            "recipient_name": "",
            "total_amount": None,
            "currency": "",
            "raw_text": "",
            "confidence_map": {},
        }
        # -------------------

        InvoiceExtraction.objects.update_or_create(document=doc, defaults=fields)

        doc.status = DocumentStatus.DONE
        doc.save(update_fields=["status"])

        logger.info("Invoice extraction complete for document %s.", document_id)

    except Exception as exc:
        logger.exception("Extraction failed for document %s: %s", document_id, exc)
        doc.status = DocumentStatus.ERROR
        doc.save(update_fields=["status"])
        raise
