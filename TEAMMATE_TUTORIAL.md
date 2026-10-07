# 🇧🇩 Layout-Aware Bangla Handwriting Digitization
## Complete Teammate Guide: Setup, Model Weights, Pipeline Execution & Evaluation

Welcome to the **Layout-Aware Bangla Handwriting Digitization** project! This repository implements an end-to-end framework converting raw handwritten Bangla document scans into layout-preserved, editable Microsoft Word (`.docx`) documents.

---

## 📑 Table of Contents
1. [Pipeline Architecture (5 Stages)](#1-pipeline-architecture-5-stages)
2. [Environment Setup & Installation](#2-environment-setup--installation)
3. [Model Weights Setup (Not in Git)](#3-model-weights-setup-not-in-git)
4. [Running the End-to-End Digitization Pipeline](#4-running-the-end-to-end-digitization-pipeline)
5. [Running the Evaluation Suite (IoU, CER, WER, Accuracy)](#5-running-the-evaluation-suite-iou-cer-wer-accuracy)
6. [Bangla Juktakkhor (যুক্তাক্ষর) & Vowel Engine](#6-bangla-juktakkhor-যুক্তাক্ষর--vowel-engine)
7. [Adaptive Line-to-Word Segmentation](#7-adaptive-line-to-word-segmentation)
8. [Troubleshooting & FAQs](#8-troubleshooting--faqs)

---

## 1. Pipeline Architecture (5 Stages)

The system processes documents across five modular stages:

```
[Raw Document Image (.jpg/.png)]
               │
               ▼
┌─────────────────────────────────┐
│ Stage 1: OpenCV Preprocessing   │  -> Deskewing (Hough transform) & adaptive contrast
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Stage 2: Layout Detection       │  -> YOLOv8 detects text lines & reading order
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Stage 3: Text Recognition       │  -> ViT + Bangla BERT TrOCR recognizes words
│          & Juktakkhor Engine    │  -> Restores compound consonants & vowel signs
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Stage 4: Spatial-Text Fusion    │  -> Binds bounding boxes with normalized Bangla text
└─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Stage 5: Document Export        │  -> Generates formatted Microsoft Word (.docx)
└─────────────────────────────────┘     with 'Nirmala UI' font typography
```

---

## 2. Environment Setup & Installation

### A. Clone the Repository
```bash
git clone https://github.com/MD-Afnan10/Layout-Aware-Bangla-Handwriting-Digitization.git
cd Layout-Aware-Bangla-Handwriting-Digitization
```

### B. Create and Activate a Python Virtual Environment
We recommend **Python 3.10 or 3.11**:
```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### C. Install PyTorch with CUDA (or CPU)
- **If you have an NVIDIA GPU (RTX 2060, RTX 3060, GTX 1660, etc.)**:
  ```powershell
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  ```
- **If you only have a CPU**:
  ```powershell
  pip install torch torchvision
  ```

### D. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 3. Model Weights Setup (Not in Git)

> [!IMPORTANT]
> The trained model weights (`~1.1 GB`) are **intentionally excluded from Git** via `.gitignore` to prevent repository bloat and respect GitHub's 100MB file limit.

### A. Download the Trained Weights Package
Download `trocr_bangla_trained.zip` from our team Google Drive / OneDrive shared link:
- **Archive File**: `trocr_bangla_trained.zip` (~990 MB)

### B. Extract Weights into the Repository
Extract the zip file so that your local directory tree looks **exactly** like this:

```
Layout-Aware-Bangla-Handwriting-Digitization/
└── weights/
    ├── best_layout.pt                  # YOLOv8 line detection weights (~6 MB)
    └── trocr_bangla/                   # 5-Epoch Fine-tuned TrOCR model (~1.1 GB)
        ├── config.json
        ├── generation_config.json
        ├── model.safetensors           # Core weights (1,117,090,380 bytes)
        ├── preprocessor_config.json
        ├── tokenizer_config.json
        ├── tokenizer.json
        ├── training_args.bin
        └── vocab.txt
```

### C. Verify Weights Load Successfully
Run this 1-line sanity check in PowerShell/Terminal:
```powershell
python -c "from transformers import VisionEncoderDecoderModel; m = VisionEncoderDecoderModel.from_pretrained('weights/trocr_bangla'); print('Weights loaded successfully! Total params:', sum(p.numel() for p in m.parameters()))"
```
*Expected output: `Weights loaded successfully! Total params: 279256201`*

---

## 4. Running the End-to-End Digitization Pipeline

The master pipeline script executes all 5 stages in a single command.

### A. Run on an Image with GPU (CUDA)
```powershell
python scripts/run_pipeline.py --image "F:/DIP/Dataset/1/1_1.jpg" --device cuda
python scripts/run_pipeline.py --image "F:/DIP/Dataset/2/2_1.jpg" --device cuda
```

### B. Run on CPU (If no GPU is available)
```powershell
python scripts/run_pipeline.py --image "path/to/any_handwritten_document.jpg" --device cpu
```

### C. Generated Output Files
All outputs are automatically saved to `outputs/<document_name>/`:
- `<doc_name>_annotated.jpg`: Visual layout image showing detected line bounding boxes and reading order arrows.
- `<doc_name>_layout.json`: Extracted geometry, bounding box coordinates, and detection confidences.
- `crops/<doc_name>/`: Cropped line images for inspection.
- `predictions.json`: Text recognized for each region.
- `<doc_name>_fused.json`: Integrated document representation linking coordinates to recognized text.
- `<doc_name>_digitized.docx`: **The final Microsoft Word document** formatted with `Nirmala UI` font (14pt text, 1.25 line spacing).

---

## 5. Running the Evaluation Suite (IoU, CER, WER, Accuracy)

We built an evaluation suite in [`src/evaluate.py`](src/evaluate.py) and [`scripts/evaluate_pipeline.py`](scripts/evaluate_pipeline.py) to measure performance against ground truth.

### Evaluation Metrics Explained
- **Intersection over Union (IoU)**: Measures bounding box overlap between YOLO predictions and ground-truth Pascal VOC XML annotations (`Lines/*.xml`).
  $$\text{IoU} = \frac{\text{Area of Overlap}}{\text{Area of Union}}$$
  - **mIoU**: Mean IoU across all detected regions.
  - **Precision & Recall @ 0.50 IoU**: Percentage of correctly matched regions.
- **Character Error Rate (CER)**: Levenshtein edit distance on characters:
  $$\text{CER} = \frac{S + D + I}{N_{\text{characters}}}$$
  $$\text{Character Accuracy} = (1 - \text{CER}) \times 100\%$$
- **Word Error Rate (WER)**: Levenshtein edit distance on word tokens:
  $$\text{WER} = \frac{S_w + D_w + I_w}{N_{\text{words}}}$$
  $$\text{Word Accuracy} = (1 - \text{WER}) \times 100\%$$

### A. Evaluate All Documents in the Pipeline
```powershell
python scripts/evaluate_pipeline.py --doc all
```

### B. Evaluate a Specific Document
```powershell
python scripts/evaluate_pipeline.py --doc 1_1
python scripts/evaluate_pipeline.py --doc 2_1
```

### C. Evaluate Pure Isolated Word Crops on TrOCR
Tests the 5-epoch model directly on ground-truth single-word images from `Dataset/*/Words`:
```powershell
python scripts/evaluate_pipeline.py --eval-words --samples 100 --device cuda
```

### Benchmark Results Reference
```
==============================================================================
 🇧🇩 BANGLA HTR SYSTEM EVALUATION REPORT
==============================================================================

📄 Document: 1_1
------------------------------------------------------------------------------
  [Stage 1: Layout Detection (YOLOv8)]
    • Mean IoU (mIoU):        75.16%
    • Precision @ 0.50 IoU:  100.00%
    • Recall @ 0.50 IoU:     100.00%
    • F1-Score:              1.0000

  [Stage 2: Text Recognition & Juktakkhor Normalization (TrOCR)]
    • Character Error Rate (CER):  13.49%
    • Character Accuracy:          86.51%
    • Word Error Rate (WER):       28.57%
    • Word Accuracy:               71.43%
------------------------------------------------------------------------------

📄 Document: 2_1
------------------------------------------------------------------------------
  [Stage 1: Layout Detection (YOLOv8)]
    • Mean IoU (mIoU):        79.13%
    • Precision @ 0.50 IoU:   95.00%
    • Recall @ 0.50 IoU:      95.00%
    • F1-Score:              0.9500

  [Stage 2: Text Recognition & Juktakkhor Normalization (TrOCR)]
    • Character Error Rate (CER):  21.47%
    • Character Accuracy:          78.53%
    • Word Error Rate (WER):       41.22%
    • Word Accuracy:               58.78%
------------------------------------------------------------------------------

🎯 Pure Isolated Word Crop Benchmark (TrOCR):
    • Word Exact Match Accuracy:   82.00%
    • Character Accuracy:          84.62%
    • Character Error Rate (CER):  15.38%
    • Word Error Rate (WER):       18.00%
==============================================================================
```

Detailed JSON metrics are saved automatically to [`outputs/evaluation_report.json`](outputs/evaluation_report.json).

---

## 6. Bangla Juktakkhor (যুক্তাক্ষর) & Vowel Engine

Implemented in [`src/utils/juktakkhor.py`](src/utils/juktakkhor.py), this engine normalizes handwriting distortions, split Unicode encodings, and missing diacritics:

1. **Pholas (ফলা)**:
   - য-ফলা (্য): `বয` $\rightarrow$ `ব্য`, `ধয` $\rightarrow$ `ধ্য`, `তয` $\rightarrow$ `ত্য`, `নয` $\rightarrow$ `ন্য`, `ডয` $\rightarrow$ `ড্য`, `সয` $\rightarrow$ `স্য`.
   - র-ফলা (্র): `পরকাশ` $\rightarrow$ `প্রকাশ`, `পরতি` $\rightarrow$ `প্রতি`, `পরথম` $\rightarrow$ `প্রথম`, `পরধান` $\rightarrow$ `প্রধান`, `পরবীণ` $\rightarrow$ `প্রবীণ`.
   - ব-ফলা (্ব): `শব` $\rightarrow$ `শ্ব` (`বিশ্ব`), `দব` $\rightarrow$ `দ্ব` (`দ্বার`), `তব` $\rightarrow$ `ত্ব` (`গুরুত্ব`, `ঘনত্ব`, `দায়িত্ব`).
   - ম-ফলা (্ম): `সময` $\rightarrow$ `স্ময়` (`বিস্ময়`), `আতম` $\rightarrow$ `আত্ম` (`আত্মহত্যা`), `জনম` $\rightarrow$ `জন্ম`.
   - ল-ফলা (্ল): `পল` $\rightarrow$ `প্ল` (`প্লাস্টিক`), `সল` $\rightarrow$ `স্ল` (`স্লোগান`), `কল` $\rightarrow$ `ক্ল` (`ক্লিষ্ট`).
   - রেফ (র্): `করম` $\rightarrow$ `কর্ম`, `অরজন` $\rightarrow$ `অর্জন`, `বরন` $\rightarrow$ `বর্ণ`, `মরযাদা` $\rightarrow$ `মর্যাদা`.
2. **Compound Conjuncts (যুক্তব্যঞ্জন)**:
   - `ক্ষ` (guarded with negative Halant lookahead `কষ(?!\u09cd)` so `কষ্ট` never becomes `ক্ষ্ট`).
   - `জ্ঞ` (`জঞ` $\rightarrow$ `জ্ঞ`), `ষ্ঠ` (`ষঠ` $\rightarrow$ `ষ্ঠ`), `ষ্ট` (`ষট` $\rightarrow$ `ষ্ট`), `স্ট` (`সট` $\rightarrow$ `স্ট`), `ন্ট` (`নট` $\rightarrow$ `ন্ট`), `ণ্ড` (`নড` $\rightarrow$ `ণ্ড`), `ঞ্চ` (`নচ` $\rightarrow$ `ঞ্চ`), `ঞ্জ` (`নজ` $\rightarrow$ `ঞ্জ`), `চ্চ` (`উচচ` $\rightarrow$ `উচ্চ`), `চ্ছ` (`ইচছা` $\rightarrow$ `ইচ্ছা`), `ত্ত` (`উততর` $\rightarrow$ `উত্তর`), `দ্ধ` (`দধ` $\rightarrow$ `দ্ধ`), `ন্দ` (`আননদ` $\rightarrow$ `আনন্দ`), `ন্ধ` (`বনধু` $\rightarrow$ `বন্ধু`), `ম্প` (`সমপরক` $\rightarrow$ `সম্পর্ক`), `ম্ব` (`সম্বল`), `ম্ভ` (`সমভব` $\rightarrow$ `সম্ভব`), `ম্ম` (`সম্মান`).
3. **Vowel Signs & Circumfixes (কার)**:
   - Circumfix O-kar (`ে` + consonant + `া` $\rightarrow$ `ো`) with boundary guards protecting legitimate words (`দেখা`, `খেলা`, `নেতা`, `মেলা`).
   - Pre-base vowel order repair (`িক` $\rightarrow$ `কি`, `েক` $\rightarrow$ `কে`).
   - Restores missing U-kar (`নমনা` $\rightarrow$ `নমুনা`, `মানষ` $\rightarrow$ `মানুষ`, `মখ` $\rightarrow$ `মুখ`, `খব` $\rightarrow$ `খুব`) and Rri-kar (`পথিবীর` $\rightarrow$ `পৃথিবীর`, `সিরজনশীল` $\rightarrow$ `সৃজনশীল`, `সমদধ` $\rightarrow$ `সমৃদ্ধ`).
4. **Verb-Root Guards**:
   - Strictly shields forms of `করা` (`কর`, `করা`, `করে`, `করবেন`, `করছেন`, `করতে`, `করব`, `করলে`) and `করোনা` (`করোনার`, `করোনাভাইরাস`) from false conversion to `ক্র`.
   - Shields infinitive verbs (`জানতে`, `মানতে`, `শুনতে`, `আনতে`) from false conversion to `জান্তে`, `মান্তে`.

---

## 7. Adaptive Line-to-Word Segmentation

In [`src/trocr_predict.py`](src/trocr_predict.py), `segment_line_to_words` uses an adaptive horizontal kernel:
- **Tuned Kernel**: `k_w = max(6, int(h * 0.12))` and `k_h = max(2, int(h * 0.04))`.
- **Why this is critical**: Fixed wide kernels (e.g., $0.28 \times h$) bridge closely spaced cursive words, merging 3 to 4 words into a single 780-pixel crop. Because TrOCR was trained on single words, multi-word blobs cause the language decoder to hallucinate. The $0.12 \times h$ kernel connects broken strokes within words while preserving inter-word gaps.

---

## 8. Troubleshooting & FAQs

### Q1: Microsoft Word gave a `PermissionError` when exporting `.docx`!
- **Reason**: The `.docx` file is currently open in Microsoft Word, which locks the file from being overwritten.
- **Solution**: The pipeline handles this automatically! It writes a fallback file named `<doc_name>_digitized_restored.docx` without crashing. Close Microsoft Word before running if you want to overwrite the primary file.

### Q2: How do I run on CPU if my laptop doesn't have an NVIDIA GPU?
- Simply pass `--device cpu`:
  ```powershell
  python scripts/run_pipeline.py --image "F:/DIP/Dataset/1/1_1.jpg" --device cpu
  ```

### Q3: UnicodeEncodeError: 'charmap' codec can't encode characters in terminal
- Windows PowerShell sometimes defaults to cp1252. All scripts in `scripts/` and `src/` include `sys.stdout.reconfigure(encoding='utf-8')`. You can also set it globally in your terminal:
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  ```

### Q4: Can I test my own handwritten image?
- Yes! Place your image anywhere on your machine and run:
  ```powershell
  python scripts/run_pipeline.py --image "C:/path/to/my_note.jpg" --device cuda
  ```
  Check `outputs/my_note/my_note_digitized.docx` for the digitized document!

---

**Developed with ❤️ by the Bangla Handwriting Digitization DIP Team.**
