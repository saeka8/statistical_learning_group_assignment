# OCR After YOLO Segmentation

This folder contains the region-based invoice extraction pipeline.

Pipeline:

```text
invoice image
-> YOLO paragraph/table detection
-> crop each kept region
-> OCR per region
-> heuristic field extraction
-> structured JSON
```

This is different from:

- `ai/extraction/precise_yolo/`
  - field-level YOLO detector
- `ai/extraction/purely_ocr/`
  - full-page OCR fallback without region detection

## Main Files

- `train_paragraph_yolo.py`
  - prepares a grouped train/validation split for paragraph/table detection
  - trains the paragraph/table YOLO model
- `predict_paragraph_yolo.py`
  - detection only
- `ocr_by_regions.py`
  - end-to-end region detection + OCR + field extraction
- `extract_fields_from_regions.py`
  - extraction-only step from an existing `region_ocr.json`
- `shared_pipeline.py`
  - detection deduplication and crop padding helpers
- `best.pt`
  - current paragraph/table checkpoint used by default

## Current Folder Layout

Current extraction folders:

- `ai/extraction/dataset/`
  - dataset used by the precise field-level YOLO pipeline
- `ai/extraction/precise_yolo/`
  - precise field detector
- `ai/extraction/ocr_after_yolo_segmentation/`
  - paragraph/table segmentation + OCR
- `ai/extraction/purely_ocr/`
  - OCR-first fallback

## Install

YOLO:

```bash
python3 -m pip install ultralytics
```

OCR dependencies:

```bash
python3 -m pip install -r ai/extraction/purely_ocr/requirements_ocr.txt
```

If you use Tesseract, install the system `tesseract` binary as well.

## OCR Engines

`ocr_by_regions.py` supports:

- `auto`
  - tries `paddleocr`, then `easyocr`, then `tesseract`
- `paddleocr`
- `easyocr`
- `tesseract`

If you do not want EasyOCR fallback, pass `--engine paddleocr` or `--engine tesseract` explicitly.

The engine actually used is saved as `ocr_engine` in `extracted_fields.json`.

## 1. Detection + OCR + Extraction

Main end-to-end command:

```bash
python3 ai/extraction/ocr_after_yolo_segmentation/ocr_by_regions.py \
  --image "/full/path/to/invoice.png" \
  --name invoice_grouped_ocr \
  --conf 0.5 \
  --iou 0.35 \
  --pretty
```

Force PaddleOCR:

```bash
python3 ai/extraction/ocr_after_yolo_segmentation/ocr_by_regions.py \
  --image "ai/extraction/image.png" \
  --name invoice_grouped_ocr \
  --conf 0.5 \
  --iou 0.35 \
  --engine paddleocr \
  --pretty
```

Force Tesseract:

```bash
python3 ai/extraction/ocr_after_yolo_segmentation/ocr_by_regions.py \
  --image "ai/extraction/image.png" \
  --name invoice_grouped_ocr \
  --conf 0.5 \
  --iou 0.35 \
  --engine tesseract \
  --tesseract-lang eng+fra \
  --pretty
```

Outputs:

- `ai/extraction/ocr_after_yolo_segmentation/region_ocr/<name>/region_ocr.json`
- `ai/extraction/ocr_after_yolo_segmentation/region_ocr/<name>/extracted_fields.json`
- `ai/extraction/ocr_after_yolo_segmentation/region_ocr/<name>/crops/`

## 2. Extraction Only

If you already have `region_ocr.json` and only changed extraction rules:

```bash
python3 ai/extraction/ocr_after_yolo_segmentation/extract_fields_from_regions.py \
  --region-json ai/extraction/ocr_after_yolo_segmentation/region_ocr/invoice_grouped_ocr/region_ocr.json \
  --pretty
```

Use this when:

- you changed regexes, anchors, or heuristics
- you do not want to rerun YOLO and OCR

## 3. Detection Only

To test only paragraph/table detection:

```bash
python3 ai/extraction/ocr_after_yolo_segmentation/predict_paragraph_yolo.py \
  --image "/full/path/to/invoice.png" \
  --name paragraph_test
```

Outputs:

- `ai/extraction/ocr_after_yolo_segmentation/predictions/paragraph_test/`
- `detections.json`

## 4. Paragraph/Table Training

Training command:

```bash
python3 ai/extraction/ocr_after_yolo_segmentation/train_paragraph_yolo.py \
  --epochs 20 \
  --imgsz 960 \
  --batch 4 \
  --device mps \
  --name paragraph_table
```

Important:

- this script expects source data inside this folder:
  - `ai/extraction/ocr_after_yolo_segmentation/train/images/`
  - `ai/extraction/ocr_after_yolo_segmentation/train/labels/`
- it then creates:
  - `ai/extraction/ocr_after_yolo_segmentation/prepared/images/train`
  - `ai/extraction/ocr_after_yolo_segmentation/prepared/images/val`
  - `ai/extraction/ocr_after_yolo_segmentation/prepared/labels/train`
  - `ai/extraction/ocr_after_yolo_segmentation/prepared/labels/val`
- if those source `train/` folders are not present, preparation/training will fail

Training outputs go to:

- `ai/extraction/ocr_after_yolo_segmentation/runs/<name>/`

## Output Schema

`extracted_fields.json` contains:

```json
{
  "image": "/abs/path/to/invoice.png",
  "model": "/abs/path/to/best.pt",
  "ocr_engine": "paddleocr",
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

## Notes

- `ocr_by_regions.py` already uses the current `extract_fields_from_regions.py`
- grouped OCR is useful because it preserves region structure better than full-page left-to-right OCR
- post-OCR extraction is rule-based: anchors + regex + region heuristics, not BERT
- `Subtotal`, `VAT`, `Discount`, and `Total` prefer `table` regions and fall back to paragraph regions if needed
- final quality still depends on whether the detector captures the correct regions, especially totals/contact blocks
