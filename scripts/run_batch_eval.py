"""
Batch Pipeline & Evaluation Runner
Runs the full digitization pipeline across multiple diverse documents
and produces comprehensive layout (mIoU) and text (CER, WER, Accuracy) metrics.
"""

import os
import sys
import json
import argparse
from pathlib import Path
import torch
import cv2
from PIL import Image
from transformers import ViTImageProcessor, AutoTokenizer, VisionEncoderDecoderModel

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.predict import predict_layout
from src.export_rois import export_text_rois
from src.trocr_predict import segment_line_to_words
from src.utils.juktakkhor import restore_juktakkhor
from src.fusion import fuse_document
from src.export_docx import export_to_docx
from src.evaluate import (
    evaluate_digitized_document,
    evaluate_word_crops,
    print_evaluation_report
)

def run_pipeline_for_document(doc_name: str, yolo_model, trocr_processor, trocr_tokenizer, trocr_model, dataset_dir: str = "F:/DIP/Dataset", device: str = "cuda"):
    fid = doc_name.split("_")[0]
    img_path = Path(dataset_dir) / fid / f"{doc_name}.jpg"
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")
        
    outputs_dir = repo_root / "outputs" / doc_name
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n==================================================")
    print(f" PIPELINE EXECUTION: {doc_name} ({img_path.name})")
    print(f"==================================================")
    
    # 1. Layout detection
    print("[1/5] Predicting Layout with YOLOv8...")
    layout_results = predict_layout(
        image_path=str(img_path),
        model_path=str(repo_root / "weights" / "best_layout.pt"),
        output_dir=str(outputs_dir),
        device=device
    )
    layout_json_path = layout_results[0][0]
    
    # 2. Extract crops
    print("[2/5] Extracting Line ROIs...")
    crops_dir = export_text_rois(
        image_path=str(img_path),
        model_path=str(repo_root / "weights" / "best_layout.pt"),
        output_crops_dir=str(outputs_dir / "crops"),
        device=device
    )
    
    # 3. TrOCR Recognition
    print("[3/5] Running TrOCR Sequence Recognition & Juktakkhor Normalization...")
    crop_files = sorted([f for f in crops_dir.glob("*.jpg") if f.is_file()])
    predictions = {}
    
    for c_file in crop_files:
        cv_img = cv2.imread(str(c_file))
        if cv_img is None:
            continue
        word_crops = segment_line_to_words(cv_img)
        recognized_words = []
        for w_crop in word_crops:
            pil_w = Image.fromarray(cv2.cvtColor(w_crop, cv2.COLOR_BGR2RGB))
            pv = trocr_processor(pil_w, return_tensors="pt").pixel_values.to(device)
            with torch.no_grad():
                gen_ids = trocr_model.generate(pv)
            w_text = trocr_tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
            if w_text:
                recognized_words.append(w_text)
        
        normalized_line = restore_juktakkhor(" ".join(recognized_words))
        predictions[c_file.name] = normalized_line
        
    pred_json_path = outputs_dir / "predictions.json"
    with open(pred_json_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)
        
    # 4. JSON Fusion
    print("[4/5] Fusing Layout and Text JSON...")
    fused_json = outputs_dir / f"{doc_name}_fused.json"
    fuse_document(
        layout_json_path=str(layout_json_path),
        trocr_json_path=str(pred_json_path),
        output_path=str(fused_json)
    )
    
    # 5. DOCX Export
    print("[5/5] Synthesizing Word Document...")
    final_docx = outputs_dir / f"{doc_name}_digitized.docx"
    export_to_docx(str(fused_json), str(final_docx))
    print(f"✓ Completed {doc_name} -> {final_docx.name}")


def main():
    parser = argparse.ArgumentParser(description="Batch Pipeline & Evaluation Runner")
    parser.add_argument("--docs", nargs="+", default=["1_1", "2_1", "3_1", "4_1", "5_1"], help="Documents to evaluate")
    parser.add_argument("--device", type=str, default="cuda", help="Execution device")
    parser.add_argument("--force-run", action="store_true", help="Force re-running pipeline even if outputs exist")
    args = parser.parse_args()
    
    device = args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu"
    print(f"Using Device: {device.upper()}")
    
    # Check which docs need pipeline execution
    docs_to_run = []
    for d in args.docs:
        fused = repo_root / "outputs" / d / f"{d}_fused.json"
        if not fused.exists() or args.force_run:
            docs_to_run.append(d)
            
    if docs_to_run:
        print(f"\nLoading TrOCR model onto {device.upper()} for documents: {docs_to_run}...")
        model_dir = str(repo_root / "weights" / "trocr_bangla")
        processor = ViTImageProcessor.from_pretrained(model_dir)
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(device)
        model.eval()
        
        for d in docs_to_run:
            run_pipeline_for_document(
                doc_name=d,
                yolo_model=None,
                trocr_processor=processor,
                trocr_tokenizer=tokenizer,
                trocr_model=model,
                device=device
            )
            
    # Run quantitative evaluation across all documents
    print("\n" + "=" * 65)
    print(" EXECUTING COMPREHENSIVE BENCHMARK EVALUATION")
    print("=" * 65)
    
    all_results = []
    for d in args.docs:
        res = evaluate_digitized_document(doc_name=d, dataset_dir="F:/DIP/Dataset", outputs_dir="outputs")
        all_results.append(res)
        
    print_evaluation_report(all_results)
    
    # Save unified evaluation JSON report
    report_file = repo_root / "outputs" / "evaluation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"📊 Saved unified multi-document evaluation report to: {report_file}")
    
    # Word crops evaluation
    doc_ids = sorted(list(set([d.split("_")[0] for d in args.docs])))
    w_eval = evaluate_word_crops(
        dataset_dir="F:/DIP/Dataset",
        model_dir="weights/trocr_bangla",
        doc_ids=doc_ids,
        device=device,
        max_samples=60
    )
    print("\n" + "=" * 65)
    print(" 🎯 AGGREGATED ISOLATED WORD-LEVEL RECOGNITION METRICS")
    print("=" * 65)
    print(f"  • Evaluated Document IDs:    {doc_ids}")
    print(f"  • Total Evaluated Words:    {w_eval.get('total_evaluated_words')}")
    print(f"  • Word Exact Accuracy:       {w_eval.get('word_exact_accuracy')}%")
    print(f"  • Character Accuracy:        {w_eval.get('character_accuracy')}%")
    print(f"  • Character Error Rate (CER):{w_eval.get('CER') * 100:.2f}%")
    print(f"  • Word Error Rate (WER):     {w_eval.get('WER') * 100:.2f}%")
    print("=" * 65 + "\n")
    

if __name__ == "__main__":
    main()
