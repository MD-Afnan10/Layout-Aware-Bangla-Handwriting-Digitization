"""
Evaluation Module for Bangla Handwriting Digitization Pipeline
Computes:
  - Layout Detection: IoU (Intersection over Union), Mean IoU (mIoU), Precision@0.5, Recall@0.5, F1-Score
  - Text Recognition: Character Error Rate (CER), Word Error Rate (WER), Character Accuracy, Word Accuracy
  - Sequence Exact Match (EM)

Supports both:
  1. End-to-End Pipeline Evaluation (Layout + Text Fusion)
  2. Isolated Word-Level TrOCR Evaluation on Ground-Truth Crops
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict, Any, Union

import numpy as np
import pandas as pd
from PIL import Image

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import jiwer
    HAS_JIWER = True
except ImportError:
    HAS_JIWER = False

from src.utils.juktakkhor import restore_juktakkhor


# ==============================================================================
# 1. Levenshtein Distance & Error Rates (CER, WER)
# ==============================================================================

def levenshtein_distance(seq1: list, seq2: list) -> int:
    """Computes Levenshtein edit distance between two sequences (chars or words)."""
    m, n = len(seq1), len(seq2)
    dp = np.zeros((m + 1, n + 1), dtype=int)
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
        
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j],      # deletion
                                   dp[i][j - 1],      # insertion
                                   dp[i - 1][j - 1])  # substitution
    return dp[m][n]


def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    Calculates Character Error Rate (CER) = (S + D + I) / N_ref.
    Values range from 0.0 (perfect) upwards.
    """
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    if HAS_JIWER:
        return float(jiwer.cer(ref, hyp))
    
    dist = levenshtein_distance(list(ref), list(hyp))
    return float(dist / len(ref))


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculates Word Error Rate (WER) = (S + D + I) / N_ref_words.
    Values range from 0.0 (perfect) upwards.
    """
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    if HAS_JIWER:
        return float(jiwer.wer(" ".join(ref_words), " ".join(hyp_words)))
    
    dist = levenshtein_distance(ref_words, hyp_words)
    return float(dist / len(ref_words))


# ==============================================================================
# 2. Geometric Evaluation: IoU & Layout Metrics
# ==============================================================================

def compute_box_iou(boxA: List[Union[int, float]], boxB: List[Union[int, float]]) -> float:
    """
    Computes Intersection over Union (IoU) between two bounding boxes.
    Box format: [xmin, ymin, xmax, ymax]
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, float(xB - xA))
    inter_h = max(0.0, float(yB - yA))
    inter_area = inter_w * inter_h

    boxA_area = max(0.0, float(boxA[2] - boxA[0])) * max(0.0, float(boxA[3] - boxA[1]))
    boxB_area = max(0.0, float(boxB[2] - boxB[0])) * max(0.0, float(boxB[3] - boxB[1]))
    union_area = boxA_area + boxB_area - inter_area

    if union_area <= 0:
        return 0.0
    return float(inter_area / union_area)


def evaluate_boxes(
    pred_boxes: List[List[int]],
    gt_boxes: List[List[int]],
    iou_thresh: float = 0.50
) -> Dict[str, Any]:
    """
    Evaluates predicted bounding boxes against ground-truth boxes using greedy bipartite matching.
    Returns: mIoU, Precision@thresh, Recall@thresh, F1@thresh, and matched pairs.
    """
    if not gt_boxes and not pred_boxes:
        return {"mIoU": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "matches": []}
    if not gt_boxes or not pred_boxes:
        return {"mIoU": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "matches": []}

    matched_gt = set()
    matches = []
    tp = 0

    for p_idx, p_box in enumerate(pred_boxes):
        best_iou = 0.0
        best_g_idx = -1
        for g_idx, g_box in enumerate(gt_boxes):
            iou = compute_box_iou(p_box, g_box)
            if iou > best_iou:
                best_iou = iou
                best_g_idx = g_idx
                
        is_tp = False
        if best_iou >= iou_thresh and best_g_idx not in matched_gt:
            matched_gt.add(best_g_idx)
            tp += 1
            is_tp = True

        matches.append({
            "pred_idx": p_idx,
            "pred_box": p_box,
            "best_gt_idx": best_g_idx,
            "best_gt_box": gt_boxes[best_g_idx] if best_g_idx >= 0 else None,
            "iou": round(best_iou, 4),
            "is_true_positive": is_tp
        })

    all_ious = [m["iou"] for m in matches]
    miou = float(np.mean(all_ious)) if all_ious else 0.0
    precision = float(tp / len(pred_boxes)) if pred_boxes else 0.0
    recall = float(tp / len(gt_boxes)) if gt_boxes else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "mIoU": round(miou, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "total_preds": len(pred_boxes),
        "total_gts": len(gt_boxes),
        "true_positives": tp,
        "matches": matches
    }


