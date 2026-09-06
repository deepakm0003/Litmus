"""
Download large datasets from Kaggle for meta-model training.
This replaces manual collection of 30+ samples with statistically robust datasets.
"""

import os
import subprocess
import sys

def setup_kaggle_credentials():
    """
    Guide user through Kaggle API setup.
    """
    print("="*70)
    print("KAGGLE API SETUP")
    print("="*70)
    print("\nTo download Kaggle datasets, you need API credentials:")
    print("\n1. Go to https://www.kaggle.com/settings")
    print("2. Scroll to 'API' section")
    print("3. Click 'Create New Token'")
    print("4. Download kaggle.json file")
    print("5. Place it in: C:\\Users\\{}\\.kaggle\\kaggle.json".format(os.getenv('USERNAME')))
    print("\nOr set environment variables:")
    print("  KAGGLE_USERNAME=your_username")
    print("  KAGGLE_KEY=your_api_key")
    print("="*70)
    
    # Check if credentials exist
    kaggle_dir = os.path.expanduser("~/.kaggle")
    kaggle_json = os.path.join(kaggle_dir, "kaggle.json")
    
    if os.path.exists(kaggle_json):
        print(f"\n✓ Found: {kaggle_json}")
        return True
    elif os.getenv('KAGGLE_USERNAME') and os.getenv('KAGGLE_KEY'):
        print("\n✓ Found: Environment variables KAGGLE_USERNAME and KAGGLE_KEY")
        return True
    else:
        print(f"\n✗ Missing: {kaggle_json}")
        print("✗ Missing: KAGGLE_USERNAME or KAGGLE_KEY environment variables")
        return False


def download_face_dataset():
    """
    Download 140k Real and Fake Faces dataset for face detection training.
    """
    print("\n" + "="*70)
    print("DOWNLOADING FACE DATASET")
    print("="*70)
    print("\nDataset: 140k Real and Fake Faces")
    print("Size: ~1.2GB")
    print("Contains: Real faces + GAN-generated fake faces")
    print("Use: Face detection meta-model training")
    print("="*70)
    
    face_data_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\kaggle_data"
    os.makedirs(face_data_dir, exist_ok=True)
    
    try:
        cmd = [
            "kaggle", "datasets", "download", 
            "-d", "xhlulu/140k-real-and-fake-faces",
            "-p", face_data_dir,
            "--unzip"
        ]
        
        print(f"\n[RUNNING] {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=face_data_dir)
        
        if result.returncode == 0:
            print(f"✓ Downloaded to: {face_data_dir}")
            
            # List contents
            print("\n[CONTENTS]")
            for root, dirs, files in os.walk(face_data_dir):
                level = root.replace(face_data_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # Show first 5 files
                    print(f"{subindent}{file}")
                if len(files) > 5:
                    print(f"{subindent}... and {len(files)-5} more files")
            
            return True
        else:
            print(f"✗ Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def download_voice_dataset():
    """
    Download fake or real voice dataset for voice detection training.
    """
    print("\n" + "="*70)
    print("DOWNLOADING VOICE DATASET")
    print("="*70)
    print("\nDataset: The Fake or Real Dataset")
    print("Size: ~500MB")
    print("Contains: Real speech + AI-generated speech")
    print("Use: Voice detection meta-model training")
    print("="*70)
    
    voice_data_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\voice\\kaggle_data"
    os.makedirs(voice_data_dir, exist_ok=True)
    
    try:
        cmd = [
            "kaggle", "datasets", "download",
            "-d", "mohammedabdeldayem/the-fake-or-real-dataset",
            "-p", voice_data_dir,
            "--unzip"
        ]
        
        print(f"\n[RUNNING] {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=voice_data_dir)
        
        if result.returncode == 0:
            print(f"✓ Downloaded to: {voice_data_dir}")
            
            # List contents
            print("\n[CONTENTS]")
            for root, dirs, files in os.walk(voice_data_dir):
                level = root.replace(voice_data_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # Show first 5 files
                    print(f"{subindent}{file}")
                if len(files) > 5:
                    print(f"{subindent}... and {len(files)-5} more files")
            
            return True
        else:
            print(f"✗ Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


if __name__ == "__main__":
    print("="*70)
    print("LITMUS - KAGGLE DATASET SETUP")
    print("="*70)
    print("\nThis script downloads large, diverse datasets for meta-model training.")
    print("Much better than manually collecting 30+ samples!")
    print("="*70)
    
    # Check Kaggle credentials
    if not setup_kaggle_credentials():
        print("\n[BLOCKED] Please set up Kaggle credentials first")
        print("Run this script again after setup.")
        sys.exit(1)
    
    print("\n[PROCEEDING] Kaggle credentials found")
    
    # Download datasets
    face_success = download_face_dataset()
    voice_success = download_voice_dataset()
    
    # Summary
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    print(f"\nFace dataset:  {'✓ Success' if face_success else '✗ Failed'}")
    print(f"Voice dataset: {'✓ Success' if voice_success else '✗ Failed'}")
    
    if face_success and voice_success:
        print("\n[COMPLETE] Both datasets downloaded successfully")
        print("Next: Update train_meta_model.py to use Kaggle data")
    elif face_success:
        print("\n[PARTIAL] Face dataset ready, voice dataset failed")
        print("Can proceed with face meta-model training")
    elif voice_success:
        print("\n[PARTIAL] Voice dataset ready, face dataset failed")
        print("Can proceed with voice meta-model training")
    else:
        print("\n[FAILED] No datasets downloaded")
        print("Check Kaggle credentials and network connection")
    
    print("="*70)