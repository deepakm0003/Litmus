"""
Test the model on demo-condition samples (fresh photo + face-swap)
This is what matters for Round 3, not FaceForensics++ accuracy.
"""

import os
from test_face import run_face_detection

print("="*70)
print("DEMO CONDITION TEST")
print("="*70)
print("\nThis test simulates the actual Round 3 demo scenario:")
print("  1. Fresh selfie photo (real)")
print("  2. Face-swapped version (fake)")
print("\nPlease provide:")
print("  - A real photo (place as: test_real_photo.jpg)")
print("  - A face-swapped version (place as: test_fake_photo.jpg)")
print("="*70)

# Check if test images exist
real_path = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\test_real_photo.jpg"
fake_path = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\test_fake_photo.jpg"

if not os.path.exists(real_path):
    print(f"\n[MISSING] {real_path}")
    print("Please add a real photo as test_real_photo.jpg")
    
if not os.path.exists(fake_path):
    print(f"\n[MISSING] {fake_path}")
    print("Please add a face-swapped photo as test_fake_photo.jpg")
    print("\nSuggested tools for face-swap:")
    print("  - DeepFaceLab (local)")
    print("  - FaceSwap (local)")
    print("  - Reface app (mobile)")
    print("  - Face Swap Online (web)")

if not os.path.exists(real_path) or not os.path.exists(fake_path):
    print("\n" + "="*70)
    print("Cannot proceed - missing test images")
    print("="*70)
    exit(1)

print("\n" + "="*70)
print("RUNNING TESTS...")
print("="*70)

# Test real photo
print("\n[TEST 1] Real Photo")
print("-"*70)
real_result = run_face_detection(real_path)
print(f"Verdict: {real_result['verdict'].upper()}")
print(f"Real Score: {real_result['real_score']:.4f} ({real_result['real_score']*100:.2f}%)")
real_correct = real_result['verdict'] == 'real'
print(f"Correct: {real_correct}")

# Test fake photo
print("\n[TEST 2] Face-Swapped Photo")
print("-"*70)
fake_result = run_face_detection(fake_path)
print(f"Verdict: {fake_result['verdict'].upper()}")
print(f"Real Score: {fake_result['real_score']:.4f} ({fake_result['real_score']*100:.2f}%)")
fake_correct = fake_result['verdict'] == 'fake'
print(f"Correct: {fake_correct}")

# Summary
print("\n" + "="*70)
print("DEMO CONDITION ACCURACY")
print("="*70)
accuracy = (real_correct + fake_correct) / 2.0 * 100
print(f"Accuracy: {accuracy:.0f}% (2/2 correct)" if accuracy == 100 else f"Accuracy: {accuracy:.0f}%")

if accuracy >= 50:
    print("\n[VERDICT] Model is usable for Round 3 demo")
    print("This is the real test - FF++ performance doesn't matter")
else:
    print("\n[VERDICT] Model needs recalibration or replacement")
    
print("="*70)
