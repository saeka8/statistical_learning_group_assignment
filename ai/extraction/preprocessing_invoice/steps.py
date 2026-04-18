"""
Individual preprocessing steps.

Each function is a pure transformation:
  - input : numpy uint8 array (grayscale or BGR depending on step)
  - output: numpy uint8 array
  - no side effects, no global state
"""

from __future__ import annotations

import cv2
import numpy as np


def to_lab_l(bgr: np.ndarray) -> np.ndarray:
    """Convert a BGR image to LAB colour space and return the L channel.

    The L channel captures luminance independently of colour, which makes
    subsequent contrast enhancement more stable on coloured invoice backgrounds.
    """
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l_channel, _, _ = cv2.split(lab)
    return l_channel


def apply_clahe(gray: np.ndarray, clip_limit: float, tile_grid_size: tuple[int, int]) -> np.ndarray:
    """Apply Contrast-Limited Adaptive Histogram Equalisation to a grayscale image.

    CLAHE boosts local contrast without over-amplifying noise in uniform regions
    (the clip limit caps the contrast enhancement per tile).
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray)


def normalize_background(gray: np.ndarray, sigma: float) -> np.ndarray:
    """Remove uneven background illumination via Gaussian-blur division.

    A heavily blurred copy of the image approximates the illumination envelope.
    Dividing the original by this estimate flattens the background so that text
    contrast is consistent across the whole page.

    The result is rescaled to [0, 255] uint8.
    """
    # (0, 0) ksize tells OpenCV to derive the kernel size from sigma
    background = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), sigma)
    normed = gray.astype(np.float32) / np.maximum(background, 1.0)
    normed = np.clip(normed * 128.0, 0.0, 255.0)
    return normed.astype(np.uint8)


def apply_adaptive_threshold(gray: np.ndarray, block_size: int, c: int) -> np.ndarray:
    """Binarise a grayscale image with adaptive Gaussian thresholding.

    Each pixel threshold is the Gaussian-weighted mean of its neighbourhood
    minus the constant `c`.  The block_size is forced to be odd.
    """
    block_size = block_size if block_size % 2 == 1 else block_size + 1
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )
