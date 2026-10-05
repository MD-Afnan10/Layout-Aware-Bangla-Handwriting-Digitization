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

def build_dataset_manifest(dataset_root: str, output_csv: str):
    root_path = Path(dataset_root).resolve()
    gt_dir = root_path / "Recognition_Ground_Truth_Texts"
    img_dir = root_path / "Segmentation_Images" / "Words"
    
    if not gt_dir.exists() or not img_dir.exists():
        raise FileNotFoundError(f"Ensure both Recognition_Ground_Truth_Texts and Segmentation_Images/Words exist in {root_path}")
        
    records = []
    
    print(f"Scanning ground truth Excel files in: {gt_dir}")
    # Find all xlsx files
    xlsx_files = list(gt_dir.rglob("*.xlsx"))
    print(f"Found {len(xlsx_files)} Excel files. Parsing mapping...")
    
    missing_images = 0
    
    for xlsx_path in tqdm(xlsx_files):
        try:
            df = pd.read_excel(xlsx_path)
            # Ensure required columns exist
            if 'Id' not in df.columns or 'Word' not in df.columns:
                continue
                
            for _, row in df.iterrows():
                crop_id = str(row['Id']).strip()
                word_text = str(row['Word']).strip()
                
                if not crop_id or not word_text or word_text == 'nan':
                    continue
                    
                # crop_id format: DocID_PageID_LineID_WordID (e.g. 1_1_1_1)
                parts = crop_id.split('_')
                if len(parts) != 4:
                    continue
                    
                doc_id = parts[0]
                page_dir = f"{parts[0]}_{parts[1]}"
                line_dir = f"{parts[0]}_{parts[1]}_{parts[2]}"
                
                # Resolve physical image path
                # Format: Words/1/1_1/1_1_1/1_1_1_1.jpg
                img_path = img_dir / doc_id / page_dir / line_dir / f"{crop_id}.jpg"
                
                if img_path.exists():
                    records.append({
                        "image_path": str(img_path),
                        "text": word_text
                    })
                else:
                    missing_images += 1
        except Exception as e:
            print(f"Error reading {xlsx_path}: {e}")
            
    print(f"\nSuccessfully mapped {len(records)} word-image pairs.")
    if missing_images > 0:
        print(f"Note: {missing_images} images referenced in Excel could not be found on disk.")
        
    # Save to CSV
    out_df = pd.DataFrame(records)
    out_csv_path = Path(output_csv).resolve()
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_csv_path, index=False, encoding='utf-8')
    print(f"Manifest saved to: {out_csv_path}")
    
    return out_csv_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare TrOCR dataset mapping.")
    parser.add_argument("--dataset-dir", type=str, default="BN-HTR_Dataset", help="Root of BN-HTRd dataset.")
    parser.add_argument("--output-csv", type=str, default="data/trocr_dataset/train_manifest.csv", help="Output CSV path.")
    args = parser.parse_args()
    
    build_dataset_manifest(args.dataset_dir, args.output_csv)
