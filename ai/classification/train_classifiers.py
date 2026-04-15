"""
Multi-Model Document Classification — Training & Evaluation
============================================================
Trains SVM, Random Forest, Logistic Regression, and Naive Bayes
on hybrid features (TF-IDF text + handcrafted image features).

Outputs:
  - Comparison table with accuracy, precision, recall, F1
  - Confusion matrices for each model
  - Saves the best model as best_classifier.pkl

Usage:
    python train_classifiers.py
"""

import os
import sys
import time
import pickle
import warnings
import numpy as np
from collections import defaultdict

from PIL import Image
from skimage.feature import hog
from scipy.ndimage import sobel
import pytesseract

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "trained_models")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CATEGORIES = ["email", "invoice", "resume", "scientific_publication"]


# ── image feature extraction (same 33 features as Nathan's pipeline) ──
def extract_image_features(img_path, target_size=(256, 256)):
    """Extract 33 handcrafted visual features from a document image."""
    img = Image.open(img_path).convert("L")
    img_resized = img.resize(target_size)
    img_arr = np.array(img_resized)

    # 1. HOG (4 summary stats)
    hog_feat = hog(img_arr, orientations=9, pixels_per_cell=(16, 16),
                   cells_per_block=(2, 2), feature_vector=True)
    hog_summary = [float(np.mean(hog_feat)), float(np.std(hog_feat)),
                   float(np.max(hog_feat)), float(np.median(hog_feat))]

    # 2. Text density — binarize + 4x4 grid (1 + 16)
    binary = (img_arr < 128).astype(float)
    text_density = float(np.mean(binary))
    grid_size = 4
    h, w = img_arr.shape
    grid_h, grid_w = h // grid_size, w // grid_size
    grid_densities = []
    for i in range(grid_size):
        for j in range(grid_size):
            region = binary[i*grid_h:(i+1)*grid_h, j*grid_w:(j+1)*grid_w]
            grid_densities.append(float(np.mean(region)))

    # 3. Whitespace (6)
    row_means = np.mean(binary, axis=1)
    col_means = np.mean(binary, axis=0)
    blank_rows = float(np.sum(row_means < 0.01) / len(row_means))
    blank_cols = float(np.sum(col_means < 0.01) / len(col_means))
    top_half = float(np.mean(binary[:h//2, :]))
    bottom_half = float(np.mean(binary[h//2:, :]))
    left_half = float(np.mean(binary[:, :w//2]))
    right_half = float(np.mean(binary[:, w//2:]))

    # 4. Edges (2)
    edges_h = sobel(img_arr.astype(float), axis=0)
    edges_v = sobel(img_arr.astype(float), axis=1)
    edge_mag = np.sqrt(edges_h**2 + edges_v**2)
    edge_density = float(np.mean(edge_mag))
    edge_std = float(np.std(edge_mag))

    # 5. Margins (4)
    rows_text = np.where(row_means > 0.01)[0]
    cols_text = np.where(col_means > 0.01)[0]
    if len(rows_text) > 0 and len(cols_text) > 0:
        top_m = float(rows_text[0] / h)
        bot_m = float(1 - rows_text[-1] / h)
        left_m = float(cols_text[0] / w)
        right_m = float(1 - cols_text[-1] / w)
    else:
        top_m = bot_m = left_m = right_m = 0.5

    return (hog_summary + [text_density] + grid_densities +
            [blank_rows, blank_cols, top_half, bottom_half, left_half, right_half] +
            [edge_density, edge_std, top_m, bot_m, left_m, right_m])


# ── load dataset ─────────────────────────────────────────────
def load_split(split_name):
    """Load images from a split, run OCR and extract image features."""
    split_dir = os.path.join(DATA_DIR, split_name)
    texts = []
    img_features = []
    labels = []
    errors = 0

    for cat in CATEGORIES:
        cat_dir = os.path.join(split_dir, cat)
        files = sorted(os.listdir(cat_dir))
        print(f"  Processing {split_name}/{cat} ({len(files)} images)...")

        for i, fname in enumerate(files):
            fpath = os.path.join(cat_dir, fname)
            try:
                # OCR
                img = Image.open(fpath)
                text = pytesseract.image_to_string(img)
                texts.append(text)

                # Image features
                feats = extract_image_features(fpath)
                img_features.append(feats)

                labels.append(cat)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"    Error on {fname}: {e}")

            if (i + 1) % 40 == 0:
                print(f"    {i+1}/{len(files)} done")

    print(f"  {split_name}: {len(texts)} loaded, {errors} errors")
    return texts, np.array(img_features), labels


# ── main ─────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("DOCUMENT CLASSIFICATION — MULTI-MODEL COMPARISON")
    print("=" * 70)

    # ── Step 1: Feature extraction ──
    cache_path = os.path.join(OUTPUT_DIR, "features_cache.pkl")

    if os.path.exists(cache_path):
        print("\nLoading cached features...")
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
        train_texts = cache["train_texts"]
        train_img = cache["train_img"]
        train_labels = cache["train_labels"]
        val_texts = cache["val_texts"]
        val_img = cache["val_img"]
        val_labels = cache["val_labels"]
    else:
        print("\nStep 1: Extracting features (this takes a while — OCR on every image)...")
        t0 = time.time()

        print("\n[TRAIN SET]")
        train_texts, train_img, train_labels = load_split("train")

        print("\n[VALIDATION SET]")
        val_texts, val_img, val_labels = load_split("validation")

        elapsed = time.time() - t0
        print(f"\nFeature extraction done in {elapsed/60:.1f} minutes")

        # Cache features so we don't have to re-run OCR
        with open(cache_path, "wb") as f:
            pickle.dump({
                "train_texts": train_texts, "train_img": train_img,
                "train_labels": train_labels,
                "val_texts": val_texts, "val_img": val_img,
                "val_labels": val_labels,
            }, f)
        print("Features cached to", cache_path)

    # ── Step 2: Build feature vectors ──
    print("\nStep 2: Building TF-IDF + image feature vectors...")

    # TF-IDF (500 features, same as Nathan)
    tfidf = TfidfVectorizer(max_features=500, stop_words="english",
                            sublinear_tf=True)
    train_tfidf = tfidf.fit_transform(train_texts).toarray()
    val_tfidf = tfidf.transform(val_texts).toarray()

    # Combine: TF-IDF (500) + image (33) = 533
    X_train = np.hstack([train_tfidf, train_img])
    X_val = np.hstack([val_tfidf, val_img])

    # Scale
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    # Labels
    le = LabelEncoder()
    y_train = le.fit_transform(train_labels)
    y_val = le.transform(val_labels)

    print(f"  Train: {X_train.shape} | Val: {X_val.shape}")
    print(f"  Classes: {list(le.classes_)}")

    # ── Step 3: Train models ──
    print("\nStep 3: Training classifiers...\n")

    models = {
        "Random Forest (200 trees)": RandomForestClassifier(
            n_estimators=200, max_depth=10, random_state=42, n_jobs=-1
        ),
        "SVM (RBF kernel)": SVC(
            kernel="rbf", C=10, gamma="scale", probability=True, random_state=42
        ),
        "SVM (Linear)": SVC(
            kernel="linear", C=1.0, probability=True, random_state=42
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=1000, C=1.0, random_state=42, n_jobs=-1
        ),
        "Naive Bayes": GaussianNB(),
    }

    results = {}

    for name, model in models.items():
        print(f"  Training {name}...")
        t0 = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - t0

        y_pred = model.predict(X_val)
        acc = accuracy_score(y_val, y_pred)
        prec = precision_score(y_val, y_pred, average="weighted")
        rec = recall_score(y_val, y_pred, average="weighted")
        f1 = f1_score(y_val, y_pred, average="weighted")
        cm = confusion_matrix(y_val, y_pred)

        results[name] = {
            "model": model,
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "confusion_matrix": cm,
            "train_time": train_time,
            "predictions": y_pred,
        }
        print(f"    Accuracy: {acc:.4f} | F1: {f1:.4f} | Time: {train_time:.1f}s")

    # ── Step 4: Print comparison ──
    print("\n" + "=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)
    print(f"\n{'Model':<30s} {'Accuracy':>10s} {'Precision':>10s} {'Recall':>10s} {'F1':>10s} {'Time':>8s}")
    print("-" * 78)

    best_name = None
    best_f1 = 0

    for name, r in sorted(results.items(), key=lambda x: -x[1]["f1"]):
        print(f"{name:<30s} {r['accuracy']:>10.4f} {r['precision']:>10.4f} {r['recall']:>10.4f} {r['f1']:>10.4f} {r['train_time']:>7.1f}s")
        if r["f1"] > best_f1:
            best_f1 = r["f1"]
            best_name = name

    # ── Step 5: Detailed report for each model ──
    print("\n" + "=" * 70)
    print("DETAILED CLASSIFICATION REPORTS")
    print("=" * 70)

    for name, r in results.items():
        print(f"\n--- {name} ---")
        print(classification_report(y_val, r["predictions"],
              target_names=le.classes_))
        print("Confusion Matrix:")
        print(f"{'':>25s}", end="")
        for c in le.classes_:
            print(f"{c[:10]:>12s}", end="")
        print()
        for i, row in enumerate(r["confusion_matrix"]):
            print(f"{le.classes_[i]:>25s}", end="")
            for val in row:
                print(f"{val:>12d}", end="")
            print()

    # ── Step 6: Save best model ──
    print(f"\n{'=' * 70}")
    print(f"BEST MODEL: {best_name} (F1 = {best_f1:.4f})")
    print(f"{'=' * 70}")

    best_model = results[best_name]["model"]
    model_data = {
        "model": best_model,
        "scaler": scaler,
        "label_encoder": le,
        "tfidf_vectorizer": tfidf,
        "model_name": best_name,
        "metrics": {
            "accuracy": results[best_name]["accuracy"],
            "precision": results[best_name]["precision"],
            "recall": results[best_name]["recall"],
            "f1": results[best_name]["f1"],
        },
    }

    best_path = os.path.join(OUTPUT_DIR, "best_classifier.pkl")
    with open(best_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"Saved to {best_path}")

    # Also save TF-IDF separately (for compatibility)
    tfidf_path = os.path.join(OUTPUT_DIR, "tfidf_vectorizer.pkl")
    with open(tfidf_path, "wb") as f:
        pickle.dump(tfidf, f)
    print(f"TF-IDF saved to {tfidf_path}")

    # Save all models for comparison
    all_path = os.path.join(OUTPUT_DIR, "all_classifiers.pkl")
    all_data = {}
    for name, r in results.items():
        all_data[name] = {
            "model": r["model"],
            "accuracy": r["accuracy"],
            "f1": r["f1"],
        }
    with open(all_path, "wb") as f:
        pickle.dump(all_data, f)
    print(f"All models saved to {all_path}")


if __name__ == "__main__":
    main()
