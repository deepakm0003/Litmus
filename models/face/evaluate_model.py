"""
Evaluate deepfake detection model on FaceForensics++ test set
"""

import os
import sys
from test_face import run_face_detection
from sklearn.metrics import confusion_matrix, accuracy_score, classification_report
import numpy as np

def evaluate_on_dataset(real_dir, fake_dir, num_samples=10):
    """
    Test the model on a balanced set of real and fake images.
    
    Args:
        real_dir: Path to directory with real images
        fake_dir: Path to directory with fake images
        num_samples: Number of samples to test from each class
        
    Returns:
        dict with results and metrics
    """
    # Get sample files
    real_files = [f for f in os.listdir(real_dir) if f.endswith('.png')][:num_samples]
    fake_files = [f for f in os.listdir(fake_dir) if f.endswith('.png')][:num_samples]
    
    print(f"Testing on {len(real_files)} real + {len(fake_files)} fake = {len(real_files) + len(fake_files)} total images")
    print("="*70)
    
    y_true = []
    y_pred = []
    y_scores = []
    results = []
    
    # Test real images
    print("\n[REAL] Testing REAL images...")
    for i, filename in enumerate(real_files, 1):
        filepath = os.path.join(real_dir, filename)
        try:
            result = run_face_detection(filepath)
            y_true.append(1)  # 1 = real
            y_pred.append(1 if result['verdict'] == 'real' else 0)
            y_scores.append(result['real_score'])
            
            status = "[OK]" if result['verdict'] == 'real' else "[MISS]"
            print(f"  {i:2d}. {filename[:30]:30s} = {result['verdict']:4s} ({result['real_score']*100:5.1f}%) {status}")
            
            results.append({
                'filename': filename,
                'ground_truth': 'real',
                'prediction': result['verdict'],
                'real_score': result['real_score']
            })
        except Exception as e:
            print(f"  {i:2d}. {filename[:30]:30s} = ERROR: {e}")
    
    # Test fake images
    print("\n[FAKE] Testing FAKE images...")
    for i, filename in enumerate(fake_files, 1):
        filepath = os.path.join(fake_dir, filename)
        try:
            result = run_face_detection(filepath)
            y_true.append(0)  # 0 = fake
            y_pred.append(1 if result['verdict'] == 'real' else 0)
            y_scores.append(result['real_score'])
            
            status = "[OK]" if result['verdict'] == 'fake' else "[MISS]"
            print(f"  {i:2d}. {filename[:30]:30s} = {result['verdict']:4s} ({result['real_score']*100:5.1f}%) {status}")
            
            results.append({
                'filename': filename,
                'ground_truth': 'fake',
                'prediction': result['verdict'],
                'real_score': result['real_score']
            })
        except Exception as e:
            print(f"  {i:2d}. {filename[:30]:30s} = ERROR: {e}")
    
    # Calculate metrics
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_scores = np.array(y_scores)
    
    accuracy = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    
    # Confusion matrix breakdown
    tn, fp, fn, tp = cm.ravel()
    
    print("\n" + "="*70)
    print("[RESULTS]")
    print("="*70)
    print(f"\n Overall Accuracy: {accuracy*100:.1f}%")
    print(f"\n Confusion Matrix:")
    print(f"                  Predicted")
    print(f"                  Fake  Real")
    print(f"    Actual Fake   {tn:4d}  {fp:4d}   (FN={fp}, correctly detected fake={tn})")
    print(f"    Actual Real   {fn:4d}  {tp:4d}   (FP={fn}, correctly detected real={tp})")
    
    # Per-class metrics
    if tp + fn > 0:
        real_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        real_recall = tp / (tp + fn)
        print(f"\n Real Detection: Precision={real_precision*100:.1f}%, Recall={real_recall*100:.1f}%")
    
    if tn + fp > 0:
        fake_precision = tn / (tn + fn) if (tn + fn) > 0 else 0
        fake_recall = tn / (tn + fp)
        print(f" Fake Detection: Precision={fake_precision*100:.1f}%, Recall={fake_recall*100:.1f}%")
    
    print("\n" + "="*70)
    
    return {
        'accuracy': accuracy,
        'confusion_matrix': cm,
        'y_true': y_true,
        'y_pred': y_pred,
        'y_scores': y_scores,
        'results': results
    }


def find_optimal_threshold(y_true, y_scores):
    """
    Find the optimal threshold for classification by testing multiple cutoffs.
    
    Args:
        y_true: Ground truth labels (1=real, 0=fake)
        y_scores: Real scores from the model
        
    Returns:
        Best threshold and its accuracy
    """
    print("\n" + "="*70)
    print("[THRESHOLD OPTIMIZATION]")
    print("="*70)
    print("\nTesting different thresholds for real_score cutoff:")
    print(f"{'Threshold':>12s} {'Accuracy':>10s} {'TP':>5s} {'TN':>5s} {'FP':>5s} {'FN':>5s}")
    print("-"*70)
    
    thresholds = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    best_threshold = 0.5
    best_accuracy = 0.0
    
    for threshold in thresholds:
        # Predict: real if real_score > threshold
        y_pred_thresh = (y_scores > threshold).astype(int)
        accuracy = accuracy_score(y_true, y_pred_thresh)
        
        cm = confusion_matrix(y_true, y_pred_thresh)
        tn, fp, fn, tp = cm.ravel()
        
        marker = " <--" if accuracy > best_accuracy else ""
        print(f"{threshold:12.2f} {accuracy*100:9.1f}% {tp:5d} {tn:5d} {fp:5d} {fn:5d}{marker}")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    
    print("-"*70)
    print(f"\n[BEST] Optimal threshold: {best_threshold:.2f} with accuracy {best_accuracy*100:.1f}%")
    print(f"       (Default was 0.50 with accuracy {accuracy_score(y_true, (y_scores > 0.5).astype(int))*100:.1f}%)")
    print("="*70)
    
    return best_threshold, best_accuracy


if __name__ == "__main__":
    # Use prepared_dataset which has 11 real + 11 fake images
    test_real_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\real"
    test_fake_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\fake"
    
    # Run evaluation on 10+10 samples (20 total)
    results = evaluate_on_dataset(test_real_dir, test_fake_dir, num_samples=10)
    
    # Find optimal threshold
    best_threshold, best_acc = find_optimal_threshold(results['y_true'], results['y_scores'])
