"""
Convenience CLI Script: Evaluate Full Digitization Pipeline
Calculates:
  - Layout Detection: Mean IoU (mIoU), Precision, Recall, F1-Score
  - OCR Text: Character Error Rate (CER), Word Error Rate (WER), Accuracy
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.evaluate import (
    evaluate_digitized_document,
    evaluate_word_crops,
    print_evaluation_report
)
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Evaluate Bangla HTR Digitization: IoU, CER, WER, Accuracy")
    parser.add_argument("--doc", type=str, default="all", help="Document to evaluate: '1_1', '2_1', or 'all'")
    parser.add_argument("--dataset", type=str, default="F:/DIP/Dataset", help="Path to ground truth dataset folder")
    parser.add_argument("--outputs", type=str, default="outputs", help="Path to pipeline outputs folder")
    parser.add_argument("--eval-words", action="store_true", help="Also evaluate pure isolated word crops directly on TrOCR")
    parser.add_argument("--device", type=str, default="cuda", help="Device for TrOCR ('cuda' or 'cpu')")
    parser.add_argument("--samples", type=int, default=100, help="Number of word samples for --eval-words")
    args = parser.parse_args()

    docs = ["1_1", "2_1"] if args.doc == "all" else [args.doc]
    results = []

    for d in docs:
        res = evaluate_digitized_document(
            doc_name=d,
            dataset_dir=args.dataset,
            outputs_dir=args.outputs
        )
        results.append(res)

    print_evaluation_report(results)

    # Save detailed JSON report
    report_file = Path(args.outputs) / "evaluation_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📊 Detailed report saved to: {report_file}")

    if args.eval_words:
        w_eval = evaluate_word_crops(
            dataset_dir=args.dataset,
            model_dir="weights/trocr_bangla",
            doc_ids=["1", "2"],
            device=args.device,
            max_samples=args.samples
        )
        print("\n" + "=" * 55)
        print(" 🎯 ISOLATED WORD-LEVEL RECOGNITION METRICS")
        print("=" * 55)
        print(f"  • Total Evaluated Words:    {w_eval.get('total_evaluated_words')}")
        print(f"  • Word Exact Accuracy:       {w_eval.get('word_exact_accuracy')}%")
        print(f"  • Character Accuracy:        {w_eval.get('character_accuracy')}%")
        print(f"  • Character Error Rate (CER):{w_eval.get('CER') * 100:.2f}%")
        print(f"  • Word Error Rate (WER):     {w_eval.get('WER') * 100:.2f}%")
        print("=" * 55 + "\n")

if __name__ == "__main__":
    main()
