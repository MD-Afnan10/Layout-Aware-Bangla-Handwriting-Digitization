"""
Bangla TrOCR Inference Script (Step 03)
Loads the fine-tuned TrOCR model to predict Bangla text from word/line image crops.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
import argparse
import json
from pathlib import Path
from PIL import Image
import torch
from transformers import ViTImageProcessor, AutoTokenizer, VisionEncoderDecoderModel

import cv2
import numpy as np

try:
    from src.utils.juktakkhor import restore_juktakkhor
except ModuleNotFoundError:
    from utils.juktakkhor import restore_juktakkhor

def segment_line_to_words(cv_img):
    """
    Segments a wide text line into word bounding boxes using adaptive horizontal morphology.
    Tuned to preserve individual words without merging closely-spaced handwriting into multi-word blobs.
    """
    h, w = cv_img.shape[:2]
    if w / max(1, h) < 1.6:
        return [cv_img]
        
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Adaptive kernel: connects intra-word strokes while strictly preventing inter-word bridging
    k_w = max(6, int(h * 0.12))
    k_h = max(2, int(h * 0.04))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_w, k_h))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    min_w = max(12, int(h * 0.14))
    min_h = max(12, int(h * 0.14))
    for c in contours:
        bx, by, bw, bh = cv2.boundingRect(c)
        if bw >= min_w and bh >= min_h:
            boxes.append((bx, by, bw, bh))
            
    if not boxes:
        return [cv_img]
        
    boxes.sort(key=lambda b: b[0])
    word_crops = []
    pad = 4
    for bx, by, bw, bh in boxes:
        y1 = max(0, by - pad)
        y2 = min(h, by + bh + pad)
        x1 = max(0, bx - pad)
        x2 = min(w, bx + bw + pad)
        word_crops.append(cv_img[y1:y2, x1:x2])
        
    return word_crops

def predict_text(
    image_path: str,
    model_dir: str = "weights/trocr_bangla",
    output_dir: str = "outputs/trocr_results",
    device: str = "cpu"
):
    img_path = Path(image_path).resolve()
    model_path = Path(model_dir).resolve()
    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    
    if str(device).isdigit():
        device = f"cuda:{device}"
    
    if not model_path.exists():
        print(f"[WARNING] Trained model not found at {model_path}.")
        print("Please run trocr_train.py first!")
        return
        
    print(f"Loading TrOCR processors and model from: {model_dir}")
    processor = ViTImageProcessor.from_pretrained(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(device)
    
    # Determine input files
    if img_path.is_dir():
        image_files = sorted([f for f in img_path.iterdir() if f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
    else:
        image_files = [img_path]
        
    if not image_files:
        raise FileNotFoundError(f"No images found in {img_path}")
        
    print(f"Processing {len(image_files)} image(s)...")
    
    results = {}
    for img_file in image_files:
        cv_img = cv2.imread(str(img_file))
        if cv_img is None:
            continue
            
        word_crops = segment_line_to_words(cv_img)
        recognized_words = []
        for w_crop in word_crops:
            pil_w = Image.fromarray(cv2.cvtColor(w_crop, cv2.COLOR_BGR2RGB))
            pv = processor(pil_w, return_tensors="pt").pixel_values.to(device)
            gen_ids = model.generate(pv)
            w_text = tokenizer.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()
            if w_text:
                recognized_words.append(w_text)
                
        generated_text = restore_juktakkhor(" ".join(recognized_words))
        results[img_file.name] = generated_text
        print(f"[{img_file.name}] -> {generated_text}")
        
    # Save results to JSON
    out_json = out_root / "predictions.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"\nSaved all predictions to: {out_json}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TrOCR prediction on handwriting crops.")
    parser.add_argument("--image", type=str, required=True, help="Path to cropped image or folder of crops.")
    parser.add_argument("--model", type=str, default="weights/trocr_bangla", help="Path to fine-tuned TrOCR model.")
    parser.add_argument("--output-dir", type=str, default="outputs/trocr_results", help="Output directory for predictions.")
    parser.add_argument("--device", type=str, default="cpu", help="Device to use ('cpu' or 'cuda').")
    args = parser.parse_args()
    
    predict_text(args.image, args.model, args.output_dir, args.device)
