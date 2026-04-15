#!/usr/bin/env python3
"""Run YOLO detection on a new invoice image and save the labeled result."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "runs" / "invoice_fields_960_best2" / "weights" / "best.pt"
DEFAULT_OUTPUT = ROOT / "real_invoice_labeling"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict invoice fields on a new image with YOLO.")
    parser.add_argument("--image", type=Path, required=True, help="Path to the invoice image.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="Path to a YOLO .pt checkpoint.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--name", default="new_invoice", help="Output subfolder name.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.image.exists():
        raise SystemExit(f"Image not found: {args.image}")
    if not args.model.exists():
        raise SystemExit(f"Model not found: {args.model}")

    from ultralytics import YOLO

    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(args.model))
    model.predict(
        source=str(args.image),
        save=True,
        project=str(DEFAULT_OUTPUT),
        name=args.name,
        conf=args.conf,
    )

    print(f"Saved labeled result under {DEFAULT_OUTPUT / args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
