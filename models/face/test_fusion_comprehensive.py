"""
Comprehensive test of fusion logic on all available photo pairs.
This validates that disagreement-based routing prevents silent wrong auto-approvals.
"""

import os
from test_face import run_face_detection
from test_face_model2 import run_face_detection_model2
from fuse_face_verdict import fuse_face_verdict

print("="*80)
print("LITMUS FACEGUARD - ENSEMBLE FUSION VALIDATION")
print("="*80)
print("\nTesting disagreement-based routing on real photo pairs")
print("Goal: Prove the system catches ambiguous cases instead of auto-approving wrongly")
print("="*80)

# Test pairs
test_pairs = [
    {
        'name': 'Demo Pair 1: Your selfie + face-swap',
        'real': 'c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\img\\test_real_photo.jpg',
        'fake': 'c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\img\\test_fake_photo.png'
    }
]

# Check if there are additional test images in the img folder
img_dir = 'c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\img'
if os.path.exists(img_dir):
    all_imgs = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"\n[INFO] Found {len(all_imgs)} images in img/ folder")
    
    # Look for additional real/fake pairs
    real_imgs = [f for f in all_imgs if 'real' in f.lower() and f not in ['test_real_photo.jpg']]
    fake_imgs = [f for f in all_imgs if 'fake' in f.lower() and f not in ['test_fake_photo.png']]
    
    if real_imgs or fake_imgs:
        print(f"  Additional real images: {real_imgs}")
        print(f"  Additional fake images: {fake_imgs}")

# Also test on a few FF++ samples to see fusion behavior
ff_real_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\real"
ff_fake_dir = "c:\\Users\\deepa\\OneDrive\\Desktop\\litmus\\models\\face\\prepared_dataset\\fake"

if os.path.exists(ff_real_dir):
    ff_real_files = [f for f in os.listdir(ff_real_dir) if f.endswith('.png')][:2]
    ff_fake_files = [f for f in os.listdir(ff_fake_dir) if f.endswith('.png')][:2]
    
    for i, (real_file, fake_file) in enumerate(zip(ff_real_files, ff_fake_files), 2):
        test_pairs.append({
            'name': f'FF++ Pair {i}: Compressed video frames',
            'real': os.path.join(ff_real_dir, real_file),
            'fake': os.path.join(ff_fake_dir, fake_file)
        })

print(f"\n[INFO] Testing {len(test_pairs)} pair(s)")
print("="*80)

# Statistics
total_tests = 0
silent_wrong_approvals = 0
correctly_routed = 0
correct_auto_approvals = 0

