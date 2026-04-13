from .models import DocumentStatus, DocumentCategory


def apply_document_filters(queryset, request):
    status = request.query_params.get("status")
    label = request.query_params.get("label")

    if status and status in DocumentStatus.values:
        queryset = queryset.filter(status=status)

    if label and label in DocumentCategory.values:
        queryset = queryset.filter(classification__predicted_label=label)

    return queryset
