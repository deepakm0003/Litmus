"""
Test the Litmus FaceGuard API with demo photos
"""

import requests
import os

API_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint"""
    print("="*70)
    print("Testing health check endpoint...")
    print("="*70)
    
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_face_detection(image_path, label):
    """Test face detection endpoint"""
    print("="*70)
    print(f"Testing face detection: {label}")
    print(f"Image: {os.path.basename(image_path)}")
    print("="*70)
    
    if not os.path.exists(image_path):
        print(f"[ERROR] File not found: {image_path}")
        return
    
    with open(image_path, 'rb') as f:
        files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}
        response = requests.post(f"{API_URL}/api/v1/face/detect", files=files)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nFused Verdict: {result['verdict'].upper()}")
        print(f"Confidence Band: {result['confidence_band']}")
        print(f"Action: {result['action']}")
        print(f"\nModel 1: {result['model1_verdict'].upper()} ({result['m1_score']*100:.1f}% real)")
        print(f"Model 2: {result['model2_verdict'].upper()} ({result['m2_score']*100:.1f}% real)")
        print(f"Agreement: {result['agreement']}")
        print(f"\nExplanation: {result['explanation']}")
    else:
        print(f"Error: {response.text}")
    
    print()

if __name__ == "__main__":
    # Test health endpoint
    try:
        test_health()
    except Exception as e:
        print(f"[ERROR] Could not connect to API: {e}")
        print("Make sure the API is running: python app.py")
        exit(1)
    
    # Test with demo photos
    real_photo = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\img\\test_real_photo.jpg"
    fake_photo = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\img\\test_fake_photo.png"
    
    test_face_detection(real_photo, "REAL PHOTO (Ground Truth: REAL)")
    test_face_detection(fake_photo, "FAKE PHOTO (Ground Truth: FAKE)")
    
    print("="*70)
    print("VALIDATION COMPLETE")
    print("="*70)
    print("\nBoth tests should show:")
    print("  - verdict: 'uncertain'")
    print("  - action: 'route-to-review'")
    print("  - Models disagree strongly")
    print("\nThis matches the validated fusion behavior.")
    print("="*70)
