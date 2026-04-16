# Paragraph/Table YOLO Pipeline

This folder contains the paragraph/table detection pipeline for invoice images.

Goal:

- detect larger logical regions such as `paragraph` and `table`
- run OCR inside those detected regions
- extract structured invoice fields from grouped region text

This is an alternative to field-level YOLO detection.

## Files

- `train_paragraph_yolo.py`
  - prepares a grouped train/validation split
  - trains YOLO on the `paragraph` / `table` dataset
- `predict_paragraph_yolo.py`
  - runs paragraph/table detection only
- `ocr_by_regions.py`
  - runs detection, OCR on each kept region, and final field extraction
- `extract_fields_from_regions.py`
  - field-mapping logic used by `ocr_by_regions.py`
- `data.yaml`
  - generated training config pointing at `prepared/`

## Dataset Layout

Source dataset expected by this pipeline:

- `train/images/`
- `train/labels/`

The script creates a prepared split here:

- `prepared/images/train`
- `prepared/images/val`
- `prepared/labels/train`
- `prepared/labels/val`

Important:

- the split is grouped by original invoice document
- augmented versions of the same invoice stay in the same split
- this avoids train/validation leakage

## Install Dependencies

For YOLO:

```bash
python3 -m pip install ultralytics
```

For OCR:

```bash
python3 -m pip install -r ai/extraction/OCR_method/requirements_ocr.txt
```

If you use Tesseract, the system binary must also be installed.

## 1. Prepare Dataset

```bash
python3 ai/extraction/paragraph_yolo/train_paragraph_yolo.py --prepare-only --force
```

This builds:

- `ai/extraction/paragraph_yolo/prepared/`
- `ai/extraction/paragraph_yolo/data.yaml`

## 2. Train YOLO

Recommended starting command:

```bash
python3 ai/extraction/paragraph_yolo/train_paragraph_yolo.py \
  --epochs 20 \
  --imgsz 960 \
  --batch 4 \
  --device mps \
  --name paragraph_table
```

Training outputs go to:

- `ai/extraction/paragraph_yolo/runs/paragraph_table/`

Important files:

- `runs/paragraph_table/weights/best.pt`
- `runs/paragraph_table/weights/last.pt`
- `runs/paragraph_table/results.csv`

Use `best.pt` for inference.

## 3. Test Detection Only

To visualize paragraph/table boxes on a new invoice image:

```bash
python3 ai/extraction/paragraph_yolo/predict_paragraph_yolo.py \
  --image "/full/path/to/invoice.png" \
  --name paragraph_test
  
```

Outputs:

- `ai/extraction/paragraph_yolo/predictions/paragraph_test/`

Important file:

- `detections.json`

## 4. Run Detection + OCR + Field Extraction

This is the main end-to-end command for backend integration:

```bash
python3 ai/extraction/paragraph_yolo/ocr_by_regions.py \
  --image "/full/path/to/invoice.png" \
  --name invoice_grouped_ocr \
  --conf 0.5 \
  --iou 0.35 \
  --pretty
```

What it does:

1. runs the paragraph/table detector
2. removes duplicate same-label boxes more aggressively
3. crops each kept region
4. runs OCR inside each crop
5. extracts invoice fields from grouped region text

Outputs:

- `ai/extraction/paragraph_yolo/region_ocr/invoice_grouped_ocr/region_ocr.json`
- `ai/extraction/paragraph_yolo/region_ocr/invoice_grouped_ocr/extracted_fields.json`
- `ai/extraction/paragraph_yolo/region_ocr/invoice_grouped_ocr/crops/`

## Output Format

`extracted_fields.json` contains:

```json
{
  "image": "/abs/path/to/invoice.png",
  "model": "/abs/path/to/best.pt",
  "ocr_engine": "easyocr",
  "extracted_fields": {
    "Invoice_Number": {
      "value": "82896",
      "method": "metadata_region",
      "evidence": "..."
    }
  }
}
```

Supported field keys:

- `Invoice_Number`
- `Invoice_Date`
- `Issuer_Name`
- `Client_Name`
- `Client_Email`
- `Client_Phone`
- `Billing_Address`
- `Shipping_Address`
- `Products`
- `Subtotal`
- `VAT`
- `Total`
- `Discount`
- `VAT_Rate`
- `Discount_Rate`
- `Due_Date`

## Suggested Backend Integration

For backend use, the simplest path is:

1. save the uploaded invoice image temporarily
2. call `ocr_by_regions.py`
3. read `extracted_fields.json`
4. return `extracted_fields` to the API layer

The backend only needs to consume:

- `extracted_fields.json`

The extra files are useful for debugging:

- `region_ocr.json`
- cropped region images
- rendered YOLO prediction image

## Recommended Defaults

These work well for first integration tests:

- `--conf 0.5`
- `--iou 0.35`
- default model:
  - `runs/paragraph_table/weights/best.pt`

If duplicate boxes remain high, tune:

- `--conf`
- `--iou`
- internal deduplication settings in `ocr_by_regions.py`

## Notes

- `best.pt` is the checkpoint to use for inference, not `last.pt`
- grouped OCR is useful because it avoids reading the whole page strictly left-to-right
- post-OCR field extraction is heuristic: anchor words + regexes + region-type rules, not a transformer model
- money fields such as `Subtotal`, `VAT`, `Discount`, and `Total` now prefer `table` regions and only fall back to paragraph regions when needed
- final quality still depends on whether the detector keeps the right regions, especially the totals block
