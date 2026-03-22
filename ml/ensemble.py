from typing import Optional
import numpy as np
from main import GridState
from ml.online_learner import OnlineLearner
from ml.lstm_predictor import LSTMPredictor

class EnsemblePredictor:
    """
    Combines OnlineLearner and LSTMPredictor with dynamic weighting.
    """
    
    def __init__(self):
        self.online = OnlineLearner()
        self.lstm = LSTMPredictor()
        
    def save(self, dir_path: str):
        import os
        os.makedirs(dir_path, exist_ok=True)
        self.online.save(f"{dir_path}/online.pkl")
        self.lstm.save(f"{dir_path}/lstm.pt")
        
    def load(self, dir_path: str):
        import os
        if os.path.exists(f"{dir_path}/online.pkl"):
            self.online.load(f"{dir_path}/online.pkl")
        if os.path.exists(f"{dir_path}/lstm.pt"):
            self.lstm.load(f"{dir_path}/lstm.pt")
    
    def collect_data_point(self, state: GridState):
        self.online.update(state)
        self.lstm.collect(state)
    
    def predict(self, state: GridState, electricity_rate: float = 6.50) -> Optional[float]:
        p_online = self.online.predict(state)
        p_lstm = self.lstm.predict(state)
        
        if p_online is None and p_lstm is None:
            return None
        if p_online is None:
            return p_lstm
        if p_lstm is None:
            return p_online
        
        # Dynamic weighting
        err_online = self.online.recent_mae + 1e-6
        err_lstm = float(np.mean(list(self.lstm.recent_errors))) + 1e-6 if self.lstm.recent_errors else err_online
        
        total = err_online + err_lstm
        w_online = 1 - (err_online / total)
        w_lstm = 1 - (err_lstm / total)
        w_sum = w_online + w_lstm
        
        return float((p_online * (w_online / w_sum)) + (p_lstm * (w_lstm / w_sum)))

    @property
    def is_trained(self) -> bool:
        return self.online.is_ready
    
    @property
    def training_data(self):
        return [0] * self.online.samples_seen
        
    @property
    def min_training_samples(self) -> int:
        return self.online.min_samples
    
    @property
    def is_ready(self) -> bool:
        return self.online.is_ready or self.lstm.is_ready
    
    @property
    def samples_collected(self) -> int:
        return self.online.samples_seen
