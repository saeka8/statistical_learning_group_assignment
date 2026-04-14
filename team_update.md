# Project Update — Document Classification & Information Extraction

## Chosen Categories (4)
1. **Invoices** (required)
2. **Emails**
3. **Scientific Publications**
4. **Resumes**

## Datasets
| Dataset | Purpose | Format | Size | Source |
|---------|---------|--------|------|--------|
| RVL-CDIP | Document classification (all 4 categories) | Grayscale PNG images | 25,000 images per class | [Hugging Face](https://huggingface.co/datasets/aharley/rvl_cdip) / [Kaggle](https://www.kaggle.com/datasets/pdavpoojan/the-rvlcdip-dataset-test) |
| SROIE (ICDAR 2019) | Invoice field extraction (annotated) | Scanned receipt/invoice images | ~1,000 images | [ICDAR](https://rrc.cvc.uab.es/?ch=13) / [Kaggle](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2) |

## Technical Approach — Hybrid (NLP + CV)
- **Text pipeline:** OCR (Tesseract) → TF-IDF / bag-of-words features
- **Image pipeline:** Handcrafted visual features (HOG, text density, layout metrics, whitespace ratios)
- **Classifier:** SVM or Random Forest on combined feature vectors
- **Invoice extraction:** Regex and rule-based pattern matching on OCR output
- **No generative AI or deep learning** — all traditional/classical methods

## Why These Categories?
They are maximally distinct in vocabulary, layout, and structure:
- **Invoices** — structured tables, line items, monetary amounts, dates
- **Emails** — From/To/Subject headers, casual tone, short body text
- **Scientific Publications** — dense text, two-column layouts, abstracts, citations
- **Resumes** — section-based (Education, Experience, Skills), bulleted lists, contact info
