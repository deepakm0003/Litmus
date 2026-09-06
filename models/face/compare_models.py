"""
Compare both models side-by-side on FF++ and demo-condition samples
"""

import os
from test_face import run_face_detection
from test_face_model2 import run_face_detection_model2
from sklearn.metrics import confusion_matrix, accuracy_score
import numpy as np

def evaluate_both_models(real_dir, fake_dir, num_samples=10):
    """
    Test both models on the same dataset.
    """
    # Get sample files
    real_files = [f for f in os.listdir(real_dir) if f.endswith('.png')][:num_samples]
    fake_files = [f for f in os.listdir(fake_dir) if f.endswith('.png')][:num_samples]
    
    print(f"Testing both models on {len(real_files)} real + {len(fake_files)} fake = {len(real_files) + len(fake_files)} total images")
    print("="*70)
    
    y_true = []
    
    # Model 1 results
    y_pred_m1 = []
    y_scores_m1 = []
    
    # Model 2 results
    y_pred_m2 = []
    y_scores_m2 = []
    
    # Test real images
    print("\n[REAL] Testing REAL images...")
    for i, filename in enumerate(real_files, 1):
        filepath = os.path.join(real_dir, filename)
        try:
            # Model 1
            result_m1 = run_face_detection(filepath)
            # Model 2
            result_m2 = run_face_detection_model2(filepath)
            
            y_true.append(1)  # 1 = real
            
            y_pred_m1.append(1 if result_m1['verdict'] == 'real' else 0)
            y_scores_m1.append(result_m1['real_score'])
            
            y_pred_m2.append(1 if result_m2['verdict'] == 'real' else 0)
            y_scores_m2.append(result_m2['real_score'])
            
            m1_status = "[OK]" if result_m1['verdict'] == 'real' else "[MISS]"
            m2_status = "[OK]" if result_m2['verdict'] == 'real' else "[MISS]"
            
            print(f"  {i:2d}. {filename[:25]:25s} | M1: {result_m1['verdict']:4s} ({result_m1['real_score']*100:5.1f}%) {m1_status} | M2: {result_m2['verdict']:4s} ({result_m2['real_score']*100:5.1f}%) {m2_status}")
            
        except Exception as e:
            print(f"  {i:2d}. {filename[:25]:25s} | ERROR: {e}")
    
    # Test fake images
    print("\n[FAKE] Testing FAKE images...")
    for i, filename in enumerate(fake_files, 1):
        filepath = os.path.join(fake_dir, filename)
        try:
            # Model 1
            result_m1 = run_face_detection(filepath)
            # Model 2
            result_m2 = run_face_detection_model2(filepath)
            
            y_true.append(0)  # 0 = fake
            
            y_pred_m1.append(1 if result_m1['verdict'] == 'real' else 0)
            y_scores_m1.append(result_m1['real_score'])
            
            y_pred_m2.append(1 if result_m2['verdict'] == 'real' else 0)
            y_scores_m2.append(result_m2['real_score'])
            
            m1_status = "[OK]" if result_m1['verdict'] == 'fake' else "[MISS]"
            m2_status = "[OK]" if result_m2['verdict'] == 'fake' else "[MISS]"
            
            print(f"  {i:2d}. {filename[:25]:25s} | M1: {result_m1['verdict']:4s} ({result_m1['real_score']*100:5.1f}%) {m1_status} | M2: {result_m2['verdict']:4s} ({result_m2['real_score']*100:5.1f}%) {m2_status}")
            
        except Exception as e:
            print(f"  {i:2d}. {filename[:25]:25s} | ERROR: {e}")
    
    # Calculate metrics
    y_true = np.array(y_true)
    y_pred_m1 = np.array(y_pred_m1)
    y_pred_m2 = np.array(y_pred_m2)
    
    accuracy_m1 = accuracy_score(y_true, y_pred_m1)
    accuracy_m2 = accuracy_score(y_true, y_pred_m2)
    
    cm_m1 = confusion_matrix(y_true, y_pred_m1)
    cm_m2 = confusion_matrix(y_true, y_pred_m2)
    
    # Results
    print("\n" + "="*70)
    print("[RESULTS COMPARISON]")
    print("="*70)
    
    print(f"\nModel 1 (prithivMLmods/Deep-Fake-Detector-Model):")
    print(f"  Overall Accuracy: {accuracy_m1*100:.1f}%")
    tn1, fp1, fn1, tp1 = cm_m1.ravel()
    print(f"  Real Detection: {tp1}/{tp1+fn1} correct ({tp1/(tp1+fn1)*100:.1f}%)")
    print(f"  Fake Detection: {tn1}/{tn1+fp1} correct ({tn1/(tn1+fp1)*100:.1f}%)")
    
    print(f"\nModel 2 (dima806/deepfake_vs_real_image_detection):")
    print(f"  Overall Accuracy: {accuracy_m2*100:.1f}%")
    tn2, fp2, fn2, tp2 = cm_m2.ravel()
    print(f"  Real Detection: {tp2}/{tp2+fn2} correct ({tp2/(tp2+fn2)*100:.1f}%)")
    print(f"  Fake Detection: {tn2}/{tn2+fp2} correct ({tn2/(tn2+fp2)*100:.1f}%)")
    
    print("\n" + "="*70)
    if accuracy_m2 > accuracy_m1:
        print(f"[WINNER] Model 2 is better by {(accuracy_m2-accuracy_m1)*100:.1f} percentage points")
    elif accuracy_m1 > accuracy_m2:
        print(f"[WINNER] Model 1 is better by {(accuracy_m1-accuracy_m2)*100:.1f} percentage points")
    else:
        print("[TIE] Both models have the same accuracy")
    print("="*70)
    
    return {
        'model1_accuracy': accuracy_m1,
        'model2_accuracy': accuracy_m2,
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MODEL COMPARISON: FF++ Dataset")
    print("="*70)
    
    # Use prepared_dataset
    test_real_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\real"
    test_fake_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\fake"
    
    results = evaluate_both_models(test_real_dir, test_fake_dir, num_samples=10)
    
    print("\n" + "="*70)
    print("DEMO-CONDITION TEST")
    print("="*70)
    
    # Check if demo images exist
    real_path = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\test_real_photo.jpg"
    fake_path = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\test_fake_photo.jpg"
    
    if os.path.exists(real_path) and os.path.exists(fake_path):
        print("\n[TEST 1] Real Photo")
        print("-"*70)
        real_m1 = run_face_detection(real_path)
        real_m2 = run_face_detection_model2(real_path)
        print(f"Model 1: {real_m1['verdict']:4s} ({real_m1['real_score']*100:5.1f}%)")
        print(f"Model 2: {real_m2['verdict']:4s} ({real_m2['real_score']*100:5.1f}%)")
        
        print("\n[TEST 2] Face-Swapped Photo")
        print("-"*70)
        fake_m1 = run_face_detection(fake_path)
        fake_m2 = run_face_detection_model2(fake_path)
        print(f"Model 1: {fake_m1['verdict']:4s} ({fake_m1['real_score']*100:5.1f}%)")
        print(f"Model 2: {fake_m2['verdict']:4s} ({fake_m2['real_score']*100:5.1f}%)")
        
        m1_demo_acc = ((real_m1['verdict'] == 'real') + (fake_m1['verdict'] == 'fake')) / 2.0 * 100
        m2_demo_acc = ((real_m2['verdict'] == 'real') + (fake_m2['verdict'] == 'fake')) / 2.0 * 100
        
        print("\n" + "="*70)
        print(f"Model 1 Demo Accuracy: {m1_demo_acc:.0f}%")
        print(f"Model 2 Demo Accuracy: {m2_demo_acc:.0f}%")
        print("="*70)
    else:
        print("\n[SKIP] Demo photos not found. Please create:")
        print(f"  - {real_path}")
        print(f"  - {fake_path}")
        print("="*70)
