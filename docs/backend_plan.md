# Backend Architecture Plan
## Document Classification & Information Extraction System
**Course:** IA: Statistical Learning and Prediction — IE University  
**Author:** Adrián Sánchez Morales  
**Stack:** Django REST Framework · PostgreSQL · Docker  
**Version:** 1.0

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure](#3-repository-structure)
4. [Docker & Containerization](#4-docker--containerization)
5. [Data Models](#5-data-models)
6. [API Reference](#6-api-reference)
   - 6.1 Authentication
   - 6.2 User Profiles
   - 6.3 Documents
   - 6.4 Classification Jobs
   - 6.5 Invoice Extractions
7. [Request / Response Standards](#7-request--response-standards)
8. [File Storage Strategy](#8-file-storage-strategy)
9. [ML Pipeline Integration](#9-ml-pipeline-integration)
10. [Security](#10-security)
11. [Environment Variables](#11-environment-variables)
12. [Development Workflow](#12-development-workflow)

---

## 1. Project Overview

The backend exposes a REST API that allows clients to:

- Register and authenticate users with profile management.
- Upload documents (PDF, images, plain text).
- Trigger asynchronous classification jobs that label each document into one of four categories: **Invoice**, **Email**, **Resume**, **Scientific Publication**.
- For documents classified as **Invoice**, automatically run an information-extraction pipeline and return structured fields (invoice number, date, due date, issuer, recipient, total).
- Query the results of past jobs and download processed files.

The system is designed to run 100% inside Docker containers so any developer (or server) can bring it up with a single command.

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Ecosystem match with scikit-learn, spaCy, pytesseract |
| Web Framework | Django 5.x + Django REST Framework 3.x | Batteries-included auth, ORM, serializers |
| Task Queue | django-q2 + PostgreSQL broker | Async ML jobs without blocking HTTP; uses the existing PostgreSQL as broker — no extra service needed |
| Database | PostgreSQL 16 | JSONB for extracted fields, robust transactions |
| File Storage | MinIO (S3-compatible) | Self-hosted object storage; swap to AWS S3 in prod with one env var change |
| Auth | JWT via `djangorestframework-simplejwt` | Stateless, mobile-friendly |
| Containerization | Docker + Docker Compose | Reproducible dev & prod environments |
| Reverse Proxy | Nginx (prod only) | TLS termination, static files |
| ML Libraries | scikit-learn, scikit-image, pytesseract, pdfminer.six, Pillow | No generative AI — rule-based + classical ML only |

---

## 3. Repository Structure

```
project-root/
├── docker-compose.yml          # Dev environment (all services)
├── docker-compose.prod.yml     # Production overrides
├── .env.example                # Template — never commit .env
├── Makefile                    # Shortcuts: make up, make migrate, make test
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/                 # Django project config
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── # django-q2 uses DB broker — no separate config file needed
│   │   └── wsgi.py
│   │
│   ├── apps/
│   │   ├── users/              # Auth + Profile
│   │   ├── documents/          # Upload, storage, metadata
│   │   ├── classification/     # ML classification jobs
│   │   └── extraction/         # Invoice information extraction
│   │
│   └── ml/                     # ML pipeline (no Django dependency)
│       ├── classifier.py       # Document classifier (SVM / Random Forest)
│       ├── extractor.py        # Invoice field extractor (regex + NER)
│       ├── ocr.py              # Tesseract wrapper
│       ├── preprocessor.py     # Text cleaning, feature engineering
│       └── models/             # Serialized trained models (.pkl)
│
├── nginx/
│   └── nginx.conf
│
└── docs/
    └── backend_plan.md         # This document
```

---

## 4. Docker & Containerization

### Services (docker-compose.yml)

```yaml
services:

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      retries: 5

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"   # Admin console (dev only)

  api:
    build: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.development
    env_file: .env
    volumes:
      - ./backend:/app    # Hot reload in dev
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
  worker:
    build: ./backend
    command: python manage.py qcluster
    env_file: .env
    depends_on:
      - api

volumes:
  postgres_data:
  minio_data:
```

### One-command startup

```bash
cp .env.example .env        # Fill in secrets
make up                     # docker compose up --build -d
make migrate                # python manage.py migrate
make createsuperuser        # Create first admin
```

---

## 5. Data Models

### 5.1 User & Profile

```python
# apps/users/models.py

class UserProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=100, blank=True)
    avatar_url  = models.URLField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
```

### 5.2 Document

```python
# apps/documents/models.py

class DocumentCategory(models.TextChoices):
    INVOICE          = "invoice",          "Invoice"
    EMAIL            = "email",            "Email"
    SCIENTIFIC_PUBLICATION = "scientific_publication", "Scientific Publication"
    RESUME           = "resume",           "Resume"
    UNKNOWN          = "unknown",          "Unknown"

class Document(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4)
    owner        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    filename     = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)   # e.g. application/pdf
    file_size    = models.PositiveIntegerField()       # bytes
    storage_key  = models.CharField(max_length=500)   # path inside MinIO bucket
    status       = models.CharField(
        max_length=20,
        choices=[("pending","Pending"),("processing","Processing"),
                 ("done","Done"),("error","Error")],
        default="pending"
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
```

### 5.3 ClassificationResult

```python
class ClassificationResult(models.Model):
    document       = models.OneToOneField(Document, on_delete=models.CASCADE,
                                          related_name="classification")
    predicted_label = models.CharField(max_length=30, choices=DocumentCategory.choices)
    confidence      = models.FloatField()                    # 0.0 – 1.0
    all_scores      = models.JSONField(default=dict)         # {"invoice": 0.91, ...}
    model_version   = models.CharField(max_length=50)        # e.g. "svm_tfidf_v2"
    classified_at   = models.DateTimeField(auto_now_add=True)
```

### 5.4 InvoiceExtraction

```python
class InvoiceExtraction(models.Model):
    document        = models.OneToOneField(Document, on_delete=models.CASCADE,
                                           related_name="invoice_data")
    invoice_number  = models.CharField(max_length=100, blank=True)
    invoice_date    = models.DateField(null=True, blank=True)
    due_date        = models.DateField(null=True, blank=True)
    issuer_name     = models.CharField(max_length=255, blank=True)
    recipient_name  = models.CharField(max_length=255, blank=True)
    total_amount    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency        = models.CharField(max_length=10, blank=True)   # ISO 4217, e.g. EUR
    raw_text        = models.TextField(blank=True)                  # OCR / parsed text
    confidence_map  = models.JSONField(default=dict)                # per-field confidence
    extracted_at    = models.DateTimeField(auto_now_add=True)
```

---

## 6. API Reference

### Base URL

```
http://localhost:8000/api/v1/
```

All endpoints return `application/json`. All authenticated endpoints require:

```
Authorization: Bearer <access_token>
```

---

### 6.1 Authentication

#### `POST /api/v1/auth/register/`

Create a new user account.

**Request body:**

```json
{
  "username": "adriansm",
  "email": "adrian@example.com",
  "password": "StrongPass123!",
  "display_name": "Adrián"
}
```

**201 Created:**

```json
{
  "id": 1,
  "username": "adriansm",
  "email": "adrian@example.com",
  "profile": {
    "display_name": "Adrián",
    "avatar_url": ""
  },
  "tokens": {
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>"
  }
}
```

---

#### `POST /api/v1/auth/token/`

Obtain JWT tokens.

**Request body:**

```json
{
  "username": "adriansm",
  "password": "StrongPass123!"
}
```

**200 OK:**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

---

#### `POST /api/v1/auth/token/refresh/`

Refresh an expired access token.

**Request body:**

```json
{ "refresh": "<jwt_refresh_token>" }
```

**200 OK:**

```json
{ "access": "<new_jwt_access_token>" }
```

---

### 6.2 User Profiles

#### `GET /api/v1/profile/`  *(auth required)*

Returns the authenticated user's profile.

**200 OK:**

```json
{
  "id": 1,
  "username": "adriansm",
  "email": "adrian@example.com",
  "profile": {
    "display_name": "Adrián",
    "avatar_url": "https://minio.local/avatars/1.png",
    "created_at": "2026-04-09T10:00:00Z"
  }
}
```

---

#### `PATCH /api/v1/profile/`  *(auth required)*

Update profile fields (partial update).

**Request body (all fields optional):**

```json
{
  "display_name": "Adrián S.",
  "email": "new@example.com"
}
```

**200 OK:** Returns updated profile object (same schema as GET).

---

### 6.3 Documents

#### `POST /api/v1/documents/`  *(auth required)*

Upload a document. Uses `multipart/form-data`.

**Request:**

```
Content-Type: multipart/form-data

file: <binary file>
```

Accepted MIME types: `application/pdf`, `image/png`, `image/jpeg`, `text/plain`.  
Max file size: **20 MB** (configurable via `MAX_UPLOAD_MB` env var).

**201 Created:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "invoice_march.pdf",
  "content_type": "application/pdf",
  "file_size": 204800,
  "status": "pending",
  "created_at": "2026-04-09T11:00:00Z",
  "classification": null,
  "invoice_data": null
}
```

After a successful upload, the server automatically enqueues a **classification job** (see §9).

---

#### `GET /api/v1/documents/`  *(auth required)*

List all documents owned by the authenticated user.

**Query parameters:**

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter by `pending`, `processing`, `done`, `error` |
| `label` | string | Filter by classification label, e.g. `invoice` |
| `page` | int | Page number (default 1) |
| `page_size` | int | Items per page (default 20, max 100) |

**200 OK:**

```json
{
  "count": 42,
  "next": "/api/v1/documents/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-...",
      "filename": "invoice_march.pdf",
      "status": "done",
      "label": "invoice",
      "confidence": 0.94,
      "created_at": "2026-04-09T11:00:00Z"
    }
  ]
}
```

---

#### `GET /api/v1/documents/{id}/`  *(auth required)*

Retrieve full detail for a single document.

**200 OK:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "invoice_march.pdf",
  "content_type": "application/pdf",
  "file_size": 204800,
  "status": "done",
  "created_at": "2026-04-09T11:00:00Z",
  "classification": {
    "predicted_label": "invoice",
    "confidence": 0.94,
    "all_scores": {
      "invoice": 0.94,
      "email": 0.03,
      "scientific_publication": 0.02,
      "resume": 0.01
    },
    "model_version": "svm_tfidf_v2",
    "classified_at": "2026-04-09T11:00:45Z"
  },
  "invoice_data": {
    "invoice_number": "INV-2026-0312",
    "invoice_date": "2026-03-12",
    "due_date": "2026-04-12",
    "issuer_name": "Acme Corp SL",
    "recipient_name": "IE University",
    "total_amount": "12500.00",
    "currency": "EUR",
    "confidence_map": {
      "invoice_number": 0.98,
      "invoice_date": 0.95,
      "due_date": 0.90,
      "issuer_name": 0.87,
      "recipient_name": 0.82,
      "total_amount": 0.99
    },
    "extracted_at": "2026-04-09T11:01:02Z"
  }
}
```

`invoice_data` is `null` for non-invoice documents.

---

#### `GET /api/v1/documents/{id}/download/`  *(auth required)*

Returns a short-lived pre-signed URL to download the original file.

**200 OK:**

```json
{
  "url": "https://minio.local/documents/550e8400-...?X-Amz-Expires=300&...",
  "expires_in": 300
}
```

---

#### `DELETE /api/v1/documents/{id}/`  *(auth required)*

Deletes the document record and its file from storage.

**204 No Content**

---

### 6.4 Classification Jobs

Classification is triggered automatically on upload. These endpoints allow manual re-trigger and status polling.

#### `POST /api/v1/documents/{id}/classify/`  *(auth required)*

Manually re-trigger classification (e.g. after a model update).

**202 Accepted:**

```json
{
  "job_id": "django-q-task-uuid",
  "message": "Classification job enqueued."
}
```

---

#### `GET /api/v1/documents/{id}/classify/status/`  *(auth required)*

Poll the status of the classification job.

**200 OK:**

```json
{
  "document_id": "550e8400-...",
  "status": "processing",
  "started_at": "2026-04-09T11:00:10Z",
  "completed_at": null
}
```

Possible `status` values: `pending`, `processing`, `done`, `error`.

---

### 6.5 Invoice Extractions

#### `GET /api/v1/documents/{id}/extraction/`  *(auth required)*

Returns just the extracted invoice fields for a document classified as an invoice.

**200 OK:** Returns the `invoice_data` object shown in §6.3.

**404** if the document is not classified as an invoice.

---

## 7. Request / Response Standards

### Envelope

Every response follows this shape:

**Success:**
```json
{
  "data": { ... }
}
```

**Error:**
```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "No document with the given ID exists for this user.",
    "field_errors": {}
  }
}
```

`field_errors` is populated for validation errors, mapping field names to lists of messages:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data.",
    "field_errors": {
      "email": ["Enter a valid email address."],
      "password": ["This field is required."]
    }
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success (GET, PATCH) |
| 201 | Resource created (POST) |
| 202 | Accepted for async processing |
| 204 | Deleted (no body) |
| 400 | Validation error |
| 401 | Missing or invalid token |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 413 | File too large |
| 415 | Unsupported media type |
| 422 | Business logic error (e.g., re-classify a doc still processing) |
| 500 | Internal server error |

### Dates and Times

- All timestamps use **ISO 8601** with UTC timezone: `"2026-04-09T11:00:00Z"`
- All dates (invoice_date, due_date) use `"YYYY-MM-DD"`: `"2026-03-12"`

### Pagination

All list endpoints use **cursor-free page-number pagination**:

```json
{
  "count": 100,
  "next": "/api/v1/documents/?page=3",
  "previous": "/api/v1/documents/?page=1",
  "results": [ ... ]
}
```

### Versioning

URL-based versioning: `/api/v1/`. When breaking changes are needed, `/api/v2/` is introduced and `v1` is deprecated with a sunset header.

---

## 8. File Storage Strategy

Files are stored in **MinIO** (S3-compatible), never on the Django container's filesystem.

### Bucket layout

```
documents-bucket/
└── {user_id}/
    └── {document_uuid}/{original_filename}
```

### Upload flow

```
Client → POST /api/v1/documents/ (multipart)
       → Django validates MIME type & size
       → File streamed directly to MinIO via boto3
       → Document record saved with storage_key
       → django-q2 task enqueued
       → 201 response returned immediately
```

### Download flow

```
Client → GET /api/v1/documents/{id}/download/
       → Django checks ownership
       → Generates pre-signed MinIO URL (TTL: 5 min)
       → Returns URL to client
       → Client downloads directly from MinIO
```

This keeps large binary data out of Django's memory on downloads.

---

## 9. ML Pipeline Integration

The ML pipeline lives in `backend/ml/` — pure Python, no Django imports — so it can be tested and updated independently.

### Classification pipeline (`ml/classifier.py`)

```
raw file (downloaded from MinIO)
  └→ OCR (if image/scanned PDF) via pytesseract
  └→ Text extraction (if native PDF) via pdfminer.six
  └→ TF-IDF text features (500 features, unigrams + bigrams)
  └→ Handcrafted image features (33 features: HOG, text density, edges, margins)
  └→ Combined hybrid feature vector (533 features)
  └→ StandardScaler normalization
  └→ Random Forest classifier (200 trees, GridSearchCV-tuned)
  └→ (label, confidence, all_scores)
  └→ Save ClassificationResult to DB
  └→ If label == "invoice": enqueue extraction task
```

Trained on 400 documents (100 per category) from the RVL-CDIP dataset.
Achieves **87.5% accuracy** on held-out test data. Ablation study shows
hybrid (NLP + CV) outperforms text-only (82.5%) and image-only (63.8%).

### Extraction pipeline (`ml/extractor.py`)

```
raw file (downloaded from MinIO)
  └→ OCR text extraction via pytesseract
  └→ Cascading regex patterns (6 passes for totals, multi-format dates)
  └→ Company name detection via suffix matching + positional heuristics
  └→ Currency detection via symbol/code regex (USD, EUR, GBP, etc.)
  └→ Heuristic confidence scoring → confidence_map per field
  └→ Save InvoiceExtraction to DB (with raw_text and confidence_map)
  └→ Update Document.status = "done"
```

Tested on the SROIE dataset (626 annotated invoice images). Extraction
accuracy is bounded by OCR quality — ground-truth totals only appear in
~53% of OCR outputs, giving a theoretical effective ceiling of ~69%.

### Model versioning

Trained model files (`.pkl`) are stored in `ml/models/` and referenced by a `MODEL_VERSION` env var. To update the classifier, train a new model, place it in `ml/models/`, bump the version, and redeploy the worker container. No database migration needed.

---

## 10. Security

| Concern | Approach |
|---|---|
| Authentication | JWT access tokens (15 min TTL) + refresh tokens (7 day TTL, rotation enabled) |
| Authorization | Every queryset is filtered by `owner=request.user` — users cannot access other users' documents |
| File validation | MIME type checked server-side (python-magic), not just by extension |
| File size | Enforced at Django level before streaming to MinIO |
| Secrets | All secrets in `.env`, never in source code; `.env.example` has no real values |
| HTTPS | Nginx handles TLS in production; dev uses HTTP only on localhost |
| CORS | `django-cors-headers` with explicit `CORS_ALLOWED_ORIGINS` list |
| SQL injection | Django ORM parameterized queries throughout |
| Rate limiting | `django-ratelimit` on auth endpoints (10 req/min per IP) |
| Dependencies | `pip-audit` in CI pipeline to check for known CVEs |

---

## 11. Environment Variables

Copy `.env.example` to `.env` and fill in values. **Never commit `.env`.**

```bash
# Django
SECRET_KEY=your-very-long-random-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings.development

# Database
DB_NAME=docclassify
DB_USER=postgres
DB_PASSWORD=changeme
DB_HOST=db
DB_PORT=5432

# django-q2 (uses PostgreSQL as broker — no extra config needed)

# MinIO / S3
MINIO_ENDPOINT=minio:9000
MINIO_USER=minioadmin
MINIO_PASSWORD=changeme
MINIO_BUCKET=documents-bucket
MINIO_USE_HTTPS=False   # True in production

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# ML
MODEL_VERSION=svm_tfidf_v2
MAX_UPLOAD_MB=20
```

---

## 12. Development Workflow

### Starting the dev environment

```bash
make up           # Build and start all containers
make migrate      # Run DB migrations
make seed         # (optional) Load sample documents for testing
```

### Running tests

```bash
make test         # pytest inside the api container
make test-cov     # pytest with coverage report
```

### Makefile targets reference

```makefile
up:        docker compose up --build -d
down:      docker compose down
logs:      docker compose logs -f api worker
migrate:   docker compose exec api python manage.py migrate
shell:     docker compose exec api python manage.py shell_plus
test:      docker compose exec api pytest
test-cov:  docker compose exec api pytest --cov=apps --cov-report=term-missing
lint:      docker compose exec api ruff check .
format:    docker compose exec api ruff format .
```

### Adding a new app

```bash
docker compose exec api python manage.py startapp myapp apps/myapp
```

Register it in `config/settings/base.py` under `INSTALLED_APPS`.

### Updating the classifier model

1. Train the new model locally (or in a notebook).
2. Save as `backend/ml/models/svm_tfidf_v3.pkl`.
3. Update `MODEL_VERSION=svm_tfidf_v3` in `.env`.
4. Restart the worker: `docker compose restart worker`.

---

*End of document. Last updated: April 2026.*
