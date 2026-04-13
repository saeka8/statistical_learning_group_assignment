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
        from ml.classifier import classify

        result = classify(doc.storage_key, doc.content_type)

        ClassificationResult.objects.update_or_create(
            document=doc,
            defaults={
                "predicted_label": result["predicted_label"],
                "confidence": result["confidence"],
                "all_scores": result["all_scores"],
                "model_version": result["model_version"],
            },
        )

        doc.status = DocumentStatus.DONE
        doc.save(update_fields=["status"])

        logger.info(
            "Document %s classified as '%s' (confidence %.2f).",
            document_id, result["predicted_label"], result["confidence"],
        )

        # If classified as invoice, automatically enqueue extraction
        if result["predicted_label"] == "invoice":
            from django_q.tasks import async_task

            async_task("apps.documents.tasks.run_extraction", str(doc.id))
            logger.info("Invoice detected — extraction task enqueued for %s.", document_id)

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
        from ml.extractor import extract_invoice_fields

        fields = extract_invoice_fields(doc.storage_key, doc.content_type)

        InvoiceExtraction.objects.update_or_create(document=doc, defaults=fields)

        doc.status = DocumentStatus.DONE
        doc.save(update_fields=["status"])

        logger.info("Invoice extraction complete for document %s.", document_id)

    except Exception as exc:
        logger.exception("Extraction failed for document %s: %s", document_id, exc)
        doc.status = DocumentStatus.ERROR
        doc.save(update_fields=["status"])
        raise
