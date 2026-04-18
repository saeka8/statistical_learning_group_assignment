from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pytesseract
from PIL import Image


MIN_TOKEN_CONFIDENCE = 0.3
COLUMN_GAP_FACTOR = 4.0


@dataclass
class OCRToken:
    text: str
    confidence: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def center_x(self) -> float:
        return (self.xmin + self.xmax) / 2.0

    @property
    def center_y(self) -> float:
        return (self.ymin + self.ymax) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.ymax - self.ymin)


@dataclass
class OCRLine:
    text: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    tokens: list[OCRToken]

    @property
    def center_y(self) -> float:
        return (self.ymin + self.ymax) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.ymax - self.ymin)


def filter_tokens(tokens: Iterable[OCRToken]) -> list[OCRToken]:
    filtered = [token for token in tokens if token.text and token.confidence > MIN_TOKEN_CONFIDENCE]
    filtered.sort(key=lambda token: (token.center_y, token.xmin))
    return filtered


def group_lines(tokens: list[OCRToken]) -> list[OCRLine]:
    if not tokens:
        return []

    heights = sorted(token.height for token in tokens)
    median_height = heights[len(heights) // 2]
    y_tolerance = max(6.0, median_height * 0.5)
    gap_threshold = median_height * COLUMN_GAP_FACTOR

    lines: list[list[OCRToken]] = []
    for token in tokens:
        placed = False
        for line_tokens in lines:
            avg_center_y = sum(item.center_y for item in line_tokens) / len(line_tokens)
            if abs(token.center_y - avg_center_y) > y_tolerance:
                continue
            line_xmin = min(item.xmin for item in line_tokens)
            line_xmax = max(item.xmax for item in line_tokens)
            if token.xmin > line_xmax + gap_threshold or token.xmax < line_xmin - gap_threshold:
                continue
            line_tokens.append(token)
            placed = True
            break
        if not placed:
            lines.append([token])

    grouped: list[OCRLine] = []
    for line_tokens in lines:
        line_tokens.sort(key=lambda token: token.xmin)
        grouped.append(
            OCRLine(
                text=" ".join(token.text for token in line_tokens).strip(),
                xmin=min(token.xmin for token in line_tokens),
                ymin=min(token.ymin for token in line_tokens),
                xmax=max(token.xmax for token in line_tokens),
                ymax=max(token.ymax for token in line_tokens),
                tokens=line_tokens,
            )
        )
    grouped.sort(key=lambda line: (line.center_y, line.xmin))
    return grouped


def ocr_pil_tesseract_tokens(image: Image.Image, lang: str = "eng+fra") -> list[OCRToken]:
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        output_type=pytesseract.Output.DICT,
    )
    tokens: list[OCRToken] = []
    for index, text in enumerate(data["text"]):
        text = str(text).strip()
        if not text:
            continue
        confidence = float(data["conf"][index])
        if confidence < 0:
            continue
        xmin = float(data["left"][index])
        ymin = float(data["top"][index])
        width = float(data["width"][index])
        height = float(data["height"][index])
        tokens.append(
            OCRToken(
                text=text,
                confidence=confidence / 100.0,
                xmin=xmin,
                ymin=ymin,
                xmax=xmin + width,
                ymax=ymin + height,
            )
        )
    return filter_tokens(tokens)


def ocr_pil_tesseract(image: Image.Image, lang: str = "eng+fra") -> list[OCRLine]:
    return group_lines(ocr_pil_tesseract_tokens(image, lang))
