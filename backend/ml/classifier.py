"""
Document classifier — hybrid NLP + Computer Vision pipeline.

Retrieves a document from MinIO, runs OCR (Tesseract), extracts
TF-IDF bigram features + 33 handcrafted image features + 15 text
meta-features, and classifies via a trained ensemble model.

Interface:
    from ml.classifier import classify
    result = classify(storage_key, content_type)
"""

import io
import os
import re
import pickle
import warnings
import logging

import numpy as np
from PIL import Image
from skimage.feature import hog
from scipy.ndimage import sobel
import pytesseract

from typing import TypedDict

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── paths ────────────────────────────────────────────────────────
ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ML_DIR, "models")

# ── lazy-loaded singleton ────────────────────────────────────────
_model_data = None


def _load_model():
    """Load the trained classifier (includes TF-IDF, scaler, label encoder)."""
    global _model_data
    if _model_data is None:
        path = os.path.join(MODELS_DIR, "improved_classifier.pkl")
        with open(path, "rb") as f:
            _model_data = pickle.load(f)
        logger.info(
            "Classifier loaded: %s  categories=%s",
            _model_data["model_name"],
            list(_model_data["label_encoder"].classes_),
        )
    return _model_data


# ── MinIO helper ─────────────────────────────────────────────────
def _download_from_minio(storage_key: str) -> bytes:
    """Download a file from MinIO and return its bytes."""
    from apps.documents.storage import _s3_client
    from django.conf import settings

    client = _s3_client()
    response = client.get_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=storage_key
    )
    return response["Body"].read()


# ── text helpers ─────────────────────────────────────────────────
def _clean_ocr_text(text: str) -> str:
    """Remove OCR noise: non-ASCII garbage, collapsed whitespace, tiny tokens."""
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = re.sub(r'\s+', ' ', text)
    tokens = text.split()
    tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]
    return " ".join(tokens)


def _extract_text_meta(text: str) -> list:
    """Extract 15 hand-crafted text meta-features."""
    clean = _clean_ocr_text(text)
    words = clean.split()
    lines = text.strip().split('\n')

    n_chars = len(text)
    n_words = len(words)
    n_lines = len(lines)
    avg_word_len = float(np.mean([len(w) for w in words])) if words else 0.0
    avg_line_len = float(np.mean([len(l) for l in lines])) if lines else 0.0

    n_digits = sum(c.isdigit() for c in text)
    n_upper = sum(c.isupper() for c in text)
    n_special = sum(not c.isalnum() and not c.isspace() for c in text)
    digit_ratio = n_digits / max(n_chars, 1)
    upper_ratio = n_upper / max(n_chars, 1)
    special_ratio = n_special / max(n_chars, 1)

    text_lower = text.lower()
    invoice_kw = sum(1 for kw in ['invoice', 'total', 'amount', 'due date',
                                   'bill to', 'subtotal', 'tax', 'payment']
                     if kw in text_lower)
    email_kw = sum(1 for kw in ['from:', 'to:', 'subject:', 'sent:',
                                 'dear', 'regards', 'sincerely', 'cc:']
                   if kw in text_lower)
    resume_kw = sum(1 for kw in ['experience', 'education', 'skills',
                                  'objective', 'references', 'university',
                                  'degree', 'employment']
                    if kw in text_lower)
    sci_kw = sum(1 for kw in ['abstract', 'introduction', 'conclusion',
                               'references', 'methodology', 'results',
                               'figure', 'table', 'et al']
                 if kw in text_lower)

    return [
        n_chars, n_words, n_lines, avg_word_len, avg_line_len,
        digit_ratio, upper_ratio, special_ratio,
        invoice_kw, email_kw, resume_kw, sci_kw,
        float('@' in text),
        float('$' in text or '€' in text or '£' in text),
        float(bool(re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text))),
    ]