# ==============================================================================
# 3. Ground Truth Loaders
# ==============================================================================

def load_xml_gt_boxes(xml_path: str) -> List[List[int]]:
    """Parses Pascal VOC XML annotation file to extract line bounding boxes."""
    path = Path(xml_path)
    if not path.exists():
        return []
    tree = ET.parse(str(path))
    boxes = []
    for b in tree.getroot().findall("object/bndbox"):
        boxes.append([
            int(float(b.find("xmin").text)),
            int(float(b.find("ymin").text)),
            int(float(b.find("xmax").text)),
            int(float(b.find("ymax").text))
        ])
    return boxes


def load_excel_gt_lines(xlsx_path: str, page_prefix: str) -> Dict[int, str]:
    """
    Extracts ordered ground truth line text from BN-HTRd Excel files.
    Example page_prefix: '1_1' or '2_1'
    """
    path = Path(xlsx_path)
    if not path.exists():
        return {}
    df = pd.read_excel(str(path))
    if "Id" not in df.columns or "Word" not in df.columns:
        return {}

    lines = {}
    for _, row in df.iterrows():
        crop_id = str(row["Id"]).strip()
        word = str(row["Word"]).strip()
        if not crop_id.startswith(page_prefix) or word == "nan" or not word:
            continue
        parts = crop_id.split("_")
        if len(parts) >= 3:
            try:
                line_idx = int(parts[2])
                lines.setdefault(line_idx, []).append(word)
            except ValueError:
                continue

    return {k: " ".join(words) for k, words in lines.items()}


# ==============================================================================
# 4. Pipeline Document Evaluation (End-to-End)
# ==============================================================================

def evaluate_digitized_document(
    doc_name: str,
    dataset_dir: str = "F:/DIP/Dataset",
    outputs_dir: str = "outputs"
) -> Dict[str, Any]:
    """
    Comprehensively evaluates an end-to-end digitized document:
      1. YOLO layout bounding boxes vs GT XML boxes -> IoU, mIoU, Precision, Recall, F1
      2. Digitized text vs GT Excel annotations -> CER, WER, Character Accuracy, Word Accuracy
    """
    dataset_root = Path(dataset_dir)
    outputs_root = Path(outputs_dir) / doc_name
    
    parts = doc_name.split("_")
    folder_id = parts[0] if parts else doc_name

    xml_path = dataset_root / folder_id / "Lines" / f"{doc_name}.xml"
    xlsx_path = dataset_root / folder_id / f"{folder_id}.xlsx"
    layout_json = outputs_root / f"{doc_name}_layout.json"
    fused_json = outputs_root / f"{doc_name}_fused.json"

    result = {
        "document_name": doc_name,
        "layout_metrics": {},
        "text_metrics": {},
        "per_line_breakdown": []
    }

    # A. Layout Evaluation (IoU)
    gt_boxes = load_xml_gt_boxes(str(xml_path))
    pred_boxes = []
    if layout_json.exists():
        with open(layout_json, "r", encoding="utf-8") as f:
            layout_data = json.load(f)
            pred_boxes = [r["bbox"] for r in layout_data.get("regions", [])]

    if gt_boxes or pred_boxes:
        layout_eval = evaluate_boxes(pred_boxes, gt_boxes, iou_thresh=0.50)
        result["layout_metrics"] = layout_eval

    # B. Text Evaluation (CER, WER)
    gt_lines = load_excel_gt_lines(str(xlsx_path), page_prefix=doc_name)
    pred_lines = {}
    if fused_json.exists():
        with open(fused_json, "r", encoding="utf-8") as f:
            fused_data = json.load(f)
            for r in fused_data.get("regions", []):
                order = int(r.get("reading_order", len(pred_lines) + 1))
                pred_lines[order] = r.get("text", "").strip()

    # Per-line evaluation
    line_keys = sorted(set(list(gt_lines.keys()) + list(pred_lines.keys())))
    total_ref_chars = 0
    total_ref_words = 0
    exact_matches = 0

    all_refs = []
    all_hyps = []

    for l_idx in line_keys:
        ref = gt_lines.get(l_idx, "")
        hyp = pred_lines.get(l_idx, "")
        hyp_norm = restore_juktakkhor(hyp)

        line_cer = calculate_cer(ref, hyp_norm) if ref else 0.0
        line_wer = calculate_wer(ref, hyp_norm) if ref else 0.0
        is_em = (ref.strip() == hyp_norm.strip()) and bool(ref)
        if is_em:
            exact_matches += 1

        all_refs.append(ref)
        all_hyps.append(hyp_norm)

        total_ref_chars += len(ref)
        total_ref_words += len(ref.split())

        result["per_line_breakdown"].append({
            "line_number": l_idx,
            "ground_truth": ref,
            "predicted": hyp_norm,
            "cer": round(line_cer, 4),
            "wer": round(line_wer, 4),
            "exact_match": is_em
        })

    full_ref_text = " ".join([r for r in all_refs if r])
    full_hyp_text = " ".join([h for h in all_hyps if h])

    doc_cer = calculate_cer(full_ref_text, full_hyp_text)
    doc_wer = calculate_wer(full_ref_text, full_hyp_text)
    char_acc = max(0.0, 1.0 - doc_cer)
    word_acc = max(0.0, 1.0 - doc_wer)
    em_rate = float(exact_matches / len(gt_lines)) if gt_lines else 0.0

    result["text_metrics"] = {
        "CER": round(doc_cer, 4),
        "WER": round(doc_wer, 4),
        "character_accuracy": round(char_acc * 100, 2),
        "word_accuracy": round(word_acc * 100, 2),
        "line_exact_match_rate": round(em_rate * 100, 2),
        "total_lines_gt": len(gt_lines),
        "total_lines_pred": len(pred_lines),
        "exact_match_lines": exact_matches
    }

    return result