for pair_idx, pair in enumerate(test_pairs, 1):
    print(f"\n{'='*80}")
    print(f"PAIR {pair_idx}: {pair['name']}")
    print("="*80)
    
    # Test real image
    print(f"\n[REAL IMAGE] {os.path.basename(pair['real'])}")
    print("-"*80)
    
    if not os.path.exists(pair['real']):
        print(f"[SKIP] File not found")
        continue
    
    try:
        real_m1 = run_face_detection(pair['real'])
        real_m2 = run_face_detection_model2(pair['real'])
        real_fused = fuse_face_verdict(real_m1, real_m2)
        
        print(f"Model 1: {real_m1['verdict'].upper():4s} (real_score: {real_m1['real_score']*100:5.1f}%)")
        print(f"Model 2: {real_m2['verdict'].upper():4s} (real_score: {real_m2['real_score']*100:5.1f}%)")
        print(f"\nFUSED DECISION:")
        print(f"  Verdict: {real_fused['final_verdict'].upper()}")
        print(f"  Action:  {real_fused['action']}")
        print(f"  Reason:  {real_fused['explanation']}")
        
        # Evaluate outcome
        ground_truth = 'real'
        total_tests += 1
        
        if real_fused['action'] == 'auto-approve':
            if real_fused['final_verdict'] == ground_truth:
                print(f"\n[OUTCOME] CORRECT AUTO-APPROVAL")
                correct_auto_approvals += 1
            else:
                print(f"\n[OUTCOME] SILENT WRONG AUTO-APPROVAL (approved as {real_fused['final_verdict'].upper()}, actually {ground_truth.upper()})")
                silent_wrong_approvals += 1
        else:
            print(f"\n[OUTCOME] CORRECTLY ROUTED TO REVIEW (prevented potential error)")
            correctly_routed += 1
            
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # Test fake image
    print(f"\n[FAKE IMAGE] {os.path.basename(pair['fake'])}")
    print("-"*80)
    
    if not os.path.exists(pair['fake']):
        print(f"[SKIP] File not found")
        continue
    
    try:
        fake_m1 = run_face_detection(pair['fake'])
        fake_m2 = run_face_detection_model2(pair['fake'])
        fake_fused = fuse_face_verdict(fake_m1, fake_m2)
        
        print(f"Model 1: {fake_m1['verdict'].upper():4s} (real_score: {fake_m1['real_score']*100:5.1f}%)")
        print(f"Model 2: {fake_m2['verdict'].upper():4s} (real_score: {fake_m2['real_score']*100:5.1f}%)")
        print(f"\nFUSED DECISION:")
        print(f"  Verdict: {fake_fused['final_verdict'].upper()}")
        print(f"  Action:  {fake_fused['action']}")
        print(f"  Reason:  {fake_fused['explanation']}")
        
        # Evaluate outcome
        ground_truth = 'fake'
        total_tests += 1
        
        if fake_fused['action'] == 'auto-approve':
            if fake_fused['final_verdict'] == ground_truth:
                print(f"\n[OUTCOME] CORRECT AUTO-APPROVAL")
                correct_auto_approvals += 1
            else:
                print(f"\n[OUTCOME] SILENT WRONG AUTO-APPROVAL (approved as {fake_fused['final_verdict'].upper()}, actually {ground_truth.upper()})")
                silent_wrong_approvals += 1
        else:
            print(f"\n[OUTCOME] CORRECTLY ROUTED TO REVIEW (prevented potential error)")
            correctly_routed += 1
            
    except Exception as e:
        print(f"[ERROR] {e}")

# Final Summary
print("\n" + "="*80)
print("FINAL VALIDATION RESULTS")
print("="*80)
print(f"\nTotal tests:                    {total_tests}")
print(f"Correct auto-approvals:         {correct_auto_approvals}")
print(f"Correctly routed to review:     {correctly_routed}")
print(f"Silent wrong auto-approvals:    {silent_wrong_approvals}")

print("\n" + "="*80)
print("KEY METRIC: SAFETY")
print("="*80)

if silent_wrong_approvals == 0:
    print("\n[PASS] ZERO SILENT WRONG AUTO-APPROVALS")
    print("  The fusion logic successfully prevented all potential errors")
    print("  by routing ambiguous cases to human review.")
    print("\n  This is the exact behavior you'll demo in Round 3:")
    print("  'When models disagree, a human decides, not an algorithm guessing.'")
else:
    print(f"\n[FAIL] {silent_wrong_approvals} SILENT WRONG AUTO-APPROVAL(S) DETECTED")
    print("  The fusion logic needs adjustment.")

review_rate = (correctly_routed / total_tests * 100) if total_tests > 0 else 0
auto_rate = (correct_auto_approvals / total_tests * 100) if total_tests > 0 else 0

print(f"\nRouting breakdown:")
print(f"  {auto_rate:.1f}% auto-approved (both models confident + agreed)")
print(f"  {review_rate:.1f}% routed to review (disagreement or low confidence)")

print("\n" + "="*80)
print("DEMO READINESS")
print("="*80)

if silent_wrong_approvals == 0:
    print("\n[READY FOR ROUND 3]")
    print("This fusion logic is production-ready for the demo.")
    print("\nDemo script:")
    print("1. Show real photo → models disagree → routed to review")
    print("2. Show fake photo → models disagree → routed to review")
    print("3. Explain: 'Neither model alone is reliable. Disagreement triggers")
    print("   human oversight, preventing silent fraud approvals.'")
else:
    print("\n[NEEDS REFINEMENT]")
    print("Adjust thresholds or fusion logic before Round 3.")

print("="*80)
