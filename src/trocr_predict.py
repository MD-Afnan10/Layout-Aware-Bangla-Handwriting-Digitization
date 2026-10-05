"""
Bangla TrOCR Inference Script (Step 03)
Loads the fine-tuned TrOCR model to predict Bangla text from word/line image crops.
"""

import os
import argparse
import json
from pathlib import Path
from PIL import Image
import torch
from transformers import ViTImageProcessor, AutoTokenizer, VisionEncoderDecoderModel

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
        image_files = [f for f in img_path.iterdir() if f.suffix.lower() in [".jpg", ".jpeg", ".png"]]
    else:
        image_files = [img_path]
        
    if not image_files:
        raise FileNotFoundError(f"No images found in {img_path}")
        
    print(f"Processing {len(image_files)} image(s)...")
    
    results = {}
    for img_file in image_files:
        image = Image.open(img_file).convert("RGB")
        pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
        
        # Generate text
        generated_ids = model.generate(pixel_values)
        generated_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
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
