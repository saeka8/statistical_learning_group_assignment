# Donut — OCR-Free Invoice Extraction

## What This Is

This folder implements a third alternative for invoice field extraction using **Donut** (Document Understanding Transformer), an OCR-free end-to-end generative model developed by Naver CLOVA.

Unlike every other track in this project, Donut requires **no OCR step**. It takes a raw invoice image and directly generates structured JSON output in a single forward pass.

```
invoice image → Donut model → {"invoice_number": "...", "date": "...", "total": "..."}
```

This makes it fundamentally different from the YOLO and OCR tracks, both of which depend on OCR somewhere in their pipeline.

---

## How Donut Works

Donut combines two components:

| Component | Role |
|---|---|
| Vision encoder (Swin Transformer) | Reads the document image |
| Text decoder (BART-like) | Generates the output token by token |

The model learns reading, layout understanding, and field mapping **jointly** — there is no intermediate text representation. This avoids OCR error propagation entirely.

---

## Why This Is Different

| Step | OCR Method | YOLO + OCR | **Donut** |
|---|---|---|---|
| OCR | ✅ Yes | ✅ Yes | ❌ No |
| Bounding boxes | ❌ No | ✅ Yes | ❌ No |
| End-to-end learning | ❌ No | ❌ No | ✅ Yes |

---

## Tradeoffs

**Advantages**
- No OCR error propagation (`1450` never becomes `14S0`)
- No bounding box annotations required
- Simpler pipeline: image → JSON directly
- Most "human-like" understanding of layout and meaning

**Limitations**
- Data hungry — needs many image + JSON pairs to fine-tune well
- Heavier to train — GPU strongly recommended
- Harder to debug — wrong output is just wrong JSON with no intermediate step to inspect

---

## Pretrained Model Used

```
naver-clova-ix/donut-base
```

Available on HuggingFace. We fine-tune this pretrained checkpoint on our invoice dataset rather than training from scratch.

---

## Target Fields

For this experimental track we focus on a concise subset:

```json
{
  "invoice_number": "...",
  "date": "...",
  "total": "..."
}
```

This keeps fine-tuning feasible on a small dataset while still producing a meaningful comparison.

---

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `donut_invoice_extraction.ipynb` | Full walkthrough: setup, data prep, fine-tuning, inference |
| `README.md` | This file |

---

## Steps to Run

### 1. Install dependencies

```bash
pip install -r ai/extraction/Donut/requirements.txt
```

> A CUDA-capable GPU is strongly recommended. Fine-tuning on CPU is very slow.

### 2. Prepare your invoice data

Your dataset must be a folder of invoice images alongside a JSON file mapping each image to its ground-truth fields:

```
data/
  images/
    invoice_001.jpg
    invoice_002.jpg
    ...
  labels.json
```

`labels.json` format:

```json
[
  {
    "file": "invoice_001.jpg",
    "ground_truth": "{\"invoice_number\": \"INV-001\", \"date\": \"2024-01-15\", \"total\": \"1450.00\"}"
  },
  ...
]
```

The notebook includes a helper cell to generate this JSON from your existing CSV annotations.

### 3. Open and run the notebook

```bash
jupyter notebook ai/extraction/Donut/donut_invoice_extraction.ipynb
```

Run all cells in order. The notebook is divided into clearly labelled sections:

1. **Setup** — imports and configuration
2. **Data preparation** — convert dataset to Donut format
3. **Fine-tuning** — load pretrained Donut, train on invoices
4. **Inference** — run on a single invoice image
5. **Evaluation** — compare extracted fields against ground truth

### 4. Run inference on a new image

The last cells of the notebook show how to load the fine-tuned checkpoint and run it on any invoice image:

```python
result = extract_invoice_fields("path/to/invoice.jpg")
print(result)
# {"invoice_number": "12345", "date": "12/03/2024", "total": "1450.00"}
```

---

## Notes for the Report

This track is included as an **experimental extension**, not a replacement. Even if performance is lower than the YOLO or OCR tracks on our small dataset, the comparison is academically valuable because:

- Donut may be more robust on invoices with unusual or messy layouts
- Error types differ fundamentally (no OCR noise, but possible hallucination)
- It demonstrates the pipeline evolution from `read then think` → `look then read` → `end-to-end understanding`
