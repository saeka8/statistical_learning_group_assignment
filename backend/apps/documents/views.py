import magic
from django.conf import settings
from django.db.models import Count, Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, DocumentStatus, InvoiceExtraction
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    InvoiceExtractionSerializer,
    WorkspaceSummarySerializer,
)
from .storage import upload_file, delete_file, generate_presigned_url
from .filters import apply_document_filters
from apps.core.pagination import StandardPagination


class DocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Document.objects.filter(owner=self.request.user).select_related(
            "classification", "invoice_data"
        )
        return apply_document_filters(qs, self.request)

    def get_serializer_class(self):
        return DocumentListSerializer

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "No file provided.", "field_errors": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > settings.MAX_UPLOAD_BYTES:
            return Response(
                {"error": {"code": "FILE_TOO_LARGE", "message": f"Max upload size is {settings.MAX_UPLOAD_MB} MB.", "field_errors": {}}},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        mime = magic.from_buffer(uploaded_file.read(2048), mime=True)
        uploaded_file.seek(0)
        if mime not in settings.ALLOWED_UPLOAD_CONTENT_TYPES:
            return Response(
                {"error": {"code": "UNSUPPORTED_MEDIA_TYPE", "message": f"File type '{mime}' is not supported.", "field_errors": {}}},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        storage_key = f"{request.user.pk}/{uploaded_file.name}"
        upload_file(uploaded_file, storage_key)

        doc = Document.objects.create(
            owner=request.user,
            filename=uploaded_file.name,
            content_type=mime,
            file_size=uploaded_file.size,
            storage_key=storage_key,
        )

        from django_q.tasks import async_task
        async_task("apps.documents.tasks.run_classification", str(doc.id))

        serializer = DocumentDetailSerializer(doc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).select_related(
            "classification", "invoice_data"
        )

    def destroy(self, request, *args, **kwargs):
        doc = self.get_object()
        delete_file(doc.storage_key)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Document.objects.filter(owner=request.user).select_related(
            "classification",
            "invoice_data",
        )

        totals = {
            "uploads": queryset.count(),
            "processed": queryset.filter(status=DocumentStatus.DONE).count(),
            "errors": queryset.filter(status=DocumentStatus.ERROR).count(),
            "invoices": queryset.filter(classification__predicted_label="invoice").count(),
        }

        dominant = (
            queryset.filter(classification__isnull=False)
            .values("classification__predicted_label")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )
        dominant_label = None
        if dominant:
            dominant_label = {
                "value": dominant["classification__predicted_label"],
                "count": dominant["total"],
            }

        invoice_total = (
            queryset.filter(invoice_data__total_amount__isnull=False)
            .aggregate(total=Sum("invoice_data__total_amount"))
            .get("total")
        )

        recent_activity = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status,
                "label": getattr(getattr(doc, "classification", None), "predicted_label", None),
                "confidence": getattr(getattr(doc, "classification", None), "confidence", None),
                "created_at": doc.created_at,
            }
            for doc in queryset[:5]
        ]

        serializer = WorkspaceSummarySerializer(
            {
                "totals": totals,
                "dominant_label": dominant_label,
                "recent_invoice_total": str(invoice_total) if invoice_total is not None else None,
                "recent_activity": recent_activity,
            }
        )
        return Response(serializer.data)


class DocumentDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        try:
            doc = Document.objects.get(id=id, owner=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Document not found.", "field_errors": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        url = generate_presigned_url(doc.storage_key, expires_in=300)
        return Response({"url": url, "expires_in": 300})


class ClassifyView(APIView):
    """POST /api/documents/{id}/classify/ — manually re-trigger classification."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            doc = Document.objects.get(id=id, owner=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Document not found.", "field_errors": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if doc.status == DocumentStatus.PROCESSING:
            return Response(
                {"error": {"code": "UNPROCESSABLE", "message": "Document is already being processed.", "field_errors": {}}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        from django_q.tasks import async_task
        task = async_task("apps.documents.tasks.run_classification", str(doc.id))

        return Response(
            {"job_id": task, "message": "Classification job enqueued."},
            status=status.HTTP_202_ACCEPTED,
        )


class ClassifyStatusView(APIView):
    """GET /api/documents/{id}/classify/status/ — poll classification status."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        try:
            doc = Document.objects.get(id=id, owner=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Document not found.", "field_errors": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )

        classified_at = None
        if hasattr(doc, "classification"):
            classified_at = doc.classification.classified_at

        return Response({
            "document_id": str(doc.id),
            "status": doc.status,
            "started_at": None,
            "completed_at": classified_at,
        })


class ExtractionView(APIView):
    """GET /api/documents/{id}/extraction/ — return extracted invoice fields."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        try:
            doc = Document.objects.get(id=id, owner=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Document not found.", "field_errors": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            extraction = doc.invoice_data
        except InvoiceExtraction.DoesNotExist:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "No invoice extraction available for this document.", "field_errors": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(InvoiceExtractionSerializer(extraction).data)
