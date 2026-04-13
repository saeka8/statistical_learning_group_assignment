from django.contrib import admin
from .models import Document, ClassificationResult, InvoiceExtraction


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["filename", "owner", "status", "content_type", "file_size", "created_at"]
    list_filter = ["status", "content_type"]
    search_fields = ["filename", "owner__username"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(ClassificationResult)
class ClassificationResultAdmin(admin.ModelAdmin):
    list_display = ["document", "predicted_label", "confidence", "model_version", "classified_at"]
    list_filter = ["predicted_label", "model_version"]
    search_fields = ["document__filename"]
    readonly_fields = ["classified_at"]


@admin.register(InvoiceExtraction)
class InvoiceExtractionAdmin(admin.ModelAdmin):
    list_display = [
        "document", "invoice_number", "invoice_date",
        "issuer_name", "total_amount", "currency", "extracted_at",
    ]
    search_fields = ["document__filename", "invoice_number", "issuer_name"]
    readonly_fields = ["extracted_at"]
