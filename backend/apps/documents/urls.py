from django.urls import path
from .views import (
    DocumentListCreateView,
    DocumentDetailView,
    DocumentDownloadView,
    ClassifyView,
    ClassifyStatusView,
    ExtractionView,
)

urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<uuid:id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:id>/download/", DocumentDownloadView.as_view(), name="document-download"),
    path("documents/<uuid:id>/classify/", ClassifyView.as_view(), name="document-classify"),
    path("documents/<uuid:id>/classify/status/", ClassifyStatusView.as_view(), name="document-classify-status"),
    path("documents/<uuid:id>/extraction/", ExtractionView.as_view(), name="document-extraction"),
]
