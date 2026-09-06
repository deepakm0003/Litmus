"""
Alternative deepfake detection using dima806/deepfake_vs_real_image_detection
"""

from transformers import pipeline
from PIL import Image
import os


def run_face_detection_model2(image_path):
    """
    Detect if a face image is real or AI-generated/deepfake using Model 2.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        dict: {
            "real_score": float,  # Confidence score for "Real" label (0-1)
            "verdict": str        # "real" or "fake"
        }
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Load the alternative deepfake detection model
    detector = pipeline("image-classification", model="dima806/deepfake_vs_real_image_detection")
    
    # Load and analyze the image
    image = Image.open(image_path)
    result = detector(image)
    
    # Parse results - model returns list of label-score pairs
    real_score = 0.0
    fake_score = 0.0
    
    for prediction in result:
        label = prediction['label'].lower()
        score = prediction['score']
        
        if 'real' in label:
            real_score = score
        elif 'fake' in label:
            fake_score = score
    
    # Determine verdict based on higher confidence
    verdict = "real" if real_score > fake_score else "fake"
    
    return {
        "real_score": real_score,
        "verdict": verdict
    }


if __name__ == "__main__":
    # Test the function
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_face_model2.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    result = run_face_detection_model2(image_path)
    
    print(f"\n{'='*50}")
    print(f"[MODEL 2] Image: {os.path.basename(image_path)}")
    print(f"{'='*50}")
    print(f"Verdict: {result['verdict'].upper()}")
    print(f"Real Score: {result['real_score']:.4f} ({result['real_score']*100:.2f}%)")
    print(f"Fake Score: {1-result['real_score']:.4f} ({(1-result['real_score'])*100:.2f}%)")
    print(f"{'='*50}\n")
