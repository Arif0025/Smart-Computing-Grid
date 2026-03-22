from collections import deque
from datetime import datetime
from typing import Optional
from main import GridState
import numpy as np

class OnlineLearner:
    def __init__(self):
        self.samples_seen = 0
        self.recent_errors = deque(maxlen=100)
        self.is_ready = False
        self.min_samples = 10
        try:
            from river import linear_model, preprocessing, compose, metrics
            self.model = compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.PARegressor(C=0.1, eps=0.1)
            )
            self.mae = metrics.MAE()
            self._has_river = True
        except ImportError:
            self.model = None
            self.mae = None
            self._has_river = False
            
    def save(self, filepath: str):
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'mae': self.mae,
                'samples_seen': self.samples_seen,
                'recent_errors': self.recent_errors,
                'is_ready': self.is_ready
            }, f)
            
    def load(self, filepath: str):
        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.mae = data['mae']
            self.samples_seen = data['samples_seen']
            self.recent_errors = data['recent_errors']
            self.is_ready = data['is_ready']
    
    def _extract_features(self, state: GridState, custom_timestamp: Optional[datetime] = None) -> dict:
        now = custom_timestamp if custom_timestamp else datetime.now()
        hour = now.hour
        return {
            'hour_sin': float(np.sin(2 * np.pi * hour / 24)),
            'hour_cos': float(np.cos(2 * np.pi * hour / 24)),
            'day_sin': float(np.sin(2 * np.pi * now.weekday() / 7)),
            'day_cos': float(np.cos(2 * np.pi * now.weekday() / 7)),
            'avg_load': state.avg_load,
            'load_variance': float(np.var([n.load for n in state.nodes])) if state.nodes else 0.0,
            'avg_temp': state.avg_temperature,
            'temp_variance': float(np.var([n.temperature for n in state.nodes])) if state.nodes else 0.0,
            'active_nodes': len([n for n in state.nodes if n.load > 0.1]),
            'num_nodes': len(state.nodes),
        }
    
    def update(self, state: GridState):
        features = self._extract_features(state)
        actual = state.total_power
        
        if not self._has_river:
            self.samples_seen += 1
            if self.samples_seen >= self.min_samples:
                self.is_ready = True
            return actual * 0.95 
            
        if self.samples_seen >= self.min_samples:
            predicted = self.model.predict_one(features)
            if predicted is not None:
                error = abs(predicted - actual)
                self.recent_errors.append(error)
                self.mae.update(actual, predicted)
        
        self.model.learn_one(features, actual)
        self.samples_seen += 1
        
        if self.samples_seen >= self.min_samples:
            self.is_ready = True
        
        return self.model.predict_one(features)
    
    def predict(self, state: GridState) -> Optional[float]:
        if not self.is_ready:
            return None
        if not self._has_river:
            return state.total_power * 1.05
        return self.model.predict_one(self._extract_features(state))
    
    @property
    def recent_mae(self) -> float:
        return float(np.mean(self.recent_errors)) if self.recent_errors else float('inf')