# ==============================================================================
# 5. Isolated Word Crop Evaluation (Pure Model Capabilities)
# ==============================================================================

def evaluate_word_crops(
    dataset_dir: str = "F:/DIP/Dataset",
    model_dir: str = "weights/trocr_bangla",
    doc_ids: List[str] = None,
    device: str = "cpu",
    max_samples: int = 100
) -> Dict[str, Any]:
    """
    Evaluates the 5-epoch TrOCR model directly on ground-truth isolated word crops
    from the dataset to measure intrinsic model character & word accuracy.
    """
    from transformers import ViTImageProcessor, AutoTokenizer, VisionEncoderDecoderModel
    import torch

    device_str = "cuda" if (device == "cuda" and torch.cuda.is_available()) else "cpu"
    print(f"\n[Evaluating Isolated Word Crops on {device_str.upper()}]")
    print(f"Loading TrOCR model from: {model_dir}")
    processor = ViTImageProcessor.from_pretrained(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(device_str)
    model.eval()

    dataset_root = Path(dataset_dir)
    records = []

    target_docs = doc_ids or ["1", "2"]
    for d_id in target_docs:
        xlsx_file = dataset_root / d_id / f"{d_id}.xlsx"
        words_folder = dataset_root / d_id / "Words"
        if not xlsx_file.exists() or not words_folder.exists():
            continue
        df = pd.read_excel(str(xlsx_file))
        for _, row in df.iterrows():
            crop_id = str(row["Id"]).strip()
            word_gt = str(row["Word"]).strip()
            if not crop_id or not word_gt or word_gt == "nan":
                continue
            parts = crop_id.split("_")
            if len(parts) < 3:
                continue
            # Search for image file
            page_dir = f"{parts[0]}_{parts[1]}"
            img_candidates = list(words_folder.rglob(f"{crop_id}.*"))
            if img_candidates:
                records.append({
                    "id": crop_id,
                    "img_path": str(img_candidates[0]),
                    "ground_truth": word_gt
                })

    if not records:
        print("[WARNING] No word crops found for evaluation.")
        return {}

    if max_samples and len(records) > max_samples:
        records = records[:max_samples]

    print(f"Evaluating {len(records)} ground-truth word images...")
    exact_matches = 0
    all_refs = []
    all_hyps = []

    for rec in records:
        im = Image.open(rec["img_path"]).convert("RGB")
        pv = processor(im, return_tensors="pt").pixel_values.to(device_str)
        with torch.no_grad():
            gen_ids = model.generate(pv)
        pred_raw = tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
        pred_norm = restore_juktakkhor(pred_raw)

        gt = rec["ground_truth"]
        all_refs.append(gt)
        all_hyps.append(pred_norm)

        if gt == pred_norm:
            exact_matches += 1

    ref_blob = " ".join(all_refs)
    hyp_blob = " ".join(all_hyps)

    cer = calculate_cer(ref_blob, hyp_blob)
    wer = calculate_wer(ref_blob, hyp_blob)
    acc = float(exact_matches / len(records)) * 100

    return {
        "total_evaluated_words": len(records),
        "exact_matches": exact_matches,
        "word_exact_accuracy": round(acc, 2),
        "CER": round(cer, 4),
        "WER": round(wer, 4),
        "character_accuracy": round(max(0.0, 1.0 - cer) * 100, 2)
    }


# ==============================================================================
# 6. Beautiful CLI Output Display
# ==============================================================================

def print_evaluation_report(results: List[Dict[str, Any]]):
    """Prints a structured ASCII markdown table summarizing the evaluation results."""
    print("\n" + "=" * 78)
    print(" 🇧🇩 BANGLA HTR SYSTEM EVALUATION REPORT")
    print("=" * 78)

    for res in results:
        doc = res.get("document_name", "Document")
        lm = res.get("layout_metrics", {})
        tm = res.get("text_metrics", {})

        print(f"\n📄 Document: {doc}")
        print("-" * 78)
        
        # Layout section
        print("  [Stage 1: Layout Detection (YOLOv8)]")
        if lm:
            print(f"    • Mean IoU (mIoU):       {lm.get('mIoU', 0) * 100:6.2f}%")
            print(f"    • Precision @ 0.50 IoU:  {lm.get('precision', 0) * 100:6.2f}%")
            print(f"    • Recall @ 0.50 IoU:     {lm.get('recall', 0) * 100:6.2f}%")
            print(f"    • F1-Score:              {lm.get('f1', 0):6.4f}")
            print(f"    • Regions Detected:      {lm.get('total_preds', 0)} / {lm.get('total_gts', 0)} Ground Truth")
        else:
            print("    • No layout ground-truth annotations found.")

        # Text section
        print("\n  [Stage 2: Text Recognition & Juktakkhor Normalization (TrOCR)]")
        if tm:
            print(f"    • Character Error Rate (CER): {tm.get('CER', 0) * 100:6.2f}%")
            print(f"    • Character Accuracy:         {tm.get('character_accuracy', 0):6.2f}%")
            print(f"    • Word Error Rate (WER):      {tm.get('WER', 0) * 100:6.2f}%")
            print(f"    • Word Accuracy:              {tm.get('word_accuracy', 0):6.2f}%")
            print(f"    • Line Exact Matches:         {tm.get('exact_match_lines', 0)} / {tm.get('total_lines_gt', 0)} ({tm.get('line_exact_match_rate', 0)}%)")
        else:
            print("    • No text annotations found.")
        print("-" * 78)
    print("=" * 78 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Layout and HTR Model Accuracy (IoU, CER, WER)")
    parser.add_argument("--doc", type=str, default="1_1", help="Document to evaluate (e.g. '1_1' or '2_1')")
    parser.add_argument("--dataset", type=str, default="F:/DIP/Dataset", help="Root directory of dataset")
    parser.add_argument("--outputs", type=str, default="outputs", help="Root directory of outputs")
    parser.add_argument("--eval-words", action="store_true", help="Also evaluate pure isolated word crops")
    parser.add_argument("--device", type=str, default="cuda", help="Device for word crop evaluation ('cpu' or 'cuda')")
    args = parser.parse_args()

    # Document-level evaluation
    docs = [args.doc] if args.doc != "all" else ["1_1", "2_1"]
    all_results = []
    for d in docs:
        r = evaluate_digitized_document(d, args.dataset, args.outputs)
        all_results.append(r)

    print_evaluation_report(all_results)

    # Save detailed report
    out_rep = Path(args.outputs) / "evaluation_report.json"
    with open(out_rep, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Detailed evaluation metrics saved to: {out_rep}")

    # Optional: Isolated Word Evaluation
    if args.eval_words:
        w_eval = evaluate_word_crops(
            dataset_dir=args.dataset,
            doc_ids=["1", "2"],
            device=args.device,
            max_samples=100
        )
        print("\n=== ISOLATED WORD-LEVEL RECOGNITION METRICS ===")
        print(f"  • Evaluated Crops:    {w_eval.get('total_evaluated_words')}")
        print(f"  • Word Exact Match:   {w_eval.get('word_exact_accuracy')}%")
        print(f"  • Character Accuracy: {w_eval.get('character_accuracy')}%")
        print(f"  • CER:                {w_eval.get('CER') * 100:.2f}%")
        print(f"  • WER:                {w_eval.get('WER') * 100:.2f}%")
