"""Download RVL-CDIP subset (4 categories) from Hugging Face."""
import os
from huggingface_hub import HfApi, hf_hub_download

REPO = "vaclavpechtor/rvl_cdip-small-200"
CATEGORIES = ["email", "invoice", "resume", "scientific_publication"]
SPLITS = ["train", "validation"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")

api = HfApi()
all_files = api.list_repo_files(REPO, repo_type="dataset")

# Filter to only our 4 categories
target_files = []
for f in all_files:
    for cat in CATEGORIES:
        if f"/{cat}/" in f and (f.startswith("train/") or f.startswith("validation/")):
            target_files.append(f)
            break

print(f"Found {len(target_files)} files to download")

for i, filepath in enumerate(target_files):
    # Create local directory structure
    local_dir = os.path.join(OUTPUT_DIR, os.path.dirname(filepath))
    os.makedirs(local_dir, exist_ok=True)
    
    local_path = os.path.join(OUTPUT_DIR, filepath)
    if os.path.exists(local_path):
        continue
    
    # Download
    downloaded = hf_hub_download(REPO, filepath, repo_type="dataset")
    
    # Copy to our data folder
    import shutil
    shutil.copy2(downloaded, local_path)
    
    if (i + 1) % 50 == 0 or i == 0:
        print(f"  [{i+1}/{len(target_files)}] {filepath}")

print("\nDone! Verifying...")
for split in SPLITS:
    for cat in CATEGORIES:
        cat_dir = os.path.join(OUTPUT_DIR, split, cat)
        if os.path.isdir(cat_dir):
            count = len(os.listdir(cat_dir))
            print(f"  {split}/{cat}: {count} images")
        else:
            print(f"  {split}/{cat}: MISSING")
