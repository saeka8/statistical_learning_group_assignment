# Document Classification & Invoice Extraction System

**Course:** IA: Statistical Learning and Prediction — IE University

A full-stack web application that classifies scanned documents into 4 categories and extracts structured fields from invoices using a hybrid ML pipeline combining traditional feature engineering, image preprocessing, and transformer-based document understanding.

---

## Document Categories

| Category | Dataset Source | Samples per class |
|---|---|---|
| Invoice | RVL-CDIP (small-200) | ~200 (pre-split train/validation) |
| Email | RVL-CDIP (small-200) | ~200 (pre-split train/validation) |
| Resume | RVL-CDIP (small-200) | ~200 (pre-split train/validation) |
| Scientific Publication | RVL-CDIP (small-200) | ~200 (pre-split train/validation) |

Data is streamed directly from HuggingFace (`vaclavpechtor/rvl_cdip-small-200`) — no manual dataset preparation required.

---

## ML Pipeline

### Classification

A hybrid NLP + Computer Vision ensemble:

1. **OCR** — Tesseract extracts text from the document image
2. **Text cleaning** — removes non-ASCII noise, collapses whitespace, drops single-char tokens
3. **TF-IDF features** — 750 bigram features (sublinear TF weighting)
4. **Image features** — 33 handcrafted visual features: HOG descriptors (4 summary stats), 4×4 text density grid, whitespace ratios, Sobel edge density/std, margin measurements
5. **Text meta-features** — 15 features: character/word/line counts, digit/uppercase/special ratios, keyword hit counts for invoice/email/resume/scientific vocabulary, structural hints (currency symbols, date patterns, `@`)
6. **Combined vector** — 798 features, StandardScaler normalised
7. **Ensemble classifier** — soft-voting VotingClassifier (SVM-RBF + Logistic Regression + Random Forest), 93.8% accuracy on the RVL-CDIP small-200 held-out validation split

Ablation study: hybrid (93.8%) > text-only bigrams + meta (88.4%) > text-only unigrams (82.5%) > image-only (63.8%).

**Stored model:**
```
backend/ml/models/improved_classifier.pkl   # VotingClassifier + TF-IDF + scaler + label encoder
```

### Invoice Field Extraction

When a document is classified as an invoice, a second pipeline extracts 16 structured fields:

1. **Page rendering** — PyMuPDF converts PDFs to images at 200 DPI; PNGs/JPEGs loaded directly
2. **Image preprocessing** — `ai/extraction/preprocessing_invoice/`:
   - RGB → LAB colour space → L channel (luminance only, colour-independent)
   - CLAHE (contrast-limited adaptive histogram equalisation, clip=2.0, tile=8×8)
   - Gaussian background normalisation (σ=51) — divides by blurred background to flatten uneven illumination
3. **Full-page OCR** — single Tesseract pass on the preprocessed image returns all word tokens with bounding boxes
4. **LayoutLM extraction** — `impira/layoutlm-document-qa` (LayoutLMv2, fine-tuned for document QA) answers one targeted natural-language question per field using the original image; the model runs its own internal OCR to preserve spatial layout information
5. **Structured output** — invoice number, invoice date, due date, issuer name, recipient name, billing/shipping address, products, subtotal, VAT, VAT rate, total, discount, discount rate

**Fields extracted:**
`Invoice_Number`, `Invoice_Date`, `Due_Date`, `Issuer_Name`, `Client_Name`, `Client_Email`, `Client_Phone`, `Billing_Address`, `Shipping_Address`, `Products`, `Subtotal`, `VAT`, `VAT_Rate`, `Total`, `Discount`, `Discount_Rate`

**Model weights** — downloaded automatically on first run and cached in the `huggingface_cache` Docker volume (~1.4 GB, one-time download):
```
impira/layoutlm-document-qa   # LayoutLMv2 for document question answering
```

**End-to-end flow:**
```
Upload → run_classification task → ClassificationResult saved
                                 ↘ if invoice → run_extraction task → InvoiceExtraction saved
```

Both tasks run asynchronously in the background worker (`django-q2`). The frontend polls until the document status becomes `done`.

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
| Extraction ML | transformers (LayoutLMv2), PyMuPDF, Pillow, pytesseract, opencv-python |
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
                    │  (metadata   │   │  (file storage)  │  │  pkl + HF    │
                    │   + task Q)  │   └──────────────────┘  │  transformer │
                    └──────────────┘                         └──────────────┘
```

- Django Q2 uses PostgreSQL as its message broker — no Redis required
- All uploads go to MinIO; downloads use presigned URLs (300 s TTL)
- JWT access tokens (15 min) + rotating refresh tokens (7 days)
- All API responses are envelope-wrapped: `{"data": ...}` for success, `{"error": {...}}` for errors
- LayoutLM model weights (~1.4 GB) are downloaded from HuggingFace on first run and stored in the `huggingface_cache` named volume — subsequent rebuilds reuse the cache and do not re-download

---

## Getting Started

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

---

### Option A — Docker + Make (recommended)

**Prerequisites:** [Docker Engine](https://docs.docker.com/engine/install/) (or Docker Desktop), `make`

> Tesseract OCR, PostgreSQL, and MinIO are all provisioned inside Docker — nothing extra to install on the host.

**Start all backend services**
```bash
make up        # build images and start PostgreSQL, MinIO, API, worker
make migrate   # first run only
```

**Start the frontend**
```bash
cd frontend
npm install    # first run only
npm run dev
```

Open **http://localhost:5173**.

**Everyday commands**

| Command | What it does |
|---|---|
| `make up` | Build and start all containers |
| `make down` | Stop all containers |
| `make logs` | Tail logs for the API and worker |
| `make migrate` | Run pending database migrations |
| `make shell` | Open a Django shell inside the container |
| `make lint` | Run the linter (ruff) |

Without `make`, the equivalents are:
```bash
docker compose up --build -d
docker compose exec api python manage.py migrate
docker compose logs -f api worker
docker compose down
```

---

### Option B — Without Docker (local dev)

**Prerequisites:** Python 3.12+, Node.js 20+, PostgreSQL 16, a running MinIO instance (or any S3-compatible store), and Tesseract OCR with English + French language packs.

Install Tesseract:
```bash
# Ubuntu/Debian/WSL
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra

# macOS
brew install tesseract
```

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your local PostgreSQL and MinIO connection details, then:
```bash
python manage.py migrate
python manage.py runserver          # API on :8000
```

In a second terminal, start the background task worker:
```bash
source .venv/bin/activate
python manage.py qcluster           # Django Q2 worker
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                         # dev server on :5173
```

Open **http://localhost:5173**.

---

### Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/ |
| Django admin | http://localhost:8000/admin/ |
| MinIO console | http://localhost:9001 |

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
│   │   ├── classifier.py   # OCR → TF-IDF + image + meta features → VotingClassifier ensemble
│   │   ├── extractor.py    # preprocess → Tesseract OCR → LayoutLMv2 field extraction
│   │   └── models/         # improved_classifier.pkl
│   ├── config/             # Django settings (base / development / production)
│   └── Dockerfile          # Includes Tesseract, libmagic, ML dependencies
├── ai/
│   ├── classification/     # Classifier training scripts and trained model artefacts
│   └── extraction/
│       ├── purely_ocr/             # Shared Tesseract OCR helpers (token extraction, line grouping)
│       ├── preprocessing_invoice/  # Image preprocessing pipeline (LAB-L, CLAHE, background normalisation)
│       └── layoutlm/               # LayoutLMv2 document-QA wrapper (singleton pipeline, per-field questions)
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
