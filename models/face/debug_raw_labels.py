"""
Debug script to check RAW pipeline output for label-mapping bugs.
0/10 real detection suggests label swap, not genuine model bias.
"""

from transformers import pipeline
from PIL import Image
import os

print("="*70)
print("RAW LABEL DEBUG - Model 2 (dima806)")
print("="*70)
print("\nChecking if labels are LABEL_0/LABEL_1 vs Real/Fake")
print("or if there's a case-sensitivity issue...")
print("="*70)

# Load Model 2
detector = pipeline("image-classification", model="dima806/deepfake_vs_real_image_detection")

# Test on 3 "real" images from prepared_dataset
real_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\real"
real_files = [f for f in os.listdir(real_dir) if f.endswith('.png')][:3]

print("\n[REAL IMAGES] - RAW Pipeline Output:")
print("-"*70)

for i, filename in enumerate(real_files, 1):
    filepath = os.path.join(real_dir, filename)
    image = Image.open(filepath)
    
    # Get RAW output - don't interpret it yet
    raw_result = detector(image)
    
    print(f"\n{i}. {filename}")
    print(f"   RAW OUTPUT: {raw_result}")
    print(f"   Type: {type(raw_result)}")
    
    # Check each prediction dict
    for pred in raw_result:
        print(f"     - label: '{pred['label']}' (type: {type(pred['label'])})")
        print(f"       score: {pred['score']:.4f}")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)
print("\nLook for:")
print("  1. Are labels 'LABEL_0'/'LABEL_1' instead of 'Real'/'Fake'?")
print("  2. Is there case mismatch? ('Real' vs 'real' vs 'REAL')")
print("  3. Are the scores inverted (higher score = fake, not real)?")
print("="*70)

# Also test Model 1 for comparison
print("\n" + "="*70)
print("RAW LABEL DEBUG - Model 1 (prithivMLmods)")
print("="*70)

detector1 = pipeline("image-classification", model="prithivMLmods/Deep-Fake-Detector-Model")

print("\n[REAL IMAGES] - RAW Pipeline Output:")
print("-"*70)

for i, filename in enumerate(real_files, 1):
    filepath = os.path.join(real_dir, filename)
    image = Image.open(filepath)
    
    raw_result = detector1(image)
    
    print(f"\n{i}. {filename}")
    print(f"   RAW OUTPUT: {raw_result}")
    
    for pred in raw_result:
        print(f"     - label: '{pred['label']}' (type: {type(pred['label'])})")
        print(f"       score: {pred['score']:.4f}")

print("\n" + "="*70)
