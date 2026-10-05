import sys
import argparse
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.trocr_predict import predict_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, required=True, help="Image or folder of crops")
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()
    
    model_dir = str(repo_root / "weights" / "trocr_bangla")
    output_dir = str(repo_root / "outputs" / "trocr_results")
    
    predict_text(
        image_path=args.image,
        model_dir=model_dir,
        output_dir=output_dir,
        device=args.device
    )
