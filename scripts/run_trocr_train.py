import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.trocr_train import train_trocr

if __name__ == "__main__":
    csv_path = str(repo_root / "data" / "trocr_dataset" / "train_manifest.csv")
    output_dir = str(repo_root / "weights" / "trocr_bangla")
    
    train_trocr(
        csv_path=csv_path,
        output_dir=output_dir,
        epochs=5,
        batch_size=4
    )
