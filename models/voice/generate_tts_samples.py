"""
Helper script to generate TTS samples for testing using edge-tts (Microsoft Edge TTS).
Free, no API key required, multiple voices available.

Install: pip install edge-tts --break-system-packages
"""

import asyncio
import os


async def generate_tts_sample(text, output_path, voice="en-US-GuyNeural"):
    """
    Generate a TTS audio sample using Microsoft Edge TTS.
    
    Args:
        text: Text to synthesize
        output_path: Path to save the .mp3 file
        voice: Voice to use (default: Guy - male US English)
        
    Available voices:
        - en-US-GuyNeural (male, casual)
        - en-US-AriaNeural (female, casual)
        - en-US-JennyNeural (female, warm)
        - en-IN-NeerjaNeural (female, Indian English)
    """
    try:
        import edge_tts
    except ImportError:
        print("[ERROR] edge-tts not installed")
        print("Install with: pip install edge-tts --break-system-packages")
        return False
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        print(f"[SAVED] {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to generate {output_path}: {e}")
        return False


async def generate_test_set():
    """Generate a small test set of TTS audio clips."""
    
    # Create output directory
    output_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\voice\\test_audio\\spoof"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test sentences (varied for robustness)
    test_sentences = [
        ("Hello, this is a voice verification test.", "tts_sample_1.mp3", "en-US-GuyNeural"),
        ("I am applying for a loan from TVS Credit.", "tts_sample_2.mp3", "en-US-AriaNeural"),
        ("My name is John Smith and I live in Mumbai.", "tts_sample_3.mp3", "en-US-JennyNeural"),
        ("Please verify my identity for this transaction.", "tts_sample_4.mp3", "en-IN-NeerjaNeural"),
    ]
    
    print("="*70)
    print("GENERATING TTS TEST SAMPLES")
    print("="*70)
    print(f"\nOutput directory: {output_dir}")
    print(f"Generating {len(test_sentences)} samples...\n")
    
    for text, filename, voice in test_sentences:
        output_path = os.path.join(output_dir, filename)
        print(f"Generating: {filename}")
        print(f"  Text: \"{text}\"")
        print(f"  Voice: {voice}")
        await generate_tts_sample(text, output_path, voice)
        print()
    
    print("="*70)
    print(f"[COMPLETE] Generated {len(test_sentences)} TTS samples")
    print(f"Location: {output_dir}")
    print("\nNow record {len(test_sentences)} real voice clips saying the same sentences")
    print("and save them to: test_audio/real/")
    print("="*70)


if __name__ == "__main__":
    # Check if edge-tts is installed
    try:
        import edge_tts
        asyncio.run(generate_test_set())
    except ImportError:
        print("="*70)
        print("SETUP REQUIRED")
        print("="*70)
        print("\nThis script uses Microsoft Edge TTS (free, no API key needed)")
        print("\nInstall with:")
        print("  pip install edge-tts --break-system-packages")
        print("\nThen run this script again to generate test TTS samples")
        print("="*70)
