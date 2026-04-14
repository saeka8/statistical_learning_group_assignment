# Invoice Information Extraction Approach

## Goal

The objective is to extract structured fields from invoice images, such as:

- `Invoice_Number`
- `Invoice_Date`
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

## Problem Framing

There are two main ways to tackle this task.

### 1. OCR First, Then Classify

Pipeline:

```text
invoice image -> OCR over full page -> classify text spans into fields
```

Advantages:

- Simple baseline
- Fast to prototype
- Works reasonably well if invoice layouts are very similar

Limitations:

- OCR returns a lot of text with no direct field meaning
- Invoices often contain multiple dates, numbers, addresses, and totals
- Mapping raw OCR text to the correct field is difficult when layout varies
- OCR reading order can be noisy in multi-column or dense documents

### 2. Detect Fields First, Then OCR

Pipeline:

```text
invoice image -> field detection -> crop detected regions -> OCR per region -> post-process results
```

Advantages:

- The model first learns where each field is
- OCR only reads from a relevant region
- Easier to assign meaning to extracted text
- More robust when invoice layouts differ

Limitations:

- Requires bounding box annotations
- Slightly more engineering effort than OCR-only

## Chosen Approach

We are maintaining two extraction tracks in parallel:

### Primary Track

```text
Detection / segmentation first -> OCR second -> optional cleanup rules
```

Reason:

Our dataset already contains labeled bounding boxes for semantic invoice fields. That makes the detection-first pipeline the most natural and defensible solution. It separates the task into two smaller problems:

1. Locate the field on the invoice
2. Read the text inside that field

This is generally better than asking one model to infer field meaning from full-page OCR alone.

### Fallback Track

```text
Full-page OCR -> anchor-based search -> regex cleanup -> structured JSON
```

Reason:

If YOLO training remains unstable or too slow, OCR plus rule-based extraction is a practical alternative for a course project. It is easier to finish and debug, especially for fields like email, phone, dates, and totals.

## Current Dataset
https://universe.roboflow.com/roboflow-5gpbq/invoice-data-mbpu8


Current annotation file:

- `Feature_Extraction_Invoice/train/_annotations.csv`

Current image folder:

- `Feature_Extraction_Invoice/train/`

Annotation format:

```text
filename,width,height,class,xmin,ymin,xmax,ymax
```

Each row defines:

- which image the annotation belongs to
- image dimensions
- semantic class label
- bounding box coordinates

## Existing Utility

We added a visualization script:

- `Feature_Extraction_Invoice/Dataset_verification/visualize_labels.py`

This can be used to inspect how fields are labeled on the invoices before training.

Example:

```bash
python3 Feature_Extraction_Invoice/Dataset_verification/visualize_labels.py --sample 5
python3 Feature_Extraction_Invoice/Dataset_verification/visualize_labels.py --image 671_png_jpg.rf.p73UNqF5SQDjw12vTAI6.jpg --open
```

## Method Files

The project is currently organized into method-specific folders:

- `Feature_Extraction_Invoice/YOLO_method/`
- `Feature_Extraction_Invoice/OCR_method/`
- `Feature_Extraction_Invoice/Dataset_verification/`

Main entry points:

- `YOLO_method/train_yolo.py`
- `YOLO_method/run_overnight_yolo.sh`
- `YOLO_method/predict_invoice_yolo.py`
- `OCR_method/extract_invoice_ocr.py`
- `OCR_method/OCR_FALLBACK.md`
- `OCR_method/requirements_ocr.txt`
- `Dataset_verification/visualize_labels.py`

## Planned Pipeline

### Stage 1. Field Detection

Train an object detection model to detect invoice fields such as `Client_Email`, `Client_Phone`, `Total`, and `Invoice_Number`.

Recommended model family:

- YOLOv8 or another modern object detector

Why:

- Easier to train than the older TensorFlow Object Detection API
- Good ecosystem and simpler dataset preparation
- Well-suited to bounding-box detection tasks

Expected output of stage 1:

- bounding boxes
- field labels
- confidence scores

### Stage 2. OCR on Detected Regions

For each detected field:

1. Crop the image region
2. Run OCR on the crop
3. Store the extracted text under the detected label

Example:

```json
{
  "Client_Email": "client@example.com",
  "Client_Phone": "+33 6 12 34 56 78",
  "Total": "1450.00"
}
```

Recommended OCR options:

- PaddleOCR
- EasyOCR
- Tesseract
- Cloud OCR services if allowed

For invoice documents, PaddleOCR is usually a stronger default than plain Tesseract.

### Stage 3. Post-processing

After OCR, apply lightweight cleanup:

- email validation with regex
- phone number normalization
- date normalization
- amount cleanup for currency values

This step improves final field quality without requiring a separate large model.

## Why Not OCR + Transformer Only

A transformer or pre-trained language model can help after OCR, but using it alone is usually weaker for this problem.

OCR-only plus language model would require the system to:

- read all text on the page
- understand page structure
- decide which text belongs to which field

This becomes fragile when layouts vary or OCR order is inconsistent.

A stronger hybrid is:

```text
field detection -> OCR -> light NLP / rules
```

If needed later, a language model can still be added as a refinement stage, but not as the main field-localization method.

## OCR-First Fallback

We also implemented a rule-based OCR-first fallback:

- `Feature_Extraction_Invoice/OCR_method/extract_invoice_ocr.py`

This fallback:

1. runs OCR on the full page
2. groups OCR tokens into lines
3. searches for anchor words such as `Invoice`, `Date`, `TTC`, `TVA`, `Email`, and `Tel`
4. applies regex and field-specific heuristics

This path is especially useful when:

- YOLO metrics are unstable
- training time is too long
- we need a baseline extractor quickly

## Evaluation Plan

We should evaluate the system at two levels.

### Detection Evaluation

Measure whether the model finds the correct region:

- mAP
- IoU-based detection accuracy

### Extraction Evaluation

Measure whether the final extracted value is correct:

- exact match for fields like invoice number, email, and phone
- normalized string match for dates and totals

This matters because good bounding boxes do not automatically imply good OCR results.

## Practical Project Plan

1. Verify annotations visually with `Feature_Extraction_Invoice/Dataset_verification/visualize_labels.py`
2. Convert the dataset into the format required by the chosen detector
3. Train a field detection model
4. Run inference on test invoices
5. Crop detected fields and apply OCR
6. Normalize extracted values
7. Evaluate final field extraction quality

## Recommended Scope

For a realistic course project, the best scope is:

- train a detector on the annotated fields
- apply OCR to detected regions
- demonstrate extraction of a subset of important fields

Suggested priority fields:

- `Invoice_Number`
- `Invoice_Date`
- `Client_Name`
- `Client_Email`
- `Client_Phone`
- `Total`

This keeps the project focused while still demonstrating a complete document understanding pipeline.
