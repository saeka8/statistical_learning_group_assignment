# Document Classification & Invoice Extraction System

**Course:** IA: Statistical Learning and Prediction — IE University

A full-stack web application that classifies scanned documents into 4 categories and extracts structured fields from invoices using traditional ML and computer vision techniques (no generative AI).

---

## Document Categories

| Category | Dataset Source | Training Samples |
|---|---|---|
| Invoice | RVL-CDIP + SROIE | 100 |
| Email | RVL-CDIP | 100 |
| Resume | RVL-CDIP | 100 |
| Scientific Publication | RVL-CDIP | 100 |

---

## ML Pipeline

### Classification (87.5% accuracy)

A hybrid NLP + Computer Vision approach:

1. **OCR** — Tesseract extracts text from scanned document images
2. **Text features** — TF-IDF vectorizer (500 features, unigrams + bigrams)
3. **Image features** — 33 handcrafted features (HOG descriptors, 4×4 text density grid, whitespace ratios, Sobel edge features, margin detection)
4. **Combined** — 533 features, StandardScaler normalised
5. **Classifier** — Random Forest (200 trees, GridSearchCV-tuned)

Ablation study: hybrid (87.5%) > text-only (82.5%) > image-only (63.8%).

**Stored models:**
```
backend/ml/models/classifier.pkl         # trained Random Forest
backend/ml/models/tfidf_vectorizer.pkl   # fitted TF-IDF vectorizer
```

### Invoice Field Extraction (~37% field completeness on SROIE test set)

When a document is classified as an invoice, a second pipeline runs automatically to extract structured fields using **YOLOv8** object detection:

1. **Page rendering** — PyMuPDF converts PDFs to images; PNGs/JPEGs loaded directly
2. **YOLO inference** — fine-tuned YOLOv8 model detects bounding boxes for 15 field classes (trained on SROIE / ICDAR 2019, ~1,000 annotated invoice images)
3. **Region OCR** — Tesseract reads text from each detected crop
4. **Post-processing** — date parsing, amount normalisation, currency detection
5. **Structured output** — invoice number, invoice date, due date, issuer name, recipient name, total amount, currency

**Stored model:**
```
backend/ml/models/yolo_invoice.pt        # YOLOv8 weights (fine-tuned on SROIE)
```

**End-to-end flow:**
```
Upload → run_classification task → ClassificationResult saved
                                 ↘ if invoice → run_extraction task → InvoiceExtraction saved
```

Both tasks run asynchronously in the background worker. The frontend polls until the document status becomes `done`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Frontend | React 19 + TypeScript + Vite |
| Task Queue | django-q2 (PostgreSQL broker — no Redis needed) |
| Database | PostgreSQL 16 |
| File Storage | MinIO (S3-compatible) via boto3 |
| Auth | JWT (djangorestframework-simplejwt) |
| Classification ML | scikit-learn, scikit-image, pytesseract, numpy, scipy |
| Extraction ML | ultralytics (YOLOv8), PyMuPDF, Pillow, pytesseract |
| Containerisation | Docker + Docker Compose |

---

## Architecture

```
┌─────────────────┐     HTTP/JWT      ┌──────────────────────┐
│  React Frontend │ ◄────────────────► │  Django REST API     │
│  (Vite + TS)    │   /api/* proxy    │  (DRF + simplejwt)   │
└─────────────────┘                   └──────────┬───────────┘
                                                  │ enqueue task
                                      ┌───────────▼───────────┐
                                      │  Django Q2 Worker     │
                                      │  (qcluster)           │
                                      └──────────┬────────────┘
                                                  │
                              ┌───────────────────┼──────────────────┐
                              ▼                   ▼                  ▼
                    ┌──────────────┐   ┌──────────────────┐  ┌──────────────┐
                    │  PostgreSQL  │   │  MinIO (S3)      │  │  ML Models   │
                    │  (metadata   │   │  (file storage)  │  │  pkl + .pt   │
                    │   + task Q)  │   └──────────────────┘  └──────────────┘
                    └──────────────┘
```

