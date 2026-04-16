# Invoice Information Extraction Approach

## Goal

The objective is to extract structured fields from invoice images, such as:

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

We are currently maintaining four extraction tracks in parallel:

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

### Region-First Track

```text
Paragraph / table detection -> OCR inside each detected region -> field extraction from region text
```

Reason:

Instead of detecting every final field directly, we can first detect larger logical regions such as `paragraph` and `table`. This can make OCR more reliable because it limits reading to semantically related content blocks. It is especially useful when several related values appear together in the same area, for example line items inside a table or contact details grouped in one paragraph.

Current post-OCR extraction in this track is rule-based, not model-based:

- anchor words such as `invoice number`, `bill to`, `subtotal`, `vat`
- regexes for dates, amounts, percentages, emails, and phones
- simple region-type assumptions, for example preferring totals from `table` regions and contact blocks from `paragraph` regions

## Current Dataset
https://universe.roboflow.com/roboflow-5gpbq/invoice-data-mbpu8


Current annotation file:

- `ai/extraction/train/_annotations.csv`

Current image folder:

- `ai/extraction/train/`

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

- `ai/extraction/Dataset_verification/visualize_labels.py`

This can be used to inspect how fields are labeled on the invoices before training.

Example:

```bash
python3 ai/extraction/Dataset_verification/visualize_labels.py --sample 5
python3 ai/extraction/Dataset_verification/visualize_labels.py --image 671_png_jpg.rf.p73UNqF5SQDjw12vTAI6.jpg --open
```

## Method Files

The project is currently organized into method-specific folders:

- `ai/extraction/YOLO_method/`
- `ai/extraction/paragraph_yolo/`
- `ai/extraction/OCR_method/`
- `ai/extraction/Dataset_verification/`

Main entry points:

- `YOLO_method/train_yolo.py`
- `YOLO_method/run_overnight_yolo.sh`
- `YOLO_method/predict_invoice_yolo.py`
- `paragraph_yolo/train_paragraph_yolo.py`
- `paragraph_yolo/data.yaml`
- `OCR_method/extract_invoice_ocr.py`
- `OCR_method/OCR_FALLBACK.md`
- `OCR_method/requirements_ocr.txt`
- `Dataset_verification/visualize_labels.py`

## Planned Pipeline

### Stage 1. Region or Field Detection

Train an object detection model either:

- at field level, to detect targets such as `Client_Email`, `Client_Phone`, `Total`, and `Invoice_Number`
- or at region level, to detect broader classes such as `paragraph` and `table`

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

Current alternative detector:

- `ai/extraction/paragraph_yolo/`

This dataset uses two classes:

- `paragraph`
- `table`

Its training script:

- prepares a grouped train/validation split from the current data
- avoids leakage by keeping augmented versions of the same invoice in the same split
- trains YOLO on the prepared dataset

Main command:

```bash
python3 ai/extraction/paragraph_yolo/train_paragraph_yolo.py --epochs 20 --imgsz 960 --batch 4 --device mps --name paragraph_table
```

### Stage 2. OCR on Detected Regions

For each detected field or region:

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

When using the `paragraph` / `table` detector, this post-processing step becomes:

- run OCR on each detected paragraph or table crop
- merge the OCR text within the same crop
- apply field extraction rules on that crop only

This reduces confusion compared with full-page OCR because totals, invoice metadata, and product rows are no longer mixed together across the whole page.

### Experimental Track — OCR-Free End-to-End Generation (Donut)

```text
invoice image -> Donut (vision encoder + text decoder) -> JSON output
```

Reason:

We explored an OCR-free approach using Donut, which directly generates structured outputs from document images. Unlike traditional pipelines that separate OCR and extraction, this method learns layout, text recognition, and field mapping jointly. While promising, it requires more data and computational resources, making it suitable as an experimental extension rather than a replacement in our system.

This track is fundamentally different from all three others because it contains **no OCR step at all**:

| Step | OCR Method | YOLO + OCR | Paragraph + OCR | **Donut** |
|---|---|---|---|---|
| OCR | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| Bounding boxes | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| End-to-end learning | ❌ No | ❌ No | ❌ No | ✅ Yes |

Donut combines a vision encoder (Swin Transformer) that reads the document image and a text decoder (BART-like) that generates the output token by token. Internally it learns reading, layout, and field meaning all at once — there is no intermediate text representation, so OCR errors cannot propagate.

Advantages:

- No OCR error propagation (`1450` never becomes `14S0`)
- No bounding box annotations required
- Simpler pipeline: image → JSON directly
- Most "human-like" understanding of layout and structure

Tradeoffs:

- Data hungry — needs many image + JSON label pairs
- Heavier to train — GPU strongly recommended
- Harder to debug — wrong output is just wrong JSON with no intermediate step

We use the pretrained `naver-clova-ix/donut-base` checkpoint from HuggingFace and lightly fine-tune it rather than training from scratch. For this experimental track we focus on a concise field subset: `invoice_number`, `date`, and `total`.

This track represents the natural next step in the project's pipeline evolution:

- Stage 1: Read then think (OCR + regex)
- Stage 2: Look then read (YOLO + OCR)
- Stage 3: End-to-end understanding (Donut)

Even if performance is lower than the other tracks on our small dataset, the comparison is academically meaningful because Donut may be more robust on invoices with unusual layouts and its error types differ fundamentally from OCR-based methods.

Implementation files:

- `Donut/donut_invoice_extraction.ipynb`
- `Donut/requirements.txt`
- `Donut/README.md`

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

- `ai/extraction/OCR_method/extract_invoice_ocr.py`

This fallback:

1. runs OCR on the full page
2. groups OCR tokens into lines
3. searches for anchor words such as `Invoice`, `Date`, `TTC`, `TVA`, `Email`, and `Tel`
4. applies regex and field-specific heuristics

This path is especially useful when:

- YOLO metrics are unstable
- training time is too long
- we need a baseline extractor quickly

## Paragraph/Table Detection Track

We added a second YOLO-based detection strategy under:

- `ai/extraction/paragraph_yolo/`

The idea is:

```text
invoice image -> detect paragraph/table blocks -> OCR per block -> extract fields from block text
```

Why this may help:

- the classes are broader and simpler than field-level detection
- OCR gets cleaner local context
- related information often stays inside the same detected block

Example use cases:

- detect a table block and extract product rows from it
- detect a paragraph block containing invoice metadata and extract invoice number, dates, email, or phone from that block only

Current note:

- the paragraph/table dataset originally contained only one split
- `train_paragraph_yolo.py` now creates a proper grouped train/validation split automatically

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

For the paragraph/table track, evaluation should also check:

- whether the correct logical block was detected
- whether OCR inside that block is cleaner than full-page OCR
- whether extracting fields from block-local text improves final accuracy

## Practical Project Plan

1. Verify annotations visually with `ai/extraction/Dataset_verification/visualize_labels.py`
2. Train either the field-level detector or the paragraph/table detector
3. Run inference on unseen invoices
4. Crop detected fields or regions and apply OCR
5. Normalize extracted values
6. Evaluate final field extraction quality

## Recommended Scope

For a realistic course project, the best scope is:

- train one detector variant that is stable enough to use
- apply OCR to detected regions
- demonstrate extraction of a subset of important fields

Two realistic implementation choices are:

- field-level detection + OCR
- paragraph/table detection + OCR + rule-based field extraction

Suggested priority fields:

- `Invoice_Number`
- `Invoice_Date`
- `Client_Name`
- `Client_Email`
- `Client_Phone`
- `Total`

This keeps the project focused while still demonstrating a complete document understanding pipeline.
