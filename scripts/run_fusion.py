import sys
import argparse
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.fusion import fuse_document

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run JSON Fusion")
    parser.add_argument("--layout", type=str, required=True, help="Path to layout JSON (from Step 2)")
    parser.add_argument("--trocr", type=str, required=True, help="Path to TrOCR JSON (from Step 3)")
    parser.add_argument("--output", type=str, required=True, help="Path for fused JSON")
    args = parser.parse_args()
    
    fuse_document(args.layout, args.trocr, args.output)
