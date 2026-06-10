import math
from collections import defaultdict
from typing import List, Dict
from sre_pipeline.models import AnomalyFingerprint

class AdaptiveDetector:
    def __init__(self, default_threshold: int = 5, history_size: int = 20) -> None:
        self.default_threshold = default_threshold
        self.history_size = history_size
        self.history: Dict[str, List[int]] = defaultdict(list)
        
    def record_window(self, fingerprint: AnomalyFingerprint, count: int) -> None:
        hist = self.history[fingerprint.fingerprint_hash]
        hist.append(count)
        if len(hist) > self.history_size:
            hist.pop(0)
            
    def _compute_stats(self, hist: List[int]) -> tuple[float, float]:
        if not hist:
            return 0.0, 0.0
        mean = sum(hist) / len(hist)
        if len(hist) < 2:
            return mean, 0.0
        variance = sum((x - mean) ** 2 for x in hist) / (len(hist) - 1)
        return mean, math.sqrt(variance)

    def is_anomaly(self, fingerprint: AnomalyFingerprint, current_count: int) -> bool:
        hist = self.history.get(fingerprint.fingerprint_hash, [])
        if not hist:
            return current_count > self.default_threshold
            
        mean, std_dev = self._compute_stats(hist)
        # We use a minimum threshold to avoid triggering on 1 or 2 events when mean is 0
        adaptive_threshold = max(self.default_threshold, mean + 2 * std_dev)
        
        return current_count > adaptive_threshold
