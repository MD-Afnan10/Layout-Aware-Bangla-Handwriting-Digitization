"""
Bangla TrOCR Training Script (Step 03)
Fine-tunes a Vision-Encoder-Decoder model on the prepared word-crop dataset.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
from pathlib import Path
import argparse
import pandas as pd
import numpy as np
import torch
from datasets import Dataset
from PIL import Image
from transformers import (
    ViTImageProcessor,
    AutoTokenizer,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    default_data_collator
)
import jiwer

# Define globally for metrics compute
processor = None
tokenizer = None

def compute_metrics(pred):
    labels_ids = pred.label_ids
    pred_ids = pred.predictions

    if isinstance(pred_ids, tuple):
        pred_ids = pred_ids[0]

    # Replace -100 in labels so we can decode
    labels_ids = np.where(labels_ids != -100, labels_ids, tokenizer.pad_token_id)
    pred_ids = np.where(pred_ids != -100, pred_ids, tokenizer.pad_token_id)

    pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    labels_str = tokenizer.batch_decode(labels_ids, skip_special_tokens=True)

    cer = jiwer.cer(reference=labels_str, hypothesis=pred_str)
    return {"cer": cer}


def train_trocr(
    csv_path: str,
    output_dir: str = "weights/trocr_bangla",
    epochs: int = 5,
    batch_size: int = 4,
    max_samples: int = None,
    from_pretrained: str = None,
    learning_rate: float = 5e-5
):
    global processor, tokenizer
    
    if from_pretrained and Path(from_pretrained).exists() and (Path(from_pretrained) / "config.json").exists():
        print(f"Loading existing fine-tuned checkpoint from: {from_pretrained}")
        processor = ViTImageProcessor.from_pretrained(from_pretrained)
        tokenizer = AutoTokenizer.from_pretrained(from_pretrained)
        model = VisionEncoderDecoderModel.from_pretrained(from_pretrained)
    else:
        print("Loading ViT encoder and Bangla BERT decoder...")
        encoder_id = "google/vit-base-patch16-224-in21k"
        decoder_id = "sagorsarker/bangla-bert-base"
        processor = ViTImageProcessor.from_pretrained(encoder_id)
        tokenizer = AutoTokenizer.from_pretrained(decoder_id)
        model = VisionEncoderDecoderModel.from_encoder_decoder_pretrained(encoder_id, decoder_id)
    
    # Configure model parameters for TrOCR
    model.config.decoder_start_token_id = tokenizer.cls_token_id
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size

    # Generation parameters configured on generation_config (compatible with Transformers 5.x)
    model.generation_config.decoder_start_token_id = tokenizer.cls_token_id
    model.generation_config.pad_token_id = tokenizer.pad_token_id
    model.generation_config.eos_token_id = tokenizer.sep_token_id
    model.generation_config.max_length = 32
    model.generation_config.num_beams = 1
    model.generation_config.early_stopping = False
    model.generation_config.length_penalty = 1.0
    model.generation_config.no_repeat_ngram_size = 3

    print(f"Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path).dropna()
    if max_samples and max_samples < len(df):
        print(f"Subsampling dataset to {max_samples} samples...")
        df = df.sample(n=max_samples, random_state=42).reset_index(drop=True)
    
    hf_dataset = Dataset.from_pandas(df)
    hf_dataset = hf_dataset.train_test_split(test_size=0.1, seed=42)
    train_ds = hf_dataset['train']
    eval_ds = hf_dataset['test']

    def preprocess_batch(batch):
        # Read images
        images = [Image.open(path).convert("RGB") for path in batch["image_path"]]
        pixel_values = processor(images, return_tensors="pt").pixel_values
        
        # Tokenize text natively in Bangla
        labels = tokenizer(
            batch["text"], 
            padding="max_length", 
            max_length=64, 
            truncation=True
        ).input_ids
        
        # Replace pad token with -100 to ignore in loss
        labels = [
            [token if token != tokenizer.pad_token_id else -100 for token in label]
            for label in labels
        ]
        
        batch["pixel_values"] = pixel_values
        batch["labels"] = labels
        return batch

    print("Preprocessing training data...")
    train_ds.set_transform(preprocess_batch)
    print("Preprocessing evaluation data...")
    eval_ds.set_transform(preprocess_batch)

    use_cuda = torch.cuda.is_available()
    print(f"CUDA Available: {use_cuda}, using fp16={use_cuda}")

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        predict_with_generate=True,
        eval_strategy="epoch",
        remove_unused_columns=False,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        fp16=use_cuda,
        dataloader_num_workers=0,
        logging_steps=20,
        save_strategy="epoch",
        num_train_epochs=epochs,
        save_total_limit=2,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        compute_metrics=compute_metrics,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=default_data_collator,
    )

    print("Starting TrOCR Fine-tuning...")
    trainer.train()
    
    print(f"Saving final model to {output_dir}")
    trainer.save_model(output_dir)
    processor.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default="data/trocr_dataset/train_manifest.csv")
    parser.add_argument("--output", type=str, default="weights/trocr_bangla")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--max-samples", type=int, default=None, help="Limit number of samples.")
    parser.add_argument("--from-pretrained", type=str, default=None, help="Resume from checkpoint folder.")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate.")
    args = parser.parse_args()
    
    train_trocr(
        args.csv, 
        args.output, 
        epochs=args.epochs, 
        batch_size=args.batch, 
        max_samples=args.max_samples,
        from_pretrained=args.from_pretrained,
        learning_rate=args.lr
    )
