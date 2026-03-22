from typing import Tuple, Optional
from collections import deque
import numpy as np

class FaultDetector:
    def __init__(self, stuck_threshold=20, spike_sigma=4.0):
        self.history = {}  # node_id → deque of recent values
        self.stuck_threshold = stuck_threshold
        self.spike_sigma = spike_sigma

    def check(self, node_id: str, value: float, field: str) -> Tuple[str, Optional[str]]:
        key = f"{node_id}.{field}"
        if key not in self.history:
            self.history[key] = deque(maxlen=60)
        
        self.history[key].append(value)
        recent = list(self.history[key])
        
        # Stuck sensor: no variation over threshold samples
        if len(recent) >= self.stuck_threshold:
            if max(recent[-self.stuck_threshold:]) == min(recent[-self.stuck_threshold:]):
                return "fault", "stuck_sensor"
        
        # Spike detection: value is N standard deviations from recent mean
        if len(recent) >= 10:
            mean = np.mean(recent[:-1])
            std = np.std(recent[:-1])
            if std > 0 and abs(value - mean) > self.spike_sigma * std:
                return "degraded", "spike"
        
        # Dropout: value is zero or negative when it shouldn't be
        if value <= 0 and field in ("power_watts", "temperature"):
            return "fault", "dropout"
        
        return "good", None