# ── image feature extraction ─────────────────────────────────────
def _extract_image_features(img: Image.Image, target_size=(256, 256)) -> list:
    """Extract 33 handcrafted visual features from a PIL Image."""
    img_gray = img.convert("L").resize(target_size)
    img_arr = np.array(img_gray)

    # 1. HOG features (4 summary stats)
    hog_feat = hog(
        img_arr,
        orientations=9,
        pixels_per_cell=(16, 16),
        cells_per_block=(2, 2),
        feature_vector=True,
    )
    hog_summary = [
        float(np.mean(hog_feat)),
        float(np.std(hog_feat)),
        float(np.max(hog_feat)),
        float(np.median(hog_feat)),
    ]

    # 2. Text density — binarize + 4×4 grid (1 + 16 features)
    binary = (img_arr < 128).astype(float)
    text_density = float(np.mean(binary))

    grid_size = 4
    h, w = img_arr.shape
    grid_h, grid_w = h // grid_size, w // grid_size
    grid_densities = []
    for i in range(grid_size):
        for j in range(grid_size):
            region = binary[i * grid_h:(i + 1) * grid_h, j * grid_w:(j + 1) * grid_w]
            grid_densities.append(float(np.mean(region)))

    # 3. Whitespace features (6 features)
    row_means = np.mean(binary, axis=1)
    col_means = np.mean(binary, axis=0)
    blank_rows = float(np.sum(row_means < 0.01) / len(row_means))
    blank_cols = float(np.sum(col_means < 0.01) / len(col_means))
    top_half_density = float(np.mean(binary[:h // 2, :]))
    bottom_half_density = float(np.mean(binary[h // 2:, :]))
    left_half_density = float(np.mean(binary[:, :w // 2]))
    right_half_density = float(np.mean(binary[:, w // 2:]))

    # 4. Edge features (2 features)
    edges_h = sobel(img_arr.astype(float), axis=0)
    edges_v = sobel(img_arr.astype(float), axis=1)
    edge_magnitude = np.sqrt(edges_h ** 2 + edges_v ** 2)
    edge_density = float(np.mean(edge_magnitude))
    edge_std = float(np.std(edge_magnitude))

    # 5. Margin features (4 features)
    rows_with_text = np.where(row_means > 0.01)[0]
    cols_with_text = np.where(col_means > 0.01)[0]
    if len(rows_with_text) > 0 and len(cols_with_text) > 0:
        top_margin = float(rows_with_text[0] / h)
        bottom_margin = float(1 - rows_with_text[-1] / h)
        left_margin = float(cols_with_text[0] / w)
        right_margin = float(1 - cols_with_text[-1] / w)
    else:
        top_margin = bottom_margin = left_margin = right_margin = 0.5

    # Total: 4 + 1 + 16 + 2 + 4 + 2 + 4 = 33 features
    return (
        hog_summary
        + [text_density]
        + grid_densities
        + [blank_rows, blank_cols]
        + [top_half_density, bottom_half_density, left_half_density, right_half_density]
        + [edge_density, edge_std]
        + [top_margin, bottom_margin, left_margin, right_margin]
    )


# ── OCR helpers ──────────────────────────────────────────────────
def _ocr_from_image(img: Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image and return the text."""
    return pytesseract.image_to_string(img)


def _ocr_from_pdf(file_bytes: bytes):
    """
    Extract text from a PDF.
    First tries native text extraction (pdfminer); falls back to OCR on
    the first page rendered as an image.
    Returns (text, first_page_image).
    """
    try:
        from pdfminer.high_level import extract_text as pdf_extract_text

        text = pdf_extract_text(io.BytesIO(file_bytes))
        if text and len(text.strip()) > 50:
            img = _pdf_first_page_image(file_bytes)
            return text, img
    except Exception:
        pass

    img = _pdf_first_page_image(file_bytes)
    text = pytesseract.image_to_string(img)
    return text, img


def _pdf_first_page_image(file_bytes: bytes) -> Image.Image:
    """Render the first page of a PDF as a PIL Image."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
        return img
    except ImportError:
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=200)
            return images[0]
        except ImportError:
            raise RuntimeError(
                "PDF rendering requires PyMuPDF (fitz) or pdf2image. "
                "Install one: pip install PyMuPDF  OR  pip install pdf2image"
            )


# ── public interface ─────────────────────────────────────────────
class ClassificationOutput(TypedDict):
    predicted_label: str
    confidence: float
    all_scores: dict
    model_version: str


def classify(storage_key: str, content_type: str) -> ClassificationOutput:
    """
    Classify a document stored in MinIO.

    1. Downloads the file from MinIO.
    2. Runs OCR to extract text (or native PDF text extraction).
    3. Cleans OCR text and extracts:
         - TF-IDF bigram features  (from model's stored vectorizer)
         - 33 handcrafted image features
         - 15 text meta-features
    4. Classifies with the trained ensemble model.
    5. Returns predicted label, confidence, and per-class scores.
    """
    model_data = _load_model()

    model = model_data["model"]
    scaler = model_data["scaler"]
    label_encoder = model_data["label_encoder"]
    tfidf = model_data["tfidf_vectorizer"]
    model_name = model_data["model_name"]

    # Step 1: Download from MinIO
    file_bytes = _download_from_minio(storage_key)
    logger.info("Downloaded %d bytes from MinIO: %s", len(file_bytes), storage_key)

    # Step 2: OCR + get image for visual features
    is_pdf = content_type == "application/pdf" or storage_key.lower().endswith(".pdf")

    if is_pdf:
        ocr_text, img = _ocr_from_pdf(file_bytes)
    else:
        img = Image.open(io.BytesIO(file_bytes))
        ocr_text = _ocr_from_image(img)

    logger.info("OCR extracted %d characters", len(ocr_text))

    # Step 3: Extract features
    clean_text = _clean_ocr_text(ocr_text)
    tfidf_vec = tfidf.transform([clean_text]).toarray()                    # (1, N)
    img_feat = np.array(_extract_image_features(img)).reshape(1, -1)      # (1, 33)
    meta_feat = np.array(_extract_text_meta(ocr_text)).reshape(1, -1)     # (1, 15)
    hybrid_features = np.hstack([tfidf_vec, img_feat, meta_feat])
    hybrid_scaled = scaler.transform(hybrid_features)

    # Step 4: Classify
    prediction = model.predict(hybrid_scaled)[0]
    category = str(label_encoder.inverse_transform([prediction])[0])

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(hybrid_scaled)[0]
        confidence = float(max(proba))
        all_scores = {
            str(label): round(float(p), 4)
            for label, p in zip(label_encoder.classes_, proba)
        }
    else:
        confidence = 0.0
        all_scores = {str(c): 0.0 for c in label_encoder.classes_}
        all_scores[category] = 1.0

    logger.info("Classified as '%s' (confidence=%.4f)", category, confidence)

    return ClassificationOutput(
        predicted_label=category,
        confidence=confidence,
        all_scores=all_scores,
        model_version=model_name,
    )
