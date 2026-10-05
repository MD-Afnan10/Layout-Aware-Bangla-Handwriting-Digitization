# Bangla Handwriting Digitization - Teammate Guide

Hello! Tanveer and I have successfully built the entire end-to-end pipeline architecture as defined in your presentation slides. All scripts for Layout Analysis (Step 02), Text Recognition (Step 03), JSON Fusion (Step 04), and Document Export (Step 05) are fully written.

Since Tanveer does not have a dedicated NVIDIA GPU, **we need your help (and your RTX 2060) to complete the final pending task: Training the TrOCR model.**

---

## 🛠️ 1. Setup & Installation
Before starting, ensure your local repository is completely up to date.
1. Run `git pull` to get the latest scripts we just wrote.
2. Install the new dependencies required for TrOCR:
   ```bash
   pip install -r requirements.txt
   ```
3. Make sure the 3GB Kaggle dataset (`BN-HTR_Dataset`) is extracted at the root of the repository.

---

## 🚀 2. Your Mission: Train TrOCR (Step 03)
Because the presentation specifically highlighted **"Juktakkhor handling"**, we bypassed the default English TrOCR and built a custom Cross-Lingual architecture combining `google/vit-base-patch16-224-in21k` and `sagorsarker/bangla-bert-base`.

**Step A: Map the Dataset**
Run this command to map the ~104,000 image crops to their Excel ground truth text. It takes about 20 seconds.
```bash
python src/trocr_dataset.py
```
*(This will generate `data/trocr_dataset/train_manifest.csv`)*

**Step B: Start the Training**
Run the wrapper script to begin training on your GPU:
```bash
python scripts/run_trocr_train.py
```
*Note: The script is intentionally configured with `batch_size=4` to ensure it fits safely inside your RTX 2060's VRAM without crashing. This training will likely take 4 to 6 hours.*

**Step C: Send the Weights**
When the script finishes, it will save the fully trained model files into `weights/trocr_bangla/`. 
Please zip this folder up and send it to Tanveer!

---

## 🪄 3. The Final End-to-End Pipeline
Once the model is trained, the project is officially finished. We wrote a master script that ties everything together. 

To digitize a new, raw handwritten document, simply run:
```bash
python scripts/run_pipeline.py --image "path/to/raw_document.jpg" --device cuda
```
*(Or omit `--device cuda` to run on CPU).*

This master script will automatically:
1. Detect layout bounding boxes using your YOLO model.
2. Crop the text regions.
3. Read the text using the TrOCR model you are about to train.
4. Fuse the layout coordinates and text into a JSON map.
5. Export everything into a clean Microsoft Word `.docx` file!

Good luck with the training!
