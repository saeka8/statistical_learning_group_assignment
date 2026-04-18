"""
Configurable parameters for the invoice image preprocessing pipeline.
"""

from dataclasses import dataclass


@dataclass
class PreprocessingConfig:
    # CLAHE — contrast-limited adaptive histogram equalisation
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: tuple[int, int] = (8, 8)

    # Gaussian background normalisation
    # Large sigma estimates the illumination envelope; dividing removes it.
    blur_sigma: float = 51.0

    # Optional binarisation step (off by default — grayscale is fine for Tesseract)
    adaptive_threshold: bool = False
    adaptive_block_size: int = 31   # must be odd and > 1
    adaptive_c: int = 10            # constant subtracted from mean
