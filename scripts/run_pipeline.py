import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
from pathlib import Path
import json

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.predict import predict_layout
from src.export_rois import export_text_rois
from src.trocr_predict import predict_text
from src.fusion import fuse_document
from src.export_docx import export_to_docx

def run_end_to_end(image_path: str, device: str = "cpu"):
    img_path = Path(image_path).resolve()
    print(f"==================================================")
    print(f" BANGLA HTR END-TO-END PIPELINE")
    print(f" Processing: {img_path.name}")
    print(f"==================================================\n")
    
    # Define paths
    outputs_dir = repo_root / "outputs" / img_path.stem
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    layout_model = repo_root / "weights" / "best_layout.pt"
    trocr_model = repo_root / "weights" / "trocr_bangla"
    
    # ---------------------------------------------------------
    # STEP 02: Layout Analysis & ROI Extraction
    # ---------------------------------------------------------
    print("[Step 2] Running Layout Analysis (YOLOv8)...")
    layout_results = predict_layout(
        image_path=str(img_path),
        model_path=str(layout_model),
        output_dir=str(outputs_dir),
        device=device
    )
    
    layout_json_path = layout_results[0][0] # Path to the generated _layout.json
    print(f"[Step 2] Extracting Word Crops...")
    crops_dir = export_text_rois(
        image_path=str(img_path),
        model_path=str(layout_model),
        output_crops_dir=str(outputs_dir / "crops"),
        device=device
    )
    
    # ---------------------------------------------------------
    # STEP 03: Bangla Text Recognition (TrOCR)
    # ---------------------------------------------------------
    print("\n[Step 3] Running Bangla Text Recognition (TrOCR)...")
    if not (trocr_model / "config.json").exists():
        print(f"[WARNING] TrOCR model not found at {trocr_model}!")
        print("Falling back to dummy data for demonstration purposes...")
        # Create dummy predictions for the crops
        dummy_preds = {}
        for crop in crops_dir.glob("*.jpg"):
            dummy_preds[crop.name] = "[UNRECOGNIZED - TRAIN MODEL FIRST]"
        
        predictions_json = outputs_dir / "trocr_results.json"
        with open(predictions_json, "w", encoding="utf-8") as f:
            json.dump(dummy_preds, f, ensure_ascii=False, indent=2)
    else:
        trocr_results = predict_text(
            image_path=str(crops_dir),
            model_dir=str(trocr_model),
            output_dir=str(outputs_dir),
            device=device
        )
        predictions_json = outputs_dir / "predictions.json"

    # ---------------------------------------------------------
    # STEP 04: JSON Fusion
    # ---------------------------------------------------------
    print("\n[Step 4] Fusing Layout and Text JSONs...")
    fused_json = outputs_dir / f"{img_path.stem}_fused.json"
    fuse_document(
        layout_json_path=str(layout_json_path),
        trocr_json_path=str(predictions_json),
        output_path=str(fused_json)
    )

    # ---------------------------------------------------------
    # STEP 05: DOCX Export
    # ---------------------------------------------------------
    print("\n[Step 5] Exporting Final Digitized Word Document...")
    final_docx = outputs_dir / f"{img_path.stem}_digitized.docx"
    actual_saved = export_to_docx(
        fused_json_path=str(fused_json),
        output_docx_path=str(final_docx)
    )
    if actual_saved:
        final_docx = actual_saved
    
    print(f"\n==================================================")
    print(f" PIPELINE COMPLETE!")
    print(f" Final Document: {final_docx}")
    print(f"==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-End Pipeline for Bangla Digitization")
    parser.add_argument("--image", type=str, required=True, help="Path to input document image")
    parser.add_argument("--device", type=str, default="cpu", help="Device to use ('cpu' or 'cuda')")
    args = parser.parse_args()
    
    run_end_to_end(args.image, args.device)
