"""
Step 1: Test current voice model on real human voice clips
Baseline validation before ensemble
"""

import os
import sys
from pathlib import Path

# Import the existing voice detection function
from test_voice import run_voice_detection

def test_real_voice_baseline():
    """Test voice model on real human recordings"""
    print("=" * 60)
    print("STEP 1: REAL VOICE BASELINE TEST")
    print("=" * 60)
    
    # Find all real voice samples
    sample_dir = Path("real_voice_samples")
    if not sample_dir.exists():
        print(f"\n❌ Error: {sample_dir} not found")
        print("Run record_real_voice.py first to record clips")
        return
    
    audio_files = list(sample_dir.glob("*.wav"))
    if not audio_files:
        print(f"\n❌ Error: No .wav files found in {sample_dir}")
        print("Run record_real_voice.py first to record clips")
        return
    
    print(f"\nFound {len(audio_files)} real voice clips")
    print(f"Testing with MelodyMachine/Deepfake-audio-detection-V2\n")
    
    results = []
    
    for audio_path in sorted(audio_files):
        print(f"Testing: {audio_path.name}")
        try:
            result = run_voice_detection(str(audio_path))
            real_score = result['real_score']
            verdict = result['verdict']
            
            print(f"  Real Score: {real_score:.1%}")
            print(f"  Verdict: {verdict.upper()}")
            
            results.append({
                'file': audio_path.name,
                'real_score': real_score,
                'verdict': verdict
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    # Summary
    print("=" * 60)
    print("BASELINE RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'File':<20} {'Real Score':<15} {'Verdict':<10} {'Correct?':<10}")
    print("-" * 60)
    
    correct_count = 0
    for r in results:
        is_correct = r['verdict'] == 'real'
        correct_mark = "✓" if is_correct else "✗"
        if is_correct:
            correct_count += 1
        
        print(f"{r['file']:<20} {r['real_score']:<14.1%} {r['verdict'].upper():<10} {correct_mark:<10}")
    
    print("-" * 60)
    accuracy = (correct_count / len(results) * 100) if results else 0
    print(f"Accuracy on real voice: {correct_count}/{len(results)} ({accuracy:.0f}%)")
    print()
    
    # Interpretation
    if accuracy >= 75:
        print("✓ INTERPRETATION: Model correctly identifies real voice")
        print("  Same pattern as face detection - good baseline on real samples")
        print("  The TTS misclassification is likely domain mismatch (modern TTS fooling older detector)")
        print("  → Proceed to Step 2: Test second model for ensemble")
    else:
        print("⚠ INTERPRETATION: Model struggles with real voice too")
        print("  This is NOT just a domain mismatch issue")
        print("  Model may have calibration problems beyond the TTS issue")
        print("  → Need threshold tuning before proceeding to ensemble")
    
    print()
    print("Next: If baseline is good, run setup_voice_ensemble.py for Step 2")

if __name__ == "__main__":
    test_real_voice_baseline()
