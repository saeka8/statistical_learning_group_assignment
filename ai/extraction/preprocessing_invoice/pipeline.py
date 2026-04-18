"""
Invoice image preprocessing pipeline.

Usage
-----
from ai.extraction.preprocessing_invoice.pipeline import preprocess_invoice_image

processed_img, steps = preprocess_invoice_image(pil_image)
# steps = ["lab_l", "clahe", "bg_normalize"]  (or [] on failure)
"""

from __future__ import annotations

import logging

import numpy as np
from PIL import Image

from .config import PreprocessingConfig
from .steps import (
    apply_adaptive_threshold,
    apply_clahe,
    normalize_background,
    to_lab_l,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = PreprocessingConfig()


def preprocess_invoice_image(
    image: Image.Image,
    config: PreprocessingConfig | None = None,
) -> tuple[Image.Image, list[str]]:
    """Preprocess a PIL Image for invoice OCR.

    Pipeline
    --------
    1. RGB → BGR → LAB → L channel  (luminance, independent of colour)
    2. CLAHE                          (local contrast enhancement)
    3. Gaussian background normalise  (divide by blurred background)
    4. Adaptive threshold             (optional, off by default)

    Parameters
    ----------
    image:
        Source PIL Image (any mode; internally converted to RGB).
    config:
        Preprocessing parameters.  Defaults to ``PreprocessingConfig()``.

    Returns
    -------
    (processed_image, applied_steps)
        ``processed_image`` is a PIL Image in RGB mode ready for OCR.
        ``applied_steps`` lists the step names that were executed.
        On any failure the *original* image is returned with an empty list.
    """
    if config is None:
        config = _DEFAULT_CONFIG

    applied: list[str] = []

    try:
        import cv2  # noqa: F401 — guard: if opencv is absent, fall back cleanly

        # PIL RGB → numpy BGR (cv2 convention)
        bgr = np.array(image.convert("RGB"))[:, :, ::-1].copy()

        # Step 1 — LAB → L channel
        gray = to_lab_l(bgr)
        applied.append("lab_l")

        # Step 2 — CLAHE
        gray = apply_clahe(gray, config.clahe_clip_limit, config.clahe_tile_grid_size)
        applied.append("clahe")

        # Step 3 — Background normalisation
        gray = normalize_background(gray, config.blur_sigma)
        applied.append("bg_normalize")

        # Step 4 — Adaptive threshold (optional)
        if config.adaptive_threshold:
            gray = apply_adaptive_threshold(
                gray, config.adaptive_block_size, config.adaptive_c
            )
            applied.append("adaptive_threshold")

        # Convert back to RGB PIL Image (Tesseract accepts both L and RGB)
        processed = Image.fromarray(gray, mode="L").convert("RGB")
        return processed, applied

    except Exception as exc:
        logger.warning("Invoice preprocessing failed (%s) — using original image", exc)
        return image, []
