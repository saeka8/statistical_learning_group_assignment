from rest_framework import serializers
from .models import Document, InvoiceExtraction


class DocumentListSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    confidence = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "filename", "status", "label", "confidence", "created_at"]

    def get_label(self, obj):
        if hasattr(obj, "classification"):
            return obj.classification.predicted_label
        return None

    def get_confidence(self, obj):
        if hasattr(obj, "classification"):
            return obj.classification.confidence
        return None


class DocumentDetailSerializer(serializers.ModelSerializer):
    classification = serializers.SerializerMethodField()
    invoice_data = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "filename", "content_type", "file_size",
            "status", "created_at", "classification", "invoice_data",
        ]

    def get_classification(self, obj):
        if not hasattr(obj, "classification"):
            return None
        c = obj.classification
        return {
            "predicted_label": c.predicted_label,
            "confidence": c.confidence,
            "all_scores": c.all_scores,
            "model_version": c.model_version,
            "classified_at": c.classified_at,
        }

    def get_invoice_data(self, obj):
        if not hasattr(obj, "invoice_data"):
            return None
        e = obj.invoice_data
        return {
            "invoice_number": e.invoice_number,
            "invoice_date": e.invoice_date,
            "due_date": e.due_date,
            "issuer_name": e.issuer_name,
            "recipient_name": e.recipient_name,
            "total_amount": e.total_amount,
            "currency": e.currency,
            "confidence_map": e.confidence_map,
            "extracted_at": e.extracted_at,
        }


class InvoiceExtractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceExtraction
        fields = [
            "invoice_number", "invoice_date", "due_date",
            "issuer_name", "recipient_name", "total_amount",
            "currency", "confidence_map", "extracted_at",
        ]
