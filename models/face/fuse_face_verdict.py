"""
Litmus FaceGuard - Ensemble Fusion with Confidence-Aware Routing

The key insight: when models disagree, that disagreement is a signal that
the sample is risky/ambiguous and should go to human review, not auto-approval.

This is not a fallback - this is the architecture working as designed.
"""

def fuse_face_verdict(model1_result, model2_result):
    """
    Fuse verdicts from two deepfake detection models with confidence-aware routing.
    
    Args:
        model1_result: dict with {'verdict': 'real'|'fake', 'real_score': float}
        model2_result: dict with {'verdict': 'real'|'fake', 'real_score': float}
        
    Returns:
        dict: {
            'final_verdict': 'real' | 'fake' | 'uncertain',
            'confidence': 'high' | 'low',
            'action': 'auto-approve' | 'route-to-review',
            'explanation': str,
            'model1_verdict': str,
            'model2_verdict': str,
            'model1_confidence': float,
            'model2_confidence': float
        }
    """
    
    CONFIDENCE_THRESHOLD = 0.70  # 70% confidence required
    
    m1_verdict = model1_result['verdict']
    m2_verdict = model2_result['verdict']
    m1_score = model1_result['real_score']
    m2_score = model2_result['real_score']
    
    # Calculate confidence for each model's verdict
    # If verdict is 'real', confidence = real_score
    # If verdict is 'fake', confidence = 1 - real_score
    m1_confidence = m1_score if m1_verdict == 'real' else (1 - m1_score)
    m2_confidence = m2_score if m2_verdict == 'real' else (1 - m2_score)
    
    # Check agreement
    models_agree = (m1_verdict == m2_verdict)
    
    # Check if both are confident (above threshold)
    m1_is_confident = m1_confidence >= CONFIDENCE_THRESHOLD
    m2_is_confident = m2_confidence >= CONFIDENCE_THRESHOLD
    both_confident = m1_is_confident and m2_is_confident
    
    # Decision logic
    if models_agree and both_confident:
        # Both models agree with high confidence
        final_verdict = m1_verdict  # Same as m2_verdict since they agree
        confidence = 'high'
        action = 'auto-approve'
        explanation = f"Both models agree: {final_verdict.upper()} (M1: {m1_confidence*100:.1f}%, M2: {m2_confidence*100:.1f}%)"
    else:
        # Models disagree OR at least one has low confidence
        final_verdict = 'uncertain'
        confidence = 'low'
        action = 'route-to-review'
        
        if not models_agree:
            explanation = f"Models disagree (M1: {m1_verdict.upper()} {m1_confidence*100:.1f}%, M2: {m2_verdict.upper()} {m2_confidence*100:.1f}%) - routed to human review"
        else:
            # They agree but at least one lacks confidence
            low_conf_model = "M1" if not m1_is_confident else "M2"
            explanation = f"Models agree ({m1_verdict.upper()}) but {low_conf_model} confidence below threshold - routed to human review"
    
    return {
        'final_verdict': final_verdict,
        'confidence': confidence,
        'action': action,
        'explanation': explanation,
        'model1_verdict': m1_verdict,
        'model2_verdict': m2_verdict,
        'model1_confidence': m1_confidence,
        'model2_confidence': m2_confidence,
        'agreement': models_agree
    }


if __name__ == "__main__":
    # Test with example results
    
    # Example 1: Strong disagreement (like our real photo test)
    print("="*70)
    print("Example 1: Real photo with strong model disagreement")
    print("="*70)
    m1 = {'verdict': 'fake', 'real_score': 0.1114}
    m2 = {'verdict': 'real', 'real_score': 0.9987}
    result = fuse_face_verdict(m1, m2)
    print(f"Model 1: {m1['verdict'].upper()} ({m1['real_score']*100:.2f}% real)")
    print(f"Model 2: {m2['verdict'].upper()} ({m2['real_score']*100:.2f}% real)")
    print(f"\nFused Result:")
    print(f"  Verdict: {result['final_verdict'].upper()}")
    print(f"  Action: {result['action']}")
    print(f"  Explanation: {result['explanation']}")
    
    # Example 2: Strong disagreement (like our fake photo test)
    print("\n" + "="*70)
    print("Example 2: Fake photo with strong model disagreement")
    print("="*70)
    m1 = {'verdict': 'fake', 'real_score': 0.1857}
    m2 = {'verdict': 'real', 'real_score': 0.9991}
    result = fuse_face_verdict(m1, m2)
    print(f"Model 1: {m1['verdict'].upper()} ({m1['real_score']*100:.2f}% real)")
    print(f"Model 2: {m2['verdict'].upper()} ({m2['real_score']*100:.2f}% real)")
    print(f"\nFused Result:")
    print(f"  Verdict: {result['final_verdict'].upper()}")
    print(f"  Action: {result['action']}")
    print(f"  Explanation: {result['explanation']}")
    
    # Example 3: Strong agreement on real
    print("\n" + "="*70)
    print("Example 3: Both models confidently agree - REAL")
    print("="*70)
    m1 = {'verdict': 'real', 'real_score': 0.85}
    m2 = {'verdict': 'real', 'real_score': 0.92}
    result = fuse_face_verdict(m1, m2)
    print(f"Model 1: {m1['verdict'].upper()} ({m1['real_score']*100:.2f}% real)")
    print(f"Model 2: {m2['verdict'].upper()} ({m2['real_score']*100:.2f}% real)")
    print(f"\nFused Result:")
    print(f"  Verdict: {result['final_verdict'].upper()}")
    print(f"  Action: {result['action']}")
    print(f"  Explanation: {result['explanation']}")
    
    # Example 4: Strong agreement on fake
    print("\n" + "="*70)
    print("Example 4: Both models confidently agree - FAKE")
    print("="*70)
    m1 = {'verdict': 'fake', 'real_score': 0.12}
    m2 = {'verdict': 'fake', 'real_score': 0.08}
    result = fuse_face_verdict(m1, m2)
    print(f"Model 1: {m1['verdict'].upper()} ({m1['real_score']*100:.2f}% real)")
    print(f"Model 2: {m2['verdict'].upper()} ({m2['real_score']*100:.2f}% real)")
    print(f"\nFused Result:")
    print(f"  Verdict: {result['final_verdict'].upper()}")
    print(f"  Action: {result['action']}")
    print(f"  Explanation: {result['explanation']}")
    
    # Example 5: Agreement but low confidence
    print("\n" + "="*70)
    print("Example 5: Models agree but one has low confidence")
    print("="*70)
    m1 = {'verdict': 'real', 'real_score': 0.55}  # Only 55% confident
    m2 = {'verdict': 'real', 'real_score': 0.88}
    result = fuse_face_verdict(m1, m2)
    print(f"Model 1: {m1['verdict'].upper()} ({m1['real_score']*100:.2f}% real)")
    print(f"Model 2: {m2['verdict'].upper()} ({m2['real_score']*100:.2f}% real)")
    print(f"\nFused Result:")
    print(f"  Verdict: {result['final_verdict'].upper()}")
    print(f"  Action: {result['action']}")
    print(f"  Explanation: {result['explanation']}")
    
    print("\n" + "="*70)