- Django Q2 uses PostgreSQL as its message broker — no Redis required
- All uploads go to MinIO; downloads use presigned URLs (300 s TTL)
- JWT access tokens (15 min) + rotating refresh tokens (7 days)
- All API responses are envelope-wrapped: `{"data": ...}` for success, `{"error": {...}}` for errors

---

## Getting Started

### Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/) (or Docker Desktop)
- `docker compose` plugin (`docker compose version` should work)
- `make` — `sudo apt install make` on Linux/WSL
- Node.js 20+ (for the frontend)

> Tesseract OCR is installed **inside the Docker image** — you do not need it on your host machine.

### First-time setup

**1. Clone and enter the directory**
```bash
git clone <repo-url>
cd statistical_learning_group_assignment
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```
Set a real value for `SECRET_KEY`. Everything else works as-is for local development.

**3. Start all services**
```bash
make up
```
Builds the Docker images (includes Tesseract + all ML dependencies) and starts PostgreSQL, MinIO, the Django API, and the background worker.

**4. Run database migrations** *(first run only)*
```bash
make migrate
```

**5. Start the frontend**
```bash
cd frontend
npm install   # first run only
npm run dev
```

Open **http://localhost:5173** — sign up, upload a document, and click **Analyze**.

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/ |
| Django admin | http://localhost:8000/admin/ |
| MinIO console | http://localhost:9001 |

---

### Everyday commands

| Command | What it does |
|---|---|
| `make up` | Build and start all containers |
| `make down` | Stop all containers |
| `make logs` | Tail logs for the API and worker |
| `make migrate` | Run pending database migrations |
| `make shell` | Open a Django shell inside the container |
| `make lint` | Run the linter (ruff) |

Watch the worker execute classification tasks in real time:
```bash
docker compose logs worker -f
```

### Without `make`

```bash
docker compose up --build -d
docker compose exec api python manage.py migrate
docker compose logs -f api worker
docker compose down
```

---

## API Endpoints

All endpoints are prefixed `/api/`. Authenticated routes require `Authorization: Bearer <access_token>`.

### Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register/` | Create account |
| `POST` | `/auth/token/` | Login → access + refresh tokens |
| `POST` | `/auth/token/refresh/` | Refresh access token |
| `GET/PATCH` | `/profile/` | Get or update profile |

### Documents

| Method | Path | Description |
|---|---|---|
| `GET` | `/documents/` | List your documents (paginated) |
| `POST` | `/documents/` | Upload a file (multipart/form-data) |
| `GET` | `/documents/{id}/` | Full detail — includes classification + extraction |
| `DELETE` | `/documents/{id}/` | Delete document and file from storage |
| `GET` | `/documents/{id}/download/` | Presigned download URL |
| `POST` | `/documents/{id}/classify/` | Re-trigger classification manually |
| `GET` | `/documents/{id}/classify/status/` | Poll classification status |
| `GET` | `/documents/{id}/extraction/` | Invoice extraction fields |

**Document status lifecycle:** `pending → processing → done` (or `error`)

---

## Project Structure

```
.
├── backend/
│   ├── apps/
│   │   ├── core/           # ApiRenderer, exception handler, pagination
│   │   ├── documents/      # Upload, classify, extract endpoints + async tasks
│   │   └── users/          # Registration, JWT auth, profiles
│   ├── ml/
│   │   ├── classifier.py   # OCR → TF-IDF + image features → Random Forest
│   │   ├── extractor.py    # YOLOv8 inference → Tesseract OCR → field mapping
│   │   └── models/         # classifier.pkl, tfidf_vectorizer.pkl, yolo_invoice.pt
│   ├── config/             # Django settings (base / development / production)
│   └── Dockerfile          # Includes Tesseract, libmagic, ML dependencies
├── frontend/
│   └── src/
│       ├── services/       # api.ts, auth.ts, documents.ts — typed backend client
│       ├── hooks/          # useAuth, useAnalysis
│       ├── components/     # Upload workspace, classification results, invoice extraction
│       └── types/          # TypeScript type definitions
├── docker-compose.yml
├── Makefile
└── .env.example
```
