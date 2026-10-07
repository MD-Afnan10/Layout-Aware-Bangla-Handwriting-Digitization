# 🇧🇩 Step-by-Step Guide: Training Bangla TrOCR on Kaggle GPU

This guide explains how to train the **Vision-Encoder-Decoder (TrOCR)** model on Kaggle using free NVIDIA GPUs (T4 x2 or P100).

---

## 📁 What You Will Use
We have prepared a complete, ready-to-run Jupyter Notebook for you:
- **Notebook File**: [`scripts/kaggle_train_trocr.ipynb`](scripts/kaggle_train_trocr.ipynb)

---

## 🚀 Step 1: Open Kaggle & Create a Notebook

1. Go to [kaggle.com](https://www.kaggle.com) and log in.
2. In the top left navigation, click **`+ Create`** ➔ **`New Notebook`**.
3. In the top menu of the notebook, click:
   - **`File`** ➔ **`Upload Notebook`**
   - Drag and drop or browse to select [`scripts/kaggle_train_trocr.ipynb`](scripts/kaggle_train_trocr.ipynb) from your local repository.

---

## ⚙️ Step 2: Configure Kaggle Settings (CRITICAL)

On the right-hand sidebar under **Notebook options**:

| Setting | Value | Why It Is Required |
| :--- | :--- | :--- |
| **Accelerator** | **GPU T4 x2** (or **GPU P100**) | Provides 16 GB GPU VRAM for fast mixed-precision training. |
| **Internet** | **ON** | Allows downloading pre-trained ViT (`google/vit-base-patch16-224-in21k`) and Bangla BERT (`sagorsarker/bangla-bert-base`). |
| **Persistence** | **Files only** | Keeps files across sessions. |

---

## 📦 Step 3: Attach the BN-HTRd Dataset

In the right-hand sidebar, under the **Input** section:
1. Click **`+ Add Input`** (or **`Add Data`**).
2. Search for: **`BN-HTRd`** or **`Bangla Handwriting`**.
3. Click the **`+`** icon next to the dataset to attach it to your notebook.
   *(The dataset will now appear inside `/kaggle/input/`)*.

---

## ▶️ Step 4: Run the Notebook

Click **`Run All`** (or execute cell by cell from top to bottom):

1. **Cell 1**: Installs `transformers`, `datasets`, `jiwer`, `accelerate`.
2. **Cell 2 & 3**: Automatically discovers the BN-HTRd Excel files and images in `/kaggle/input` and builds the `train_manifest.csv` mapping.
3. **Cell 4**: Initializes Google's Vision Transformer (ViT) as the visual encoder and Bangla BERT as the autoregressive language decoder.
4. **Cell 5 & 6**: Executes fine-tuning with **FP16 mixed precision** and a batch size of 16.
   - You will see training progress bars with step loss and Character Error Rate (CER).
   - Training takes approximately **2.5 to 4 hours** on a Kaggle T4 GPU.
5. **Cell 7**: Automatically packages the trained weights into `/kaggle/working/trocr_bangla_trained.zip`.

---

## 💾 Step 5: Download the Trained Model to Your PC

1. On the right-hand panel, go to the **Output** tab (refresh if needed).
2. Look for **`trocr_bangla_trained.zip`**.
3. Click the three dots `...` next to it and select **`Download`**.
4. On your PC, extract the contents of the zip file directly into:
   ```
   f:\DIP\Layout-Aware-Bangla-Handwriting-Digitization\weights\trocr_bangla\
   ```
5. Ensure these files are present inside `weights/trocr_bangla/`:
   - `model.safetensors`
   - `config.json`
   - `generation_config.json`
   - `preprocessor_config.json`
   - `tokenizer_config.json`
   - `vocab.txt`

---

## 🏁 Step 6: Test Your New Model Locally

Run the master end-to-end pipeline with your newly trained model:

```powershell
python scripts/run_pipeline.py --image "F:\DIP\Dataset\1\1_1.jpg" --device cuda
```

Your pipeline will now recognize handwriting across any writer using your full Kaggle-trained weights!
