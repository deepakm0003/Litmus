"""
Verify that the ground truth labels match the actual folder structure.
40% accuracy is worse than random - this could be a label flip issue.
"""

import os

print("="*70)
print("LABEL VERIFICATION")
print("="*70)
print("\nChecking FaceForensics++ folder structure and labels...")
print("\nExpected convention:")
print("  - prepared_dataset/real/ = REAL faces (original_sequences)")
print("  - prepared_dataset/fake/ = FAKE faces (manipulated_sequences)")
print("\n" + "="*70)

# Check real directory
real_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\real"
fake_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\fake"

print("\n[REAL DIRECTORY] 10 samples:")
print("-"*70)
real_files = [f for f in os.listdir(real_dir) if f.endswith('.png')][:10]
for i, filename in enumerate(real_files, 1):
    filepath = os.path.join(real_dir, filename)
    print(f"{i:2d}. Ground Truth: REAL | File: {filepath}")

print("\n[FAKE DIRECTORY] 10 samples:")
print("-"*70)
fake_files = [f for f in os.listdir(fake_dir) if f.endswith('.png')][:10]
for i, filename in enumerate(fake_files, 1):
    filepath = os.path.join(fake_dir, filename)
    print(f"{i:2d}. Ground Truth: FAKE | File: {filepath}")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)
print("\nIf the folder structure is correct:")
print("  - Files in 'real/' folder should be labeled as REAL")
print("  - Files in 'fake/' folder should be labeled as FAKE")
print("\nBUT - check the actual FaceForensics++ documentation:")
print("  - What does the source metadata.json say about these video IDs?")
print("  - Are these pre-cropped faces from the original dataset?")
print("\n" + "="*70)

# Try to find metadata.json to verify
metadata_paths = [
    "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\train_sample_videos\\metadata.json",
    "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\metadata.json",
]

print("\nLooking for metadata.json to verify labels...")
for path in metadata_paths:
    if os.path.exists(path):
        print(f"\n[FOUND] {path}")
        import json
        with open(path, 'r') as f:
            metadata = json.load(f)
        
        # Check a few sample filenames
        print("\nSample metadata entries:")
        for i, (key, value) in enumerate(list(metadata.items())[:5]):
            print(f"  {key}: {value}")
        break
else:
    print("\n[NOT FOUND] metadata.json - cannot verify against source")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)
print("\nIf you suspect labels are flipped, we can:")
print("  1. Flip the labels in the evaluation script (swap real<->fake)")
print("  2. Re-run evaluation to see if accuracy jumps to 60-75%")
print("="*70)
