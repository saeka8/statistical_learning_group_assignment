# Document Classification & Invoice Extraction System

**Course:** IA: Statistical Learning and Prediction — IE University

A full-stack web application that classifies scanned documents into 4 categories and extracts structured fields from invoices using only traditional ML techniques (no deep learning, no generative AI).

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
3. **Image features** — 33 handcrafted features (HOG descriptors, 4x4 text density grid, whitespace ratios, Sobel edge features, margin detection)
4. **Combined** — 533 features, StandardScaler normalized
5. **Classifier** — Random Forest (200 trees, GridSearchCV-tuned)

Ablation study: hybrid (87.5%) > text-only (82.5%) > image-only (63.8%).

### Invoice Extraction

Rule-based field extraction using cascading regex patterns:

- **Invoice number** — pattern matching with fallback specificity
- **Dates** — multi-format support (DD/MM/YYYY, Month DD YYYY, ISO, etc.)
- **Total amount** — 6-pass search (grand total, incl GST, subtotal filtering, comma-decimal, currency symbols)
- **Issuer/recipient** — company suffix detection + positional heuristics
- **Currency** — symbol and ISO code detection (USD, EUR, GBP, etc.)
- **Confidence map** — heuristic per-field confidence scores

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Frontend | React 19 + TypeScript + Vite |
| Task Queue | django-q2 (PostgreSQL broker) |
| Database | PostgreSQL 16 |
| File Storage | MinIO (S3-compatible) |
| Auth | JWT (djangorestframework-simplejwt) |
| ML | scikit-learn, scikit-image, pytesseract, Pillow |
| Containerization | Docker + Docker Compose |

---

## Getting Started

### Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/) (or Docker Desktop)
- `docker compose` plugin (`docker compose version` should work)
- `make` — install with `sudo apt install make` on Linux/WSL
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and on PATH

### First-time setup

**1. Clone the repo and enter the directory**
```bash
git clone <repo-url>
cd statistical_learning_group_assignment
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```
Open `.env` and set a real value for `SECRET_KEY`. Everything else can stay as-is for local development.

**3. Start all services**
```bash
make up
```
This builds the Docker images and starts PostgreSQL, MinIO, the Django API, and the background worker.

**4. Run database migrations**
```bash
make migrate
```

**5. Create an admin user** *(optional but useful)*
```bash
make createsuperuser
```

The API is now available at `http://localhost:8000/api/`
The Django admin panel is at `http://localhost:8000/admin/`
The MinIO console is at `http://localhost:9001` (login with `MINIO_USER` / `MINIO_PASSWORD` from your `.env`)

---

### Running the standalone ML pipeline

You can also run the classification pipeline directly without the web app:

```bash
pip install -r requirements.txt
cd src
python pipeline.py --demo                    # Classify sample images from demo_images/
python pipeline.py path/to/document.png      # Classify a single document
```

Requires Tesseract OCR installed and on PATH.

---

### Everyday commands

| Command | What it does |
|---|---|
| `make up` | Build and start all containers |
| `make down` | Stop all containers |
| `make logs` | Tail logs for the API and worker |
| `make migrate` | Run pending database migrations |
| `make shell` | Open a Django shell inside the container |
| `make test` | Run the test suite |
| `make lint` | Run the linter |

---

### Without make

If you don't have `make` installed you can run the underlying commands directly:

```bash
docker compose up --build -d       # make up
docker compose exec api python manage.py migrate   # make migrate
docker compose logs -f api worker  # make logs
docker compose down                # make down
```

---

## Project Structure

```
.
├── backend/                    # Django REST API
│   ├── apps/
│   │   ├── documents/          # Upload, classify, extract endpoints
│   │   └── users/              # Auth + profiles
│   ├── ml/                     # ML pipeline (no Django dependency)
│   │   ├── classifier.py       # Hybrid NLP+CV classifier
│   │   ├── extractor.py        # Regex-based invoice field extractor
│   │   └── models/             # Trained .pkl files
│   └── config/                 # Django settings
├── frontend/                   # React + TypeScript UI
│   └── src/
│       ├── components/         # UI components (upload, results, pipeline viz)
│       ├── data/               # Sample/mock data
│       └── hooks/              # State management
├── src/                        # Standalone ML pipeline
│   └── pipeline.py             # CLI tool for classification + extraction
├── models/                     # Trained model files
├── processed_data/             # TF-IDF vectorizer, OCR results, features
├── demo_images/                # Sample test images (unseen by model)
├── docker-compose.yml
└── requirements.txt            # Python deps for standalone pipeline
```
