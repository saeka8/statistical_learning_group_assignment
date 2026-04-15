#!/usr/bin/env python3
"""Render training annotations into HTML overlays.

Examples:
  python3 Feature_Extraction_Invoice/visualize_labels.py --image 671_png_jpg.rf.p73UNqF5SQDjw12vTAI6.jpg
  python3 Feature_Extraction_Invoice/visualize_labels.py --sample 5
  python3 Feature_Extraction_Invoice/visualize_labels.py --image 671_png_jpg.rf.p73UNqF5SQDjw12vTAI6.jpg --open
"""

from __future__ import annotations

import argparse
import csv
import html
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TRAIN_DIR = ROOT / "train"
CSV_PATH = TRAIN_DIR / "_annotations.csv"
OUTPUT_DIR = ROOT / "label_previews"
PALETTE = [
    "#0b6e4f",
    "#c84c09",
    "#3366cc",
    "#a23b72",
    "#00838f",
    "#6a1b9a",
    "#ef6c00",
    "#2e7d32",
    "#ad1457",
    "#1565c0",
    "#5d4037",
    "#00897b",
    "#283593",
    "#d81b60",
    "#7b1fa2",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview object-detection boxes from train/_annotations.csv")
    parser.add_argument("--image", help="Image filename inside Feature_Extraction_Invoice/train")
    parser.add_argument("--sample", type=int, help="Render the first N annotated images")
    parser.add_argument("--open", action="store_true", help="Open generated preview files in the default browser")
    return parser


def load_annotations() -> tuple[dict[str, list[dict[str, float | str]]], Counter]:
    grouped: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    class_counts: Counter = Counter()

    with CSV_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"filename", "width", "height", "class", "xmin", "ymin", "xmax", "ymax"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        for row in reader:
            entry = {
                "filename": row["filename"],
                "width": float(row["width"]),
                "height": float(row["height"]),
                "class": row["class"],
                "xmin": float(row["xmin"]),
                "ymin": float(row["ymin"]),
                "xmax": float(row["xmax"]),
                "ymax": float(row["ymax"]),
            }
            grouped[row["filename"]].append(entry)
            class_counts[row["class"]] += 1

    return grouped, class_counts


def build_color_map(class_counts: Counter) -> dict[str, str]:
    return {label: PALETTE[idx % len(PALETTE)] for idx, label in enumerate(sorted(class_counts))}


def render_html(
    image_name: str,
    annotations: list[dict[str, float | str]],
    color_map: dict[str, str],
    output_path: Path,
) -> None:
    width = int(annotations[0]["width"])
    height = int(annotations[0]["height"])
    image_path = (TRAIN_DIR / image_name).resolve()

    rects = []
    rows = []
    for idx, box in enumerate(annotations, start=1):
        label = str(box["class"])
        xmin = float(box["xmin"])
        ymin = float(box["ymin"])
        xmax = float(box["xmax"])
        ymax = float(box["ymax"])
        color = color_map[label]
        label_width = max(120, len(label) * 9)
        rects.append(
            f"""
            <g>
              <rect x="{xmin}" y="{ymin}" width="{xmax - xmin}" height="{ymax - ymin}"
                    fill="none" stroke="{color}" stroke-width="4"/>
              <rect x="{xmin}" y="{max(0, ymin - 30)}" width="{label_width}" height="28"
                    fill="{color}" opacity="0.92"/>
              <text x="{xmin + 8}" y="{max(18, ymin - 10)}" fill="white">{html.escape(label)}</text>
            </g>
            """.strip()
        )
        rows.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{int(xmin)}</td><td>{int(ymin)}</td><td>{int(xmax)}</td><td>{int(ymax)}</td>"
            "</tr>"
        )

    legend = "".join(
        f'<span class="chip"><span class="swatch" style="background:{color_map[label]}"></span>{html.escape(label)}</span>'
        for label in sorted({str(item["class"]) for item in annotations})
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(image_name)} annotations</title>
  <style>
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, #f0ece2 0, transparent 32%),
        linear-gradient(180deg, #faf7f0 0, #f2ede2 100%);
      color: #1c1917;
      font-family: Georgia, "Times New Roman", serif;
    }}
    .page {{
      max-width: 1280px;
      margin: 24px auto;
      padding: 24px;
    }}
    .card {{
      background: rgba(255,255,255,0.92);
      border: 1px solid #d8d0c2;
      box-shadow: 0 16px 40px rgba(50, 40, 20, 0.08);
      padding: 20px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 15px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 14px;
      font-size: 14px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #f7f2e8;
      border: 1px solid #e2d8c5;
      padding: 4px 8px;
    }}
    .swatch {{
      width: 12px;
      height: 12px;
      display: inline-block;
    }}
    .viewer {{
      position: relative;
      width: min(100%, 1000px);
      aspect-ratio: {width} / {height};
      margin-top: 20px;
      border: 1px solid #d8d0c2;
      overflow: hidden;
      background: white;
    }}
    .viewer img, .viewer svg {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
      font-size: 14px;
    }}
    th, td {{
      padding: 8px 10px;
      border-top: 1px solid #e7dfd1;
      text-align: left;
    }}
    text {{
      font: 16px Georgia, "Times New Roman", serif;
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="card">
      <h1>{html.escape(image_name)}</h1>
      <div class="meta">
        <div><strong>Image</strong>: {html.escape(str(image_path))}</div>
        <div><strong>Canvas</strong>: {width} x {height}</div>
        <div><strong>Boxes</strong>: {len(annotations)}</div>
      </div>
      <div class="legend">{legend}</div>
      <div class="viewer">
        <img src="file://{image_path}" alt="{html.escape(image_name)}">
        <svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">
          {"".join(rects)}
        </svg>
      </div>
      <table>
        <thead>
          <tr><th>#</th><th>Class</th><th>xmin</th><th>ymin</th><th>xmax</th><th>ymax</th></tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""
    output_path.write_text(page, encoding="utf-8")


def open_file(path: Path) -> None:
    if Path("/usr/bin/open").exists():
        subprocess.run(["/usr/bin/open", str(path)], check=False)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.image and not args.sample:
        parser.error("pass --image <filename> or --sample <count>")

    annotations_by_image, class_counts = load_annotations()
    color_map = build_color_map(class_counts)
    OUTPUT_DIR.mkdir(exist_ok=True)

    targets = [args.image] if args.image else sorted(annotations_by_image)[: max(1, args.sample)]
    generated: list[Path] = []

    for image_name in targets:
        image_path = TRAIN_DIR / image_name
        if image_name not in annotations_by_image:
            print(f"Skip: no annotations found for {image_name}")
            continue
        if not image_path.exists():
            print(f"Skip: image file does not exist: {image_path}")
            continue

        output_path = OUTPUT_DIR / f"{Path(image_name).stem}.html"
        render_html(image_name, annotations_by_image[image_name], color_map, output_path)
        generated.append(output_path)
        print(f"Wrote {output_path}")

    print(f"CSV images: {len(annotations_by_image)}")
    print(f"CSV classes: {dict(class_counts)}")

    if args.open:
        for path in generated:
            open_file(path.resolve())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
