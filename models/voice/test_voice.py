"""
Litmus VoicePrint Module - AI Voice Spoofing Detection
Uses HuggingFace transformer model for real-time voice verification
"""

from transformers import pipeline
import os
import librosa
import numpy as np

# Ensure ffmpeg is findable regardless of shell PATH state
_FFMPEG_BIN = (
    r"C:\Users\deepa\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.1-full_build\bin"
)
if _FFMPEG_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")


def run_voice_detection(audio_path):
    """
    Detect if a voice audio clip is real or AI-generated/TTS/voice-cloned.
    
    Args:
        audio_path (str): Path to the audio file (.wav, .mp3, .flac, etc.)
        
    Returns:
        dict: {
            "real_score": float,  # Confidence score for "real" label (0-1)
            "verdict": str        # "real" or "spoof"
        }
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    try:
        # Load the deepfake audio detection model
        detector = pipeline("audio-classification", model="MelodyMachine/Deepfake-audio-detection-V2")
        
        # Load audio with librosa — handles all formats (wav, mp3, m4a, flac…)
        # This bypasses the pipeline's ffmpeg file-path requirement entirely.
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        # Run detection on the numpy array directly
        result = detector({"array": audio, "sampling_rate": 16000})
        
        # Parse results - model returns list of label-score pairs
        # Expected labels: "REAL" and "FAKE" (or similar)
        real_score = 0.0
        spoof_score = 0.0
        
        print(f"[DEBUG] Raw model output: {result}")
        
        for prediction in result:
            label = prediction['label'].lower()
            score = prediction['score']
            
            if 'real' in label or 'bonafide' in label or 'genuine' in label:
                real_score = score
            elif 'fake' in label or 'spoof' in label or 'generated' in label or 'synthetic' in label:
                spoof_score = score
        
        # Determine verdict based on higher confidence
        verdict = "real" if real_score > spoof_score else "spoof"
        
        return {
            "real_score": real_score,
            "verdict": verdict
        }
        
    except Exception as e:
        raise RuntimeError(f"Error processing audio {audio_path}: {e}")


if __name__ == "__main__":
    # Test the function
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_voice.py <audio_path>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    result = run_voice_detection(audio_path)
    
    print(f"\n{'='*50}")
    print(f"Audio: {os.path.basename(audio_path)}")
    print(f"{'='*50}")
    print(f"Verdict: {result['verdict'].upper()}")
    print(f"Real Score: {result['real_score']:.4f} ({result['real_score']*100:.2f}%)")
    print(f"Spoof Score: {1-result['real_score']:.4f} ({(1-result['real_score'])*100:.2f}%)")
    print(f"{'='*50}\n")
