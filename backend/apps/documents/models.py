import uuid
from django.db import models
from django.contrib.auth.models import User


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    DONE = "done", "Done"
    ERROR = "error", "Error"


class DocumentCategory(models.TextChoices):
    INVOICE = "invoice", "Invoice"
    EMAIL = "email", "Email"
    SCIENTIFIC_PUBLICATION = "scientific_publication", "Scientific Publication"
    RESUME = "resume", "Resume"
    UNKNOWN = "unknown", "Unknown"


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()  # bytes
    storage_key = models.CharField(max_length=500)  # path inside bucket
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.status})"


class ClassificationResult(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name="classification"
    )
    predicted_label = models.CharField(max_length=30, choices=DocumentCategory.choices)
    confidence = models.FloatField()
    all_scores = models.JSONField(default=dict)
    model_version = models.CharField(max_length=50)
    classified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.filename} → {self.predicted_label} ({self.confidence:.2f})"


class InvoiceExtraction(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name="invoice_data"
    )
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    issuer_name = models.CharField(max_length=255, blank=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, blank=True)
    raw_text = models.TextField(blank=True)
    confidence_map = models.JSONField(default=dict)
    extracted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice extraction for {self.document.filename}"
