"""
Improved Document Classifier
=============================
Improvements over baseline:
  1. Text cleaning (OCR noise removal)
  2. TF-IDF with bigrams
  3. Extra text meta-features (doc length, special chars, keyword hits)
  4. Voting ensemble (SVM + LR)

Usage:
    python improved_classifier.py
"""

import os
import re
import pickle
import warnings
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix
)

warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, "trained_models", "features_cache.pkl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "trained_models")


# ── text cleaning ────────────────────────────────────────────
def clean_ocr_text(text):
    """Clean OCR noise from extracted text."""
    # Remove non-ASCII garbage
    text = text.encode("ascii", errors="ignore").decode("ascii")
    # Collapse multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove very short tokens (OCR artifacts like 'x', '|', etc.)
    tokens = text.split()
    tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]
    return " ".join(tokens)


# ── extra text meta-features ─────────────────────────────────
def extract_text_meta(text):
    """Extract 15 hand-crafted text meta-features."""
    clean = clean_ocr_text(text)
    words = clean.split()
    lines = text.strip().split('\n')

    # Basic stats
    n_chars = len(text)
    n_words = len(words)
    n_lines = len(lines)
    avg_word_len = np.mean([len(w) for w in words]) if words else 0
    avg_line_len = np.mean([len(l) for l in lines]) if lines else 0

    # Character ratios
    n_digits = sum(c.isdigit() for c in text)
    n_upper = sum(c.isupper() for c in text)
    n_special = sum(not c.isalnum() and not c.isspace() for c in text)
    digit_ratio = n_digits / max(n_chars, 1)
    upper_ratio = n_upper / max(n_chars, 1)
    special_ratio = n_special / max(n_chars, 1)

    # Keyword indicators (binary or count-based)
    text_lower = text.lower()

    # Invoice keywords
    invoice_kw = sum(1 for kw in ['invoice', 'total', 'amount', 'due date',
                                   'bill to', 'subtotal', 'tax', 'payment']
                     if kw in text_lower)

    # Email keywords
    email_kw = sum(1 for kw in ['from:', 'to:', 'subject:', 'sent:',
                                 'dear', 'regards', 'sincerely', 'cc:']
                   if kw in text_lower)

    # Resume keywords
    resume_kw = sum(1 for kw in ['experience', 'education', 'skills',
                                  'objective', 'references', 'university',
                                  'degree', 'employment']
                    if kw in text_lower)

    # Scientific keywords
    sci_kw = sum(1 for kw in ['abstract', 'introduction', 'conclusion',
                               'references', 'methodology', 'results',
                               'figure', 'table', 'et al']
                 if kw in text_lower)

    return [
        n_chars, n_words, n_lines, avg_word_len, avg_line_len,
        digit_ratio, upper_ratio, special_ratio,
        invoice_kw, email_kw, resume_kw, sci_kw,
        # Structural hints
        float('@' in text),          # email indicator
        float('$' in text or '€' in text or '£' in text),  # currency
        float(bool(re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text))),  # dates
    ]


