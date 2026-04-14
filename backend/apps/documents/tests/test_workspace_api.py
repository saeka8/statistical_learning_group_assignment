from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.documents.models import (
    ClassificationResult,
    Document,
    DocumentCategory,
    DocumentStatus,
    InvoiceExtraction,
)


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_document(owner, filename, status, label=None, confidence=0.0, total_amount=None):
    document = Document.objects.create(
        owner=owner,
        filename=filename,
        content_type="application/pdf",
        file_size=1024,
        storage_key=f"{owner.pk}/{filename}",
        status=status,
    )

    if label is not None:
        ClassificationResult.objects.create(
            document=document,
            predicted_label=label,
            confidence=confidence,
            all_scores={label: confidence},
            model_version="test-model",
        )

    if total_amount is not None:
        InvoiceExtraction.objects.create(
            document=document,
            total_amount=Decimal(str(total_amount)),
            confidence_map={},
        )

    return document


def set_created_at(document, when):
    Document.objects.filter(pk=document.pk).update(created_at=when, updated_at=when)
    document.created_at = when
    document.updated_at = when
    return document


class WorkspaceApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")
        self.other_user = User.objects.create_user(username="bob", password="password123")

    def test_workspace_summary_returns_user_practical_stats_only(self):
        now = timezone.now()

        oldest = set_created_at(
            make_document(
                self.user,
                "invoice-a.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.91,
                total_amount="100.00",
            ),
            now - timedelta(minutes=5),
        )
        middle = set_created_at(
            make_document(
                self.user,
                "invoice-b.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.97,
                total_amount="105.50",
            ),
            now - timedelta(minutes=4),
        )
        set_created_at(
            make_document(
                self.user,
                "resume.pdf",
                DocumentStatus.ERROR,
                label=DocumentCategory.RESUME,
                confidence=0.88,
            ),
            now - timedelta(minutes=3),
        )
        set_created_at(
            make_document(
                self.user,
                "invoice-c.pdf",
                DocumentStatus.PENDING,
                label=DocumentCategory.INVOICE,
                confidence=0.73,
            ),
            now - timedelta(minutes=2),
        )
        set_created_at(
            make_document(
                self.other_user,
                "other-invoice.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.99,
                total_amount="999.99",
            ),
            now - timedelta(minutes=1),
        )
        newest = set_created_at(
            make_document(
                self.user,
                "draft.pdf",
                DocumentStatus.PENDING,
            ),
            now,
        )

        response = auth_client(self.user).get("/api/workspace/summary/")

        self.assertEqual(response.status_code, 200)
        payload = response.data

        self.assertEqual(
            payload["totals"],
            {"uploads": 5, "processed": 2, "errors": 1, "invoices": 3},
        )
        self.assertEqual(payload["dominant_label"]["value"], "invoice")
        self.assertEqual(payload["recent_invoice_total"], "205.50")
        self.assertEqual(len(payload["recent_activity"]), 5)
        self.assertEqual(
            [item["filename"] for item in payload["recent_activity"]],
            [newest.filename, "invoice-c.pdf", "resume.pdf", middle.filename, oldest.filename],
        )

    def test_document_list_defaults_to_newest_ordering(self):
        now = timezone.now()

        set_created_at(
            make_document(
                self.user,
                "invoice-a.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.91,
            ),
            now - timedelta(minutes=2),
        )
        set_created_at(
            make_document(
                self.user,
                "invoice-b.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.97,
            ),
            now - timedelta(minutes=1),
        )
        set_created_at(
            make_document(
                self.user,
                "resume.pdf",
                DocumentStatus.ERROR,
                label=DocumentCategory.RESUME,
                confidence=0.88,
            ),
            now,
        )

        response = auth_client(self.user).get("/api/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["filename"] for item in response.data["results"]],
            ["resume.pdf", "invoice-b.pdf", "invoice-a.pdf"],
        )

    def test_document_list_supports_query_filters_and_confidence_ordering(self):
        now = timezone.now()

        set_created_at(
            make_document(
                self.user,
                "invoice-a.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.91,
            ),
            now - timedelta(minutes=3),
        )
        set_created_at(
            make_document(
                self.user,
                "invoice-b.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.97,
            ),
            now - timedelta(minutes=2),
        )
        set_created_at(
            make_document(
                self.user,
                "resume.pdf",
                DocumentStatus.ERROR,
                label=DocumentCategory.RESUME,
                confidence=0.88,
            ),
            now + timedelta(minutes=2),
        )
        set_created_at(
            make_document(
                self.user,
                "draft.pdf",
                DocumentStatus.PENDING,
            ),
            now + timedelta(minutes=3),
        )
        set_created_at(
            make_document(
                self.other_user,
                "other-invoice.pdf",
                DocumentStatus.DONE,
                label=DocumentCategory.INVOICE,
                confidence=0.99,
            ),
            now + timedelta(minutes=4),
        )

        search_response = auth_client(self.user).get("/api/documents/?q=invoice-a")
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual([item["filename"] for item in search_response.data["results"]], ["invoice-a.pdf"])

        status_response = auth_client(self.user).get("/api/documents/?status=error")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual([item["filename"] for item in status_response.data["results"]], ["resume.pdf"])

        label_response = auth_client(self.user).get("/api/documents/?label=invoice")
        self.assertEqual(label_response.status_code, 200)
        self.assertEqual(
            [item["filename"] for item in label_response.data["results"]],
            ["invoice-b.pdf", "invoice-a.pdf"],
        )

        oldest_response = auth_client(self.user).get("/api/documents/?ordering=oldest")
        self.assertEqual(oldest_response.status_code, 200)
        self.assertEqual(
            [item["filename"] for item in oldest_response.data["results"]],
            ["invoice-a.pdf", "invoice-b.pdf", "resume.pdf", "draft.pdf"],
        )

        newest_response = auth_client(self.user).get("/api/documents/")
        self.assertEqual(newest_response.status_code, 200)
        self.assertEqual(
            [item["filename"] for item in newest_response.data["results"]],
            ["draft.pdf", "resume.pdf", "invoice-b.pdf", "invoice-a.pdf"],
        )

        confidence_response = auth_client(self.user).get("/api/documents/?ordering=confidence")
        self.assertEqual(confidence_response.status_code, 200)
        self.assertEqual(
            [item["filename"] for item in confidence_response.data["results"]],
            ["invoice-b.pdf", "invoice-a.pdf", "resume.pdf", "draft.pdf"],
        )
