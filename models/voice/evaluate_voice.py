"""
Evaluate voice detection model on test set with threshold tuning.
Same pattern as face model evaluation.
"""

import os
from test_voice import run_voice_detection
from sklearn.metrics import confusion_matrix, accuracy_score
import numpy as np


def evaluate_voice_detection(real_dir, spoof_dir):
    """
    Test the model on real and spoofed voice samples.
    
    Args:
        real_dir: Directory with real voice recordings
        spoof_dir: Directory with AI-generated/TTS voice samples
        
    Returns:
        Evaluation results
    """
    # Get audio files
    real_files = [f for f in os.listdir(real_dir) if f.endswith(('.wav', '.mp3', '.flac', '.m4a'))]
    spoof_files = [f for f in os.listdir(spoof_dir) if f.endswith(('.wav', '.mp3', '.flac', '.m4a'))]
    
    print(f"Testing on {len(real_files)} real + {len(spoof_files)} spoof = {len(real_files) + len(spoof_files)} total audio clips")
    print("="*70)
    
    y_true = []
    y_pred = []
    y_scores = []
    
    # Test real audio
    print("\n[REAL] Testing REAL voice clips...")
    for i, filename in enumerate(real_files, 1):
        filepath = os.path.join(real_dir, filename)
        try:
            result = run_voice_detection(filepath)
            y_true.append(1)  # 1 = real
            y_pred.append(1 if result['verdict'] == 'real' else 0)
            y_scores.append(result['real_score'])
            
            status = "[OK]" if result['verdict'] == 'real' else "[MISS]"
            print(f"  {i:2d}. {filename[:35]:35s} = {result['verdict']:5s} ({result['real_score']*100:5.1f}%) {status}")
            
        except Exception as e:
            print(f"  {i:2d}. {filename[:35]:35s} = ERROR: {e}")
    
    # Test spoofed audio
    print("\n[SPOOF] Testing SPOOFED/AI-GENERATED clips...")
    for i, filename in enumerate(spoof_files, 1):
        filepath = os.path.join(spoof_dir, filename)
        try:
            result = run_voice_detection(filepath)
            y_true.append(0)  # 0 = spoof
            y_pred.append(1 if result['verdict'] == 'real' else 0)
            y_scores.append(result['real_score'])
            
            status = "[OK]" if result['verdict'] == 'spoof' else "[MISS]"
            print(f"  {i:2d}. {filename[:35]:35s} = {result['verdict']:5s} ({result['real_score']*100:5.1f}%) {status}")
            
        except Exception as e:
            print(f"  {i:2d}. {filename[:35]:35s} = ERROR: {e}")
    
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
    print(f"                  Spoof  Real")
    print(f"    Actual Spoof  {tn:4d}  {fp:4d}   (correctly detected spoof={tn})")
    print(f"    Actual Real   {fn:4d}  {tp:4d}   (correctly detected real={tp})")
    
    # Per-class metrics
    if tp + fn > 0:
        real_recall = tp / (tp + fn)
        print(f"\n Real Detection Recall: {real_recall*100:.1f}%")
    
    if tn + fp > 0:
        spoof_recall = tn / (tn + fp)
        print(f" Spoof Detection Recall: {spoof_recall*100:.1f}%")
    
    print("\n" + "="*70)
    
    return {
        'accuracy': accuracy,
        'confusion_matrix': cm,
        'y_true': y_true,
        'y_pred': y_pred,
        'y_scores': y_scores
    }


def find_optimal_threshold(y_true, y_scores):
    """
    Find the optimal threshold for classification.
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
    print("="*70)
    print("LITMUS VOICEPRINT - MODEL EVALUATION")
    print("="*70)
    print("\nInstructions:")
    print("1. Create two directories:")
    print("   - test_audio/real/     (3-4 real voice clips)")
    print("   - test_audio/spoof/    (3-4 AI-generated/TTS clips)")
    print("\n2. For real clips: Record yourself saying different sentences")
    print("   (use Windows Voice Recorder, phone, etc.)")
    print("\n3. For spoof clips: Use any free TTS:")
    print("   - Google Cloud TTS")
    print("   - ElevenLabs free tier")
    print("   - edge-tts (Microsoft Edge TTS)")
    print("   - Any online TTS tool")
    print("\n4. Run this script to evaluate")
    print("="*70)
    
    # Check if test directories exist
    test_real_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\voice\\test_audio\\real"
    test_spoof_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\voice\\test_audio\\spoof"
    
    if not os.path.exists(test_real_dir) or not os.path.exists(test_spoof_dir):
        print("\n[ERROR] Test directories not found")
        print(f"Please create: {test_real_dir}")
        print(f"Please create: {test_spoof_dir}")
        exit(1)
    
    # Run evaluation
    results = evaluate_voice_detection(test_real_dir, test_spoof_dir)
    
    # Find optimal threshold if we have enough samples
    if len(results['y_true']) >= 4:
        best_threshold, best_acc = find_optimal_threshold(results['y_true'], results['y_scores'])
    else:
        print("\n[SKIP] Threshold optimization requires at least 4 samples")
