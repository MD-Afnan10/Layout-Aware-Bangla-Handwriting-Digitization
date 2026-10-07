import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.trocr_train import train_trocr

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TrOCR training")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=4, help="Batch size per device")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional max sample limit")
    parser.add_argument("--output", type=str, default=str(repo_root / "weights" / "trocr_bangla"), help="Output directory")
    args = parser.parse_args()

    csv_path = str(repo_root / "data" / "trocr_dataset" / "train_manifest.csv")
    
    train_trocr(
        csv_path=csv_path,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        max_samples=args.max_samples
    )
