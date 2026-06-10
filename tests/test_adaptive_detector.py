import pytest
import datetime
from sre_pipeline.adaptive_detector import AdaptiveDetector
from sre_pipeline.models import AnomalyFingerprint, AdaptiveThreshold

def test_adaptive_detector_no_history() -> None:
    detector = AdaptiveDetector()
    fingerprint = AnomalyFingerprint(
        service="db-primary", rule_id="CRITICAL_LOG", 
        hour_of_day=10, day_of_week=2, fingerprint_hash="hash1"
    )
    # With no history, the detector should perhaps fallback to a static threshold or return False
    # Let's say if count > 5 it triggers when no history
    is_anomaly = detector.is_anomaly(fingerprint, current_count=10)
    assert is_anomaly is True

    is_anomaly_low = detector.is_anomaly(fingerprint, current_count=2)
    assert is_anomaly_low is False

def test_adaptive_detector_with_history() -> None:
    detector = AdaptiveDetector()
    fingerprint = AnomalyFingerprint(
        service="db-primary", rule_id="CRITICAL_LOG", 
        hour_of_day=10, day_of_week=2, fingerprint_hash="hash1"
    )
    # Feed history: 5, 5, 6, 4, 5
    # mean is 5, std is ~0.7. mean + 2*std is ~6.4
    for count in [5, 5, 6, 4, 5]:
        detector.record_window(fingerprint, count)
        
    # 7 is anomaly
    assert detector.is_anomaly(fingerprint, current_count=7) is True
    # 6 is not anomaly
    assert detector.is_anomaly(fingerprint, current_count=6) is False
