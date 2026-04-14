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

        # NOTE: invoice extraction is owned by the YOLO module
        # (Feature_Extraction_Invoice/). Wire it in below when ready, e.g.:
        #
        #     if result["predicted_label"] == "invoice":
        #         from django_q.tasks import async_task
        #         async_task("apps.documents.tasks.run_extraction", str(doc.id))

    except Exception as exc:
        logger.exception("Classification failed for document %s: %s", document_id, exc)
        doc.status = DocumentStatus.ERROR
        doc.save(update_fields=["status"])
        raise


def run_extraction(document_id: str) -> None:
    """
    Async task stub — invoice field extraction.

    The extraction module is owned by the YOLO field-detection pipeline
    in `Feature_Extraction_Invoice/`. This function is intentionally a
    stub so the existing seam (model + serializer + view) stays in place;
    plug the YOLO inference call in here and write the resulting fields
    into `InvoiceExtraction`.

    Reference signature for whoever wires it up:

        fields = {
            "invoice_number": ...,
            "invoice_date":   ...,   # date | None
            "due_date":       ...,   # date | None
            "issuer_name":    ...,
            "recipient_name": ...,
            "total_amount":   ...,   # Decimal | None
            "currency":       ...,
            "raw_text":       ...,
            "confidence_map": {...},
        }
        InvoiceExtraction.objects.update_or_create(document=doc, defaults=fields)
    """
    from .models import Document

    try:
        Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error("Extraction task: document %s not found.", document_id)
        return

    logger.warning(
        "run_extraction stub called for %s — YOLO pipeline not yet wired in.",
        document_id,
    )
