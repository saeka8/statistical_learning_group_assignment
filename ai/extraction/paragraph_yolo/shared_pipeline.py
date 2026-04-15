from __future__ import annotations


CLASS_NAMES = {0: "paragraph", 1: "table"}
DEFAULT_PAD_RATIO = 0.02
DEFAULT_PAD_MIN = 12


def box_iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def containment_ratio(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    smaller = min(area_a, area_b)
    if smaller <= 0:
        return 0.0
    return inter_area / smaller


def filter_detections(
    detections: list[dict],
    dedup_iou: float = 0.6,
    containment_threshold: float = 0.85,
    max_paragraphs: int = 12,
    max_tables: int = 3,
    add_region_index: bool = False,
) -> list[dict]:
    kept: list[dict] = []
    counts = {"paragraph": 0, "table": 0}

    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        label = detection["label"]
        limit = max_tables if label == "table" else max_paragraphs
        if counts[label] >= limit:
            continue

        duplicate = False
        for existing in kept:
            if existing["label"] != label:
                continue
            if box_iou(existing["xyxy"], detection["xyxy"]) >= dedup_iou:
                duplicate = True
                break
            if containment_ratio(existing["xyxy"], detection["xyxy"]) >= containment_threshold:
                duplicate = True
                break
        if duplicate:
            continue

        kept.append(detection)
        counts[label] += 1

    kept.sort(key=lambda item: (item["xyxy"][1], item["xyxy"][0]))
    if add_region_index:
        for index, detection in enumerate(kept, start=1):
            detection["region_index"] = index
    return kept


def padded_box(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    image_width: int,
    image_height: int,
    pad_ratio: float = DEFAULT_PAD_RATIO,
    pad_min: int = DEFAULT_PAD_MIN,
) -> tuple[int, int, int, int]:
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    pad_x = max(pad_min, int(round(width * pad_ratio)))
    pad_y = max(pad_min, int(round(height * pad_ratio)))
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(image_width, x2 + pad_x),
        min(image_height, y2 + pad_y),
    )
