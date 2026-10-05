import sys
import argparse
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.export_docx import export_to_docx

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export fused JSON to DOCX")
    parser.add_argument("--input", type=str, required=True, help="Path to fused JSON (Step 4)")
    parser.add_argument("--output", type=str, required=True, help="Path for output .docx file")
    args = parser.parse_args()
    
    export_to_docx(args.input, args.output)