# ── main ─────────────────────────────────────────────────────
def main():
    print("Loading cached features...")
    with open(CACHE_PATH, "rb") as f:
        cache = pickle.load(f)

    train_texts = cache["train_texts"]
    train_img = cache["train_img"]
    train_labels = cache["train_labels"]
    val_texts = cache["val_texts"]
    val_img = cache["val_img"]
    val_labels = cache["val_labels"]

    le = LabelEncoder()
    y_train = le.fit_transform(train_labels)
    y_val = le.transform(val_labels)

    # ── Clean texts ──
    print("Cleaning OCR text...")
    train_clean = [clean_ocr_text(t) for t in train_texts]
    val_clean = [clean_ocr_text(t) for t in val_texts]

    # ── Extract text meta-features ──
    print("Extracting text meta-features...")
    train_meta = np.array([extract_text_meta(t) for t in train_texts])
    val_meta = np.array([extract_text_meta(t) for t in val_texts])

    # ── Build feature variants ──
    configs = {}

    # Config A: Cleaned TF-IDF unigrams (500) + image (33) — baseline with clean text
    tfidf_uni = TfidfVectorizer(max_features=500, stop_words="english", sublinear_tf=True)
    tr_tfidf_uni = tfidf_uni.fit_transform(train_clean).toarray()
    va_tfidf_uni = tfidf_uni.transform(val_clean).toarray()
    configs["A: Clean unigrams + img"] = (
        np.hstack([tr_tfidf_uni, train_img]),
        np.hstack([va_tfidf_uni, val_img]),
        tfidf_uni
    )

    # Config B: Cleaned TF-IDF bigrams (500) + image (33)
    tfidf_bi = TfidfVectorizer(max_features=500, stop_words="english",
                                sublinear_tf=True, ngram_range=(1, 2))
    tr_tfidf_bi = tfidf_bi.fit_transform(train_clean).toarray()
    va_tfidf_bi = tfidf_bi.transform(val_clean).toarray()
    configs["B: Bigrams + img"] = (
        np.hstack([tr_tfidf_bi, train_img]),
        np.hstack([va_tfidf_bi, val_img]),
        tfidf_bi
    )

    # Config C: Bigrams (500) + image (33) + meta (15) = 548
    configs["C: Bigrams + img + meta"] = (
        np.hstack([tr_tfidf_bi, train_img, train_meta]),
        np.hstack([va_tfidf_bi, val_img, val_meta]),
        tfidf_bi
    )

    # Config D: Bigrams (750) + image (33) + meta (15)
    tfidf_bi2 = TfidfVectorizer(max_features=750, stop_words="english",
                                 sublinear_tf=True, ngram_range=(1, 2))
    tr_tfidf_bi2 = tfidf_bi2.fit_transform(train_clean).toarray()
    va_tfidf_bi2 = tfidf_bi2.transform(val_clean).toarray()
    configs["D: Bigrams750 + img + meta"] = (
        np.hstack([tr_tfidf_bi2, train_img, train_meta]),
        np.hstack([va_tfidf_bi2, val_img, val_meta]),
        tfidf_bi2
    )

    print(f"\n{'=' * 75}")
    print("IMPROVED CLASSIFIER EXPERIMENTS")
    print(f"{'=' * 75}")

    best_acc = 0
    best_config = None
    best_model = None
    best_scaler = None
    best_tfidf = None

    for config_name, (X_tr, X_va, tfidf_obj) in configs.items():
        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr)
        X_va_s = scaler.transform(X_va)

        print(f"\n--- {config_name} (features: {X_tr.shape[1]}) ---")

        # SVM RBF
        svm = SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=42)
        svm.fit(X_tr_s, y_train)
        acc_svm = accuracy_score(y_val, svm.predict(X_va_s))
        f1_svm = f1_score(y_val, svm.predict(X_va_s), average="weighted")

        # Logistic Regression
        lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
        lr.fit(X_tr_s, y_train)
        acc_lr = accuracy_score(y_val, lr.predict(X_va_s))

        # Voting ensemble
        ensemble = VotingClassifier(
            estimators=[
                ("svm", SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=42)),
                ("lr", LogisticRegression(max_iter=1000, C=1.0, random_state=42)),
                ("rf", RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)),
            ],
            voting="soft"
        )
        ensemble.fit(X_tr_s, y_train)
        acc_ens = accuracy_score(y_val, ensemble.predict(X_va_s))
        f1_ens = f1_score(y_val, ensemble.predict(X_va_s), average="weighted")

        print(f"  SVM RBF:    {acc_svm:.1%} acc / {f1_svm:.4f} F1")
        print(f"  Log Reg:    {acc_lr:.1%} acc")
        print(f"  Ensemble:   {acc_ens:.1%} acc / {f1_ens:.4f} F1")

        # Track best
        for model_obj, acc, name in [(svm, acc_svm, "SVM"), (ensemble, acc_ens, "Ensemble")]:
            if acc > best_acc:
                best_acc = acc
                best_config = f"{config_name} / {name}"
                best_model = model_obj
                best_scaler = scaler
                best_tfidf = tfidf_obj

    # ── Final report ──
    print(f"\n{'=' * 75}")
    print(f"BEST: {best_config} — Accuracy: {best_acc:.1%}")
    print(f"{'=' * 75}")

    # Re-evaluate best for full report
    X_tr_best, X_va_best, _ = configs[best_config.split(" / ")[0]]
    X_va_s = best_scaler.transform(X_va_best)
    y_pred = best_model.predict(X_va_s)

    print(classification_report(y_val, y_pred, target_names=le.classes_))

    print("Confusion Matrix:")
    cm = confusion_matrix(y_val, y_pred)
    print(f"{'':>25s}", end="")
    for c in le.classes_:
        print(f"{c[:10]:>12s}", end="")
    print()
    for i, row in enumerate(cm):
        print(f"{le.classes_[i]:>25s}", end="")
        for val in row:
            print(f"{val:>12d}", end="")
        print()

    # Save
    model_data = {
        "model": best_model,
        "scaler": best_scaler,
        "label_encoder": le,
        "tfidf_vectorizer": best_tfidf,
        "model_name": best_config.replace(" ", "_"),
        "metrics": {"accuracy": best_acc},
    }
    save_path = os.path.join(OUTPUT_DIR, "improved_classifier.pkl")
    with open(save_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"\nSaved to {save_path}")


if __name__ == "__main__":
    main()
