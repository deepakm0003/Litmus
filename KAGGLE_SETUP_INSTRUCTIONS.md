# Kaggle Dataset Setup for Meta-Model Training

## Quick Setup (5 minutes)

### 1. Get Kaggle API Credentials

1. Go to https://www.kaggle.com/settings
2. Scroll to "API" section  
3. Click "Create New Token"
4. Download `kaggle.json` file
5. Place it at: `C:\Users\deepa\.kaggle\kaggle.json`

### 2. Download Datasets

```bash
cd c:\Users\deepa\OneDrive\Desktop\litmus\models
python setup_kaggle_data.py
```

This downloads:
- **Face dataset:** 140k Real and Fake Faces (~1.2GB)  
- **Voice dataset:** The Fake or Real Dataset (~500MB)

### 3. Train Meta-Models

```bash
# Face meta-model (uses 100 samples, trains in ~2 minutes)
cd models\face
python train_meta_model.py

# Voice meta-model (similar process)  
cd ..\voice
python train_voice_meta_model.py  # (to be created)
```

---

## What This Gets You

### Instead of Manual Collection:
- ❌ Take 30 selfies + face-swaps manually
- ❌ Record 30 voice clips + TTS versions
- ❌ Hours of manual work

### You Get:
- ✅ **100+ diverse samples per class** from Kaggle datasets
- ✅ **Statistically robust training data** (not just your face/voice)
- ✅ **2-minute setup** instead of hours
- ✅ **Learned fusion weights** instead of guessed 70% thresholds

---

## File Structure After Setup

```
litmus/
├── models/
│   ├── face/
│   │   ├── kaggle_data/          # 140k Real and Fake Faces
│   │   ├── meta_model.pkl        # Trained fusion model  
│   │   ├── meta_model_boundary.png  # Decision boundary plot
│   │   └── ...
│   ├── voice/
│   │   ├── kaggle_data/          # Fake or Real Dataset
│   │   └── ...
│   └── setup_kaggle_data.py      # Download script
```

---

## For Round 3 Demo

**Bulk validation:** Uses Kaggle datasets (this setup)  
**Live demo:** Still use 2-3 fresh selfie + face-swap pairs of you

The live demo shows it works on unrehearsed input, not just dataset samples.

---

## Technical Benefits

1. **"We learned the fusion weights from data"** (better than "we guessed 70%")
2. **Larger sample size** → more robust statistics  
3. **Diverse faces/voices** → better generalization than just your samples
4. **Fast training** → fits your Sep 6 deadline
5. **Legitimate ML technique** → stacked ensemble, well-established

This is the **smart path** to a stronger technical story without the time/compute cost of full model retraining.