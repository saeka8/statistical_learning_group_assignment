from django.db.models import F

from .models import DocumentStatus, DocumentCategory


def apply_document_filters(queryset, request):
    status = request.query_params.get("status")
    label = request.query_params.get("label")
    query = request.query_params.get("q")
    ordering = request.query_params.get("ordering", "newest")

    if status and status in DocumentStatus.values:
        queryset = queryset.filter(status=status)

    if label and label in DocumentCategory.values:
        queryset = queryset.filter(classification__predicted_label=label)

    if query:
        queryset = queryset.filter(filename__icontains=query.strip())

    if ordering == "oldest":
        queryset = queryset.order_by("created_at")
    elif ordering == "confidence":
        queryset = queryset.order_by(
            F("classification__confidence").desc(nulls_last=True),
            "-created_at",
        )
    else:
        queryset = queryset.order_by("-created_at")

    return queryset
