#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAIN_SCRIPT="$ROOT_DIR/train_yolo.py"
RUNS_DIR="$ROOT_DIR/runs"

BASE_CHECKPOINT="$RUNS_DIR/invoice_fields/weights/best.pt"
STAGE1_NAME="invoice_fields_960_best"
STAGE2_NAME="invoice_fields_1280_from_960"
STAGE1_CHECKPOINT="$RUNS_DIR/$STAGE1_NAME/weights/best.pt"

if [[ ! -f "$BASE_CHECKPOINT" ]]; then
  echo "Base checkpoint not found: $BASE_CHECKPOINT"
  exit 1
fi

echo "Stage 1: fine-tune at 960 for 20 epochs"
python3 "$TRAIN_SCRIPT" \
  --checkpoint "$BASE_CHECKPOINT" \
  --imgsz 960 \
  --epochs 20 \
  --batch 2 \
  --device mps \
  --name "$STAGE1_NAME"

if [[ ! -f "$STAGE1_CHECKPOINT" ]]; then
  echo "Stage 1 finished but checkpoint not found: $STAGE1_CHECKPOINT"
  exit 1
fi

echo "Stage 2: fine-tune at 1280 for 20 epochs"
python3 "$TRAIN_SCRIPT" \
  --checkpoint "$STAGE1_CHECKPOINT" \
  --imgsz 1280 \
  --epochs 20 \
  --batch 2 \
  --device mps \
  --name "$STAGE2_NAME"

echo "Overnight training complete."
echo "Stage 1 run: $RUNS_DIR/$STAGE1_NAME"
echo "Stage 2 run: $RUNS_DIR/$STAGE2_NAME"
