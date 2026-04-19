"""
Legacy standalone classification pipeline (DEPRECATED — not used by the web app).
==================================================================================
This file predates the current web application architecture. The deployed
production pipeline lives in:
  - backend/ml/classifier.py  (loads improved_classifier.pkl, soft-voting ensemble)
  - backend/ml/extractor.py   (LayoutLMv2 document-QA)

This script's path constants (PROJECT_DIR/models, PROJECT_DIR/processed_data)
point to directories that no longer exist; it is retained only as a reference
artefact. Do not use.

If you need a standalone classifier demo, use:
  ai/classification/model_training/4_improved_ensemble.py
"""

import sys
import os
import re
import json
import pickle
import warnings
import numpy as np
from PIL import Image
from skimage.feature import hog
from scipy.ndimage import sobel
import pytesseract

warnings.filterwarnings('ignore')

# ============================================================
# PATHS
# ============================================================
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
DATA_DIR = os.path.join(PROJECT_DIR, "processed_data")


# ============================================================
# IMAGE FEATURE EXTRACTION
# ============================================================
def extract_image_features(img_path, target_size=(256, 256)):
    """Extract 33 handcrafted visual features from a document image."""
    img = Image.open(img_path).convert("L")
    img_resized = img.resize(target_size)
    img_arr = np.array(img_resized)

    # 1. HOG features
    hog_feat = hog(img_arr, orientations=9, pixels_per_cell=(16, 16),
                   cells_per_block=(2, 2), feature_vector=True)
    hog_summary = [float(np.mean(hog_feat)), float(np.std(hog_feat)),
                   float(np.max(hog_feat)), float(np.median(hog_feat))]

    # 2. Text density (binarize and compute density in 4x4 grid)
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

    # 3. Whitespace features
    row_means = np.mean(binary, axis=1)
    col_means = np.mean(binary, axis=0)
    blank_rows = float(np.sum(row_means < 0.01) / len(row_means))
    blank_cols = float(np.sum(col_means < 0.01) / len(col_means))

    top_half_density = float(np.mean(binary[:h//2, :]))
    bottom_half_density = float(np.mean(binary[h//2:, :]))
    left_half_density = float(np.mean(binary[:, :w//2]))
    right_half_density = float(np.mean(binary[:, w//2:]))

    # 4. Edge features
    edges_h = sobel(img_arr.astype(float), axis=0)
    edges_v = sobel(img_arr.astype(float), axis=1)
    edge_magnitude = np.sqrt(edges_h**2 + edges_v**2)
    edge_density = float(np.mean(edge_magnitude))
    edge_std = float(np.std(edge_magnitude))

    # 5. Margins
    rows_with_text = np.where(row_means > 0.01)[0]
    cols_with_text = np.where(col_means > 0.01)[0]
    if len(rows_with_text) > 0 and len(cols_with_text) > 0:
        top_margin = float(rows_with_text[0] / h)
        bottom_margin = float(1 - rows_with_text[-1] / h)
        left_margin = float(cols_with_text[0] / w)
        right_margin = float(1 - cols_with_text[-1] / w)
    else:
        top_margin = bottom_margin = left_margin = right_margin = 0.5

    return (hog_summary + [text_density] + grid_densities +
            [blank_rows, blank_cols] +
            [top_half_density, bottom_half_density, left_half_density, right_half_density] +
            [edge_density, edge_std] +
            [top_margin, bottom_margin, left_margin, right_margin])


# ============================================================
# INVOICE INFORMATION EXTRACTION
# ============================================================
class InvoiceExtractor:
    """Rule-based invoice information extractor using regex on OCR text."""

    def __init__(self):
        self.date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b',
            r'\b(\d{4}-\d{2}-\d{2})\b',
        ]

    def extract_invoice_number(self, text):
        patterns = [
            r'(?:invoice\s*(?:no|number|#|num))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})',
            r'(?:inv\s*(?:no|#))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})',
            r'(?:doc(?:ument)?\s*(?:no|#|number))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})',
            r'(?:receipt\s*(?:no|#|number))[.:\s#]*\s*([A-Za-z0-9][\w\-/]{2,20})',
            r'INVOICE\s*NO[.\s]*(\d{3,15})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num = match.group(1).strip()
                if len(num) >= 3 and num.lower() not in ['the', 'and', 'for', 'date', 'erence']:
                    return num
        return None

    def extract_invoice_date(self, text):
        date_context = re.search(r'(?:^|\n)\s*(?:invoice\s*)?date[:\s]+(.{6,30})', text, re.IGNORECASE)
        if date_context:
            for pattern in self.date_patterns:
                match = re.search(pattern, date_context.group(1))
                if match:
                    return match.group(1).strip()
        date_line = re.search(r'date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
        if date_line:
            return date_line.group(1).strip()
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def extract_due_date(self, text):
        patterns = [
            r'(?:due\s*date|payment\s*due|pay\s*by|payable\s*by)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:due\s*date|payment\s*due|pay\s*by)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})',
            r'(?:due\s*date|payment\s*due)[:\s]*(.{6,25})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                for dp in self.date_patterns:
                    dm = re.search(dp, result)
                    if dm:
                        return dm.group(1)
                if len(result) > 3:
                    return result
        return None

    def _parse_amount(self, s):
        s = re.sub(r'\s+', '', s.strip())
        if re.match(r'^\d+,\d{2}$', s):
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
        try:
            return float(s)
        except:
            return None

    def extract_total(self, text):
        lines = text.split('\n')

        # Pass 1: Grand Total
        for line in reversed(lines):
            match = re.search(r'grand\s*total[:\s]*[\$£€RM\s]*([\d,\s]+\.?\d*)', line, re.IGNORECASE)
            if match:
                val = self._parse_amount(match.group(1))
                if val and val > 0:
                    return f"{val:.2f}"

        # Pass 2: Total Rounded / Total (incl GST)
        for line in reversed(lines):
            match = re.search(r'(?:total\s*rounded|total\s*\(?\s*incl|round\w*\s*total)[:\s]*[\$£€RM\s]*([\d,\s]+\.\d{2})', line, re.IGNORECASE)
            if match:
                val = self._parse_amount(match.group(1))
                if val and val > 0:
                    return f"{val:.2f}"

        # Pass 3: Total with amount (skip subtotal)
        for line in reversed(lines):
            if re.search(r'sub\s*total', line, re.IGNORECASE):
                continue
            match = re.search(r'\btotal(?:\s*\w*)?[:\s]*[\$£€RM\s]*([\d,\s]+\.\d{2})', line, re.IGNORECASE)
            if match:
                val = self._parse_amount(match.group(1))
                if val and val > 0:
                    return f"{val:.2f}"

        # Pass 4: Comma-decimal format
        for line in reversed(lines):
            if re.search(r'sub\s*total', line, re.IGNORECASE):
                continue
            match = re.search(r'\btotal(?:\s*\w*)?[:\s]*[\$£€RM\s]*([\d,\s]+,\d{2})\b', line, re.IGNORECASE)
            if match:
                val = self._parse_amount(match.group(1))
                if val and val > 0:
                    return f"{val:.2f}"

        # Pass 5: Total with any number
        for line in reversed(lines):
            if re.search(r'sub\s*total', line, re.IGNORECASE):
                continue
            match = re.search(r'\btotal\b.*?([\d,]+\.?\d+)', line, re.IGNORECASE)
            if match:
                val = self._parse_amount(match.group(1))
                if val and val > 0:
                    return f"{val:.2f}"

        # Pass 6: Last dollar amount
        amounts = re.findall(r'[\$£€]\s*([\d,]+\.\d{2})', text)
        if amounts:
            val = self._parse_amount(amounts[-1])
            if val and val > 0:
                return f"{val:.2f}"

        return None

    def extract_issuer(self, text):
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        skip_patterns = [r'^tan\s', r'^page\s', r'^\d+$', r'^[\s\W]+$']
        clean_lines = []
        for line in lines[:15]:
            if not any(re.match(sp, line, re.IGNORECASE) for sp in skip_patterns):
                clean_lines.append(line)

        company_suffixes = r'(?:Inc|LLC|Ltd|Corp|Co\b|Company|Enterprise|SDN\s*BHD|Sdn\s*Bhd|PLC|GmbH|AG\b|S\.?A\b|SRL|BV|NV|Restaurants?|Trading|Motor|Machinery)'
        for line in clean_lines[:10]:
            if re.search(company_suffixes, line, re.IGNORECASE):
                if len(line) > 3:
                    return line

        for line in clean_lines[:5]:
            if (len(line) > 5
                and not re.match(r'^[\d\s/\-\.,:]+$', line)
                and not re.search(r'invoice|receipt|date|total|page', line, re.IGNORECASE)):
                return line
        return None

    def extract_recipient(self, text):
        patterns = [
            r'(?:bill\s*to|sold\s*to|ship\s*to|deliver\s*to)[:\s]*\n?\s*(.+?)(?:\n|$)',
            r'(?:attn|attention)[:\s]*\n?\s*(.+?)(?:\n|$)',
            r'(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})',
            r'(?:customer|client)[:\s]*\n?\s*(.+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = re.sub(r'\s+', ' ', match.group(1).strip())
                if 2 < len(name) < 80:
                    return name
        to_match = re.search(r'^(?:to)[:\s]+(.+?)$', text, re.IGNORECASE | re.MULTILINE)
        if to_match:
            name = to_match.group(1).strip()
            if 2 < len(name) < 80:
                return name
        return None

    def extract_all(self, text):
        return {
            'invoice_number': self.extract_invoice_number(text),
            'invoice_date': self.extract_invoice_date(text),
            'due_date': self.extract_due_date(text),
            'issuer_name': self.extract_issuer(text),
            'recipient_name': self.extract_recipient(text),
            'total_amount': self.extract_total(text),
        }


# ============================================================
# MAIN PIPELINE
# ============================================================
class DocumentPipeline:
    """End-to-end document classification and invoice extraction pipeline."""

    def __init__(self):
        # Load trained classifier
        with open(os.path.join(MODELS_DIR, "classifier.pkl"), "rb") as f:
            model_data = pickle.load(f)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.model_name = model_data['model_name']

        # Load TF-IDF vectorizer
        with open(os.path.join(DATA_DIR, "tfidf_vectorizer.pkl"), "rb") as f:
            self.tfidf = f
        self.tfidf = pickle.load(open(os.path.join(DATA_DIR, "tfidf_vectorizer.pkl"), "rb"))

        # Initialize invoice extractor
        self.invoice_extractor = InvoiceExtractor()

        print(f"Pipeline loaded successfully.")
        print(f"  Classifier: {self.model_name}")
        print(f"  Categories: {list(self.label_encoder.classes_)}")

    def process(self, image_path):
        """Process a single document image through the full pipeline."""
        result = {
            'image_path': image_path,
            'category': None,
            'confidence': None,
            'ocr_text_preview': None,
            'invoice_fields': None,
        }

        # Step 1: OCR
        print(f"\n[1/4] Running OCR on {os.path.basename(image_path)}...")
        img = Image.open(image_path)
        ocr_text = pytesseract.image_to_string(img)
        result['ocr_text_preview'] = ocr_text[:200] + "..." if len(ocr_text) > 200 else ocr_text
        print(f"      Extracted {len(ocr_text)} characters")

        # Step 2: Extract features
        print("[2/4] Extracting features...")
        # Text features
        tfidf_vec = self.tfidf.transform([ocr_text]).toarray()  # (1, 500)
        # Image features
        img_feat = np.array(extract_image_features(image_path)).reshape(1, -1)  # (1, 33)
        # Combine
        hybrid_features = np.hstack([tfidf_vec, img_feat])  # (1, 533)
        hybrid_scaled = self.scaler.transform(hybrid_features)
        print(f"      Text features: {tfidf_vec.shape[1]} | Image features: {img_feat.shape[1]} | Combined: {hybrid_features.shape[1]}")

        # Step 3: Classify
        print("[3/4] Classifying document...")
        prediction = self.model.predict(hybrid_scaled)[0]
        category = self.label_encoder.inverse_transform([prediction])[0]

        # Get confidence (probability for RF, decision function for SVM)
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(hybrid_scaled)[0]
            confidence = float(max(proba))
            all_probs = dict(zip(self.label_encoder.classes_, [f"{p:.2%}" for p in proba]))
        else:
            confidence = None
            all_probs = {}

        result['category'] = category
        result['confidence'] = confidence
        result['all_probabilities'] = all_probs
        print(f"      Category: {category} (confidence: {confidence:.2%})")
        if all_probs:
            print(f"      All probabilities: {all_probs}")

        # Step 4: Extract invoice fields (only if classified as invoice)
        if category == 'invoice':
            print("[4/4] Extracting invoice information...")
            fields = self.invoice_extractor.extract_all(ocr_text)
            result['invoice_fields'] = fields
            print(f"      Invoice Number: {fields['invoice_number']}")
            print(f"      Invoice Date:   {fields['invoice_date']}")
            print(f"      Due Date:       {fields['due_date']}")
            print(f"      Issuer:         {fields['issuer_name']}")
            print(f"      Recipient:      {fields['recipient_name']}")
            print(f"      Total Amount:   {fields['total_amount']}")
        else:
            print("[4/4] Not an invoice — skipping extraction.")

        return result


def run_demo(image_paths=None):
    """Run demo on provided images, or scan a 'demo_images' folder."""
    pipeline = DocumentPipeline()

    print("\n" + "=" * 70)
    print("LIVE DEMO — Document Classification & Invoice Extraction")
    print("=" * 70)

    # If no paths given, look for a demo_images folder next to src/
    if not image_paths:
        demo_dir = os.path.join(PROJECT_DIR, "demo_images")
        if os.path.isdir(demo_dir):
            image_paths = [os.path.join(demo_dir, f) for f in sorted(os.listdir(demo_dir))
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]
        if not image_paths:
            print("\nNo images provided. Usage options:")
            print("  python pipeline.py --demo img1.png img2.jpg img3.png")
            print("  Or place images in a 'demo_images/' folder next to src/")
            return

    results = []
    for img_path in image_paths:
        print(f"\n{'─' * 70}")
        print(f"Processing: {os.path.basename(img_path)}")
        print(f"{'─' * 70}")

        result = pipeline.process(img_path)
        results.append(result)

        print(f"  Category:   {result['category']}")
        print(f"  Confidence: {result['confidence']:.1%}")
        print(f"  All scores: {', '.join(f'{k}: {v}' for k, v in result['all_probabilities'].items())}")

        if result.get('invoice_fields'):
            print(f"\n  === Invoice Fields Extracted ===")
            for field, value in result['invoice_fields'].items():
                if value:
                    print(f"    {field}: {value}")

    print(f"\n{'=' * 70}")
    print(f"Processed {len(results)} document(s)")
    print(f"{'=' * 70}")


def run_evaluation():
    """Run full evaluation on held-out test samples."""
    pipeline = DocumentPipeline()

    categories = ['email', 'invoice', 'resume', 'scientific_publication']
    raw_dir = os.path.join(DATA_DIR, "raw")

    print("\n" + "=" * 70)
    print("FULL EVALUATION")
    print("=" * 70)

    # Use images 80-99 (last 20 per class) as unseen test data
    correct = 0
    total = 0
    confusion = {c: {c2: 0 for c2 in categories} for c in categories}

    for cat in categories:
        cat_dir = os.path.join(raw_dir, cat)
        files = sorted(os.listdir(cat_dir))[80:100]

        for fname in files:
            result = pipeline.process(os.path.join(cat_dir, fname))
            predicted = result['category']
            confusion[cat][predicted] += 1
            if predicted == cat:
                correct += 1
            total += 1

    print(f"\n{'=' * 70}")
    print(f"Overall Accuracy: {correct}/{total} ({100*correct/total:.1f}%)")
    print(f"\nConfusion Matrix:")
    print(f"{'':25s} {'email':>10s} {'invoice':>10s} {'resume':>10s} {'sci_pub':>10s}")
    for cat in categories:
        short = cat[:7] if len(cat) > 10 else cat
        row = f"{cat:25s}"
        for c2 in categories:
            row += f" {confusion[cat][c2]:10d}"
        print(row)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python pipeline.py <image_path>     Process a single document")
        print("  python pipeline.py --demo           Run demo on sample images")
        print("  python pipeline.py --evaluate       Run full evaluation")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--demo":
        extra_images = sys.argv[2:] if len(sys.argv) > 2 else None
        run_demo(extra_images)
    elif arg == "--evaluate":
        run_evaluation()
    else:
        if not os.path.exists(arg):
            print(f"Error: File not found: {arg}")
            sys.exit(1)
        pipeline = DocumentPipeline()
        result = pipeline.process(arg)
        print(f"\n{'=' * 50}")
        print(json.dumps(result, indent=2, default=str))
