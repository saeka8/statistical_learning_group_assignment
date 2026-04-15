"""
Ablation Study: Text-only vs Image-only vs Hybrid
===================================================
Shows the contribution of each feature type.
Uses cached features from train_classifiers.py.
"""

import os
import pickle
import warnings
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, "trained_models", "features_cache.pkl")

print("Loading cached features...")
with open(CACHE_PATH, "rb") as f:
    cache = pickle.load(f)

train_texts = cache["train_texts"]
train_img = cache["train_img"]
train_labels = cache["train_labels"]
val_texts = cache["val_texts"]
val_img = cache["val_img"]
val_labels = cache["val_labels"]

# Build TF-IDF
tfidf = TfidfVectorizer(max_features=500, stop_words="english", sublinear_tf=True)
train_tfidf = tfidf.fit_transform(train_texts).toarray()
val_tfidf = tfidf.transform(val_texts).toarray()

# Encode labels
le = LabelEncoder()
y_train = le.fit_transform(train_labels)
y_val = le.transform(val_labels)

# Three feature sets
feature_sets = {
    "Text only (TF-IDF)": (train_tfidf, val_tfidf),
    "Image only (33 features)": (train_img, val_img),
    "Hybrid (TF-IDF + Image)": (
        np.hstack([train_tfidf, train_img]),
        np.hstack([val_tfidf, val_img]),
    ),
}

# Three best models
model_configs = {
    "SVM (RBF)": lambda: SVC(kernel="rbf", C=10, gamma="scale", random_state=42),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
    "Logistic Regression": lambda: LogisticRegression(max_iter=1000, random_state=42),
}

print("\n" + "=" * 75)
print("ABLATION STUDY: Feature Type Contribution")
print("=" * 75)
print(f"\n{'Feature Set':<30s}", end="")
for mname in model_configs:
    print(f" {mname:>18s}", end="")
print()
print("-" * 84)

for feat_name, (X_tr, X_va) in feature_sets.items():
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)

    print(f"{feat_name:<30s}", end="")
    for mname, model_fn in model_configs.items():
        model = model_fn()
        model.fit(X_tr_s, y_train)
        y_pred = model.predict(X_va_s)
        acc = accuracy_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred, average="weighted")
        print(f"     {acc:.1%} / {f1:.3f}", end="")
    print()

print("\n(Format: Accuracy / F1-score)")
print("\nKey takeaway: Hybrid features combine the strengths of both modalities.")
