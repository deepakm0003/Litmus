"""
Record real human voice clips for baseline testing
Requires: pip install sounddevice soundfile numpy
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import os

def record_clip(filename, duration=12, sample_rate=16000):
    """Record audio clip"""
    print(f"\n🎤 Recording {filename} for {duration} seconds...")
    print("Speak naturally - describe what you're doing, explain your project, or read a sentence.")
    print("Starting in 3... 2... 1...")
    
    # Record
    audio = sd.rec(int(duration * sample_rate), 
                   samplerate=sample_rate, 
                   channels=1, 
                   dtype='float32')
    sd.wait()
    
    # Save
    output_dir = "real_voice_samples"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    sf.write(filepath, audio, sample_rate)
    
    print(f"✓ Saved to {filepath}")
    return filepath

if __name__ == "__main__":
    print("=" * 60)
    print("REAL VOICE BASELINE TEST - Recording Session")
    print("=" * 60)
    print("\nWe need 3-4 clips of you speaking naturally (10-15 seconds each)")
    print("\nSuggested sentences:")
    print("1. 'I'm building Litmus, a deepfake detection system for document verification'")
    print("2. 'This system uses ensemble models to detect both face and voice manipulation'")
    print("3. 'We're testing whether the voice model can distinguish real from synthetic speech'")
    print("4. 'The goal is to route suspicious content to human review rather than auto-rejecting'")
    
    input("\nPress Enter when ready to start recording...")
    
    clips = []
    for i in range(1, 5):
        filename = f"real_clip_{i}.wav"
        filepath = record_clip(filename, duration=12)
        clips.append(filepath)
        
        if i < 4:
            cont = input(f"\nRecorded clip {i}/4. Continue? (y/n): ").lower()
            if cont != 'y':
                break
    
    print(f"\n✓ Recorded {len(clips)} clips:")
    for clip in clips:
        print(f"  - {clip}")
    print("\nRun test_real_voice.py to evaluate these clips with the voice detection model.")
