"""
Document Export (Step 05)
Converts the fused JSON (layout + text) into a properly formatted Microsoft Word document.
"""

import json
import argparse
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def export_to_docx(fused_json_path: str, output_docx_path: str):
    json_path = Path(fused_json_path).resolve()
    out_path = Path(output_docx_path).resolve()
    
    if not json_path.exists():
        print(f"Error: Fused JSON not found at {json_path}")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    doc = Document()
    
    # Title
    doc_name = data.get("document_name", "Digitized Document")
    title = doc.add_heading(f"Digitized Document: {doc_name}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add some metadata
    meta = doc.add_paragraph()
    meta.add_run(f"Total Regions Detected: {data.get('total_regions', 0)}\n").italic = True
    
    doc.add_heading("Recognized Text", level=2)
    
    # Sort regions by reading order just in case they aren't already
    regions = data.get("regions", [])
    regions.sort(key=lambda x: x.get("reading_order", 0))
    
    for region in regions:
        text = region.get("text", "")
        # If there's text, add it as a paragraph
        if text.strip():
            p = doc.add_paragraph()
            run = p.add_run(text)
            
            # Formatting (Bangla text usually needs a slightly larger font for readability)
            run.font.size = Pt(14)
            
            # Optional: Add small margin/spacing if we want to mimic physical layout,
            # but for now, we just output it as clean text lines.
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    print(f"Successfully exported digitized document to: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export fused JSON to DOCX")
    parser.add_argument("--input", type=str, required=True, help="Path to fused JSON (Step 4)")
    parser.add_argument("--output", type=str, required=True, help="Path for output .docx file")
    args = parser.parse_args()
    
    export_to_docx(args.input, args.output)
