"""
TrOCR Dataset Preparation (Step 03 in Project Architecture)
Maps word-level image crops from BN-HTRd to their ground-truth text annotations.
Generates a cleaned CSV manifest suitable for Hugging Face Datasets and TrOCR fine-tuning.
"""

import os
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import argparse

def find_dataset_root(dataset_root: str = None) -> Path:
    candidates = []
    if dataset_root:
        candidates.append(Path(dataset_root))
    candidates.extend([
        Path("f:/DIP/Dataset"),
        Path(__file__).resolve().parent.parent.parent / "Dataset",
        Path(__file__).resolve().parent.parent / "Dataset",
        Path(__file__).resolve().parent.parent / "BN-HTR_Dataset"
    ])
    for cand in candidates:
        if cand.exists():
            return cand.resolve()
    raise FileNotFoundError(f"Could not locate dataset in any of: {[str(c) for c in candidates]}")


def build_dataset_manifest(dataset_root: str = "f:/DIP/Dataset", output_csv: str = "data/trocr_dataset/train_manifest.csv"):
    root_path = find_dataset_root(dataset_root)
    print(f"Using dataset root: {root_path}")
    
    records = []
    missing_images = 0
    
    # Check if nested Kaggle structure exists
    kaggle_gt = root_path / "Recognition_Ground_Truth_Texts"
    kaggle_words = root_path / "Segmentation_Images" / "Words"
    
    if kaggle_gt.exists() and kaggle_words.exists():
        print(f"Detected Kaggle structure in {root_path}")
        xlsx_files = list(kaggle_gt.rglob("*.xlsx"))
        for xlsx_path in tqdm(xlsx_files, desc="Parsing Excel files"):
            try:
                df = pd.read_excel(xlsx_path)
                if 'Id' not in df.columns or 'Word' not in df.columns:
                    continue
                for _, row in df.iterrows():
                    crop_id = str(row['Id']).strip()
                    word_text = str(row['Word']).strip()
                    if not crop_id or not word_text or word_text == 'nan':
                        continue
                    parts = crop_id.split('_')
                    if len(parts) != 4:
                        continue
                    doc_id = parts[0]
                    page_dir = f"{parts[0]}_{parts[1]}"
                    line_dir = f"{parts[0]}_{parts[1]}_{parts[2]}"
                    img_path = kaggle_words / doc_id / page_dir / line_dir / f"{crop_id}.jpg"
                    if not img_path.exists():
                        img_path = kaggle_words / doc_id / page_dir / line_dir / f"{crop_id}.JPG"
                    if img_path.exists():
                        records.append({"image_path": str(img_path), "text": word_text})
                    else:
                        missing_images += 1
            except Exception as e:
                print(f"Error reading {xlsx_path}: {e}")
    else:
        # Direct document folder structure: <root>/<doc_id>/<doc_id>.xlsx and <root>/<doc_id>/Words/<page_id>/<crop_id>.JPG
        doc_dirs = [d for d in root_path.iterdir() if d.is_dir() and d.name.isdigit()]
        doc_dirs.sort(key=lambda x: int(x.name))
        print(f"Found {len(doc_dirs)} document directories in {root_path}")
        
        for doc_dir in tqdm(doc_dirs, desc="Parsing documents"):
            xlsx_files = list(doc_dir.glob("*.xlsx"))
            words_dir = doc_dir / "Words"
            if not xlsx_files or not words_dir.exists():
                continue
            
            for xlsx_path in xlsx_files:
                try:
                    df = pd.read_excel(xlsx_path)
                    if 'Id' not in df.columns or 'Word' not in df.columns:
                        continue
                    for _, row in df.iterrows():
                        crop_id = str(row['Id']).strip()
                        word_text = str(row['Word']).strip()
                        if not crop_id or not word_text or word_text == 'nan':
                            continue
                        parts = crop_id.split('_')
                        if len(parts) != 4:
                            continue
                        page_dir = f"{parts[0]}_{parts[1]}"
                        
                        img_path = words_dir / page_dir / f"{crop_id}.JPG"
                        if not img_path.exists():
                            img_path = words_dir / page_dir / f"{crop_id}.jpg"
                        if not img_path.exists():
                            # fallback: line subdir
                            line_dir = f"{parts[0]}_{parts[1]}_{parts[2]}"
                            img_path = words_dir / page_dir / line_dir / f"{crop_id}.JPG"
                            if not img_path.exists():
                                img_path = words_dir / page_dir / line_dir / f"{crop_id}.jpg"
                                
                        if img_path.exists():
                            records.append({"image_path": str(img_path), "text": word_text})
                        else:
                            missing_images += 1
                except Exception as e:
                    print(f"Error reading {xlsx_path}: {e}")
                    
    print(f"\nSuccessfully mapped {len(records)} word-image pairs.")
    if missing_images > 0:
        print(f"Note: {missing_images} images referenced in Excel could not be found on disk.")
        
    out_df = pd.DataFrame(records)
    out_csv_path = Path(output_csv).resolve()
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_csv_path, index=False, encoding='utf-8')
    print(f"Manifest saved to: {out_csv_path}")
    return out_csv_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare TrOCR dataset mapping.")
    parser.add_argument("--dataset-dir", type=str, default="f:/DIP/Dataset", help="Root of BN-HTRd dataset.")
    parser.add_argument("--output-csv", type=str, default="data/trocr_dataset/train_manifest.csv", help="Output CSV path.")
    args = parser.parse_args()
    
    build_dataset_manifest(args.dataset_dir, args.output_csv)
