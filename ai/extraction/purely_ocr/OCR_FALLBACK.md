# OCR-First Fallback Pipeline

## Goal

This is the fallback path when the YOLO field detector is not reliable enough.

Pipeline:

```text
invoice image -> OCR over full page -> anchor/regex extraction -> structured JSON
```

## Why This Path

For invoices, this approach is often easier to finish than training a detector, especially if:

- layouts are varied but still contain recognizable keywords
- we only need a subset of fields
- we want a robust baseline quickly

It is weaker than detection plus OCR when layout changes a lot, but it is a practical course-project fallback.

## Implemented Script

Use:

- `ai/extraction/purely_ocr/extract_invoice_ocr.py`

It does:

1. run OCR on the full invoice image
2. group OCR tokens into lines
3. extract likely fields using:
   - anchor-based search first
   - regex fallback second
   - largest-amount fallback for total if needed

## Supported Fields

The script tries to extract:

- `Invoice_Number`
- `Invoice_Date`
- `Due_Date`
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

## OCR Engines

The script supports:

- `easyocr`
- `paddleocr`
- `pytesseract` with system Tesseract installed

Default mode:

- `--engine auto`

This tries:

1. `paddleocr`
2. `easyocr`
3. `pytesseract`

If `--engine auto` fails, the script now reports which engine failed and why.

## Install

Project-level OCR extras:

```bash
python3 -m pip install -r ai/extraction/purely_ocr/requirements_ocr.txt
```

If you want to use Tesseract:

- install the system `tesseract` binary separately

## Usage

Run on one invoice image:

```bash
python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image ai/extraction/image.png --pretty
```

Use a specific engine:

```bash
python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image ai/extraction/image.png --engine easyocr --pretty
```

Dump raw OCR tokens for debugging:

```bash
python3 ai/extraction/purely_ocr/extract_invoice_ocr.py --image ai/extraction/image.png --dump-ocr ocr_tokens.json --pretty
```

## Recommended Use

Use this path as:

1. a fallback baseline if YOLO continues to underperform
2. a comparison pipeline against YOLO plus OCR
3. a debugging tool to see whether fields are recoverable from OCR alone

## Practical Notes

- `Client_Email` and `Client_Phone` are good candidates for regex-first extraction.
- `Total`, `Invoice_Date`, and `Invoice_Number` should prefer anchor-based extraction.
- The "largest amount" heuristic is only a fallback and can be wrong.
- This script works on images, not raw PDFs. Convert PDFs to images first if needed.
