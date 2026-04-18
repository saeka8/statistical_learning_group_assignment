"""
Hyperparameter Tuning for Best Models
======================================
Tests different configurations to maximize accuracy.
"""

import os
import pickle
import warnings
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report

warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "saved_models", "features_cache.pkl")
OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "saved_models")

print("Loading cached features...")
with open(CACHE_PATH, "rb") as f:
    cache = pickle.load(f)

le = LabelEncoder()
y_train = le.fit_transform(cache["train_labels"])
y_val = le.transform(cache["val_labels"])

print("\n" + "=" * 70)
print("EXPERIMENT 1: TF-IDF Vocabulary Size")
print("=" * 70)

for max_feat in [300, 500, 750, 1000, 1500, 2000]:
    tfidf = TfidfVectorizer(max_features=max_feat, stop_words="english", sublinear_tf=True)
    X_tr = tfidf.fit_transform(cache["train_texts"]).toarray()
    X_va = tfidf.transform(cache["val_texts"]).toarray()

    # Add image features
    X_tr_h = np.hstack([X_tr, cache["train_img"]])
    X_va_h = np.hstack([X_va, cache["val_img"]])

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr_h)
    X_va_s = scaler.transform(X_va_h)

    model = SVC(kernel="rbf", C=10, gamma="scale", random_state=42)
    model.fit(X_tr_s, y_train)
    acc = accuracy_score(y_val, model.predict(X_va_s))

    # Text only too
    scaler2 = StandardScaler()
    X_tr_t = scaler2.fit_transform(X_tr)
    X_va_t = scaler2.transform(X_va)
    model2 = SVC(kernel="rbf", C=10, gamma="scale", random_state=42)
    model2.fit(X_tr_t, y_train)
    acc2 = accuracy_score(y_val, model2.predict(X_va_t))

    print(f"  max_features={max_feat:<5d}  Hybrid: {acc:.1%}  Text-only: {acc2:.1%}")

print("\n" + "=" * 70)
print("EXPERIMENT 2: SVM C Parameter Tuning (best vocab from above)")
print("=" * 70)

# Use 1000 features as a good middle ground
tfidf = TfidfVectorizer(max_features=1000, stop_words="english", sublinear_tf=True)
X_tr = tfidf.fit_transform(cache["train_texts"]).toarray()
X_va = tfidf.transform(cache["val_texts"]).toarray()
X_tr_h = np.hstack([X_tr, cache["train_img"]])
X_va_h = np.hstack([X_va, cache["val_img"]])
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr_h)
X_va_s = scaler.transform(X_va_h)

for C in [0.1, 0.5, 1, 5, 10, 50, 100]:
    for gamma in ["scale", "auto"]:
        model = SVC(kernel="rbf", C=C, gamma=gamma, probability=True, random_state=42)
        model.fit(X_tr_s, y_train)
        y_pred = model.predict(X_va_s)
        acc = accuracy_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred, average="weighted")
        print(f"  C={C:<6} gamma={gamma:<6s}  Acc: {acc:.1%}  F1: {f1:.4f}")

print("\n" + "=" * 70)
print("EXPERIMENT 3: Best Config — Full Report")
print("=" * 70)

# Train final best model
best_tfidf = TfidfVectorizer(max_features=1000, stop_words="english", sublinear_tf=True)
X_tr = best_tfidf.fit_transform(cache["train_texts"]).toarray()
X_va = best_tfidf.transform(cache["val_texts"]).toarray()
X_tr_h = np.hstack([X_tr, cache["train_img"]])
X_va_h = np.hstack([X_va, cache["val_img"]])
best_scaler = StandardScaler()
X_tr_s = best_scaler.fit_transform(X_tr_h)
X_va_s = best_scaler.transform(X_va_h)

best_model = SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=42)
best_model.fit(X_tr_s, y_train)
y_pred = best_model.predict(X_va_s)

print(f"\nBest Config: SVM RBF, C=10, gamma=scale, TF-IDF max_features=1000")
print(f"Accuracy: {accuracy_score(y_val, y_pred):.4f}")
print(f"F1: {f1_score(y_val, y_pred, average='weighted'):.4f}")
print(classification_report(y_val, y_pred, target_names=le.classes_))

# Save if it's better
acc_final = accuracy_score(y_val, y_pred)
f1_final = f1_score(y_val, y_pred, average="weighted")

model_data = {
    "model": best_model,
    "scaler": best_scaler,
    "label_encoder": le,
    "tfidf_vectorizer": best_tfidf,
    "model_name": "SVM_RBF_tuned",
    "metrics": {
        "accuracy": acc_final,
        "f1": f1_final,
    },
}
save_path = os.path.join(OUTPUT_DIR, "tuned_svm.pkl")
with open(save_path, "wb") as f:
    pickle.dump(model_data, f)
print(f"Saved tuned model to {save_path}")
