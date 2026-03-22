from collections import deque
from datetime import datetime
from typing import Optional, List
import numpy as np
from main import GridState

class LSTMPredictor:
    def __init__(self, sequence_length=60, input_size=10):
        self.sequence_length = sequence_length
        self.input_size = input_size
        self.buffer: deque = deque(maxlen=500)
        self.is_ready = False
        self.recent_errors = deque(maxlen=100)
        self.last_retrain = datetime.now()
        
        try:
            import torch
            import torch.nn as nn
            class PowerLSTM(nn.Module):
                def __init__(self, input_size=10, hidden_size=64, num_layers=2, dropout=0.1):
                    super().__init__()
                    self.lstm = nn.LSTM(
                        input_size=input_size,
                        hidden_size=hidden_size,
                        num_layers=num_layers,
                        dropout=dropout,
                        batch_first=True
                    )
                    self.fc = nn.Linear(hidden_size, 1)
                
                def forward(self, x):
                    out, _ = self.lstm(x)
                    return self.fc(out[:, -1, :]).squeeze(-1)
            
            self.model = PowerLSTM(input_size=input_size)
            self.optimizer_torch = torch.optim.Adam(self.model.parameters(), lr=0.001)
            self._has_torch = True
        except ImportError:
            self._has_torch = False
            self.model = None

    def save(self, filepath: str):
        if self._has_torch and self.model:
            import torch
            torch.save(self.model.state_dict(), filepath)
            
    def load(self, filepath: str):
        if self._has_torch and self.model:
            import torch
            self.model.load_state_dict(torch.load(filepath, weights_only=True))
            self.model.eval()
            self.is_ready = True

    def _state_to_vector(self, state: GridState, custom_timestamp: Optional[datetime] = None) -> List[float]:
        now = custom_timestamp if custom_timestamp else datetime.now()
        hour = now.hour
        return [
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * now.weekday() / 7),
            np.cos(2 * np.pi * now.weekday() / 7),
            state.avg_load,
            np.var([n.load for n in state.nodes]) if state.nodes else 0,
            state.avg_temperature,
            np.var([n.temperature for n in state.nodes]) if state.nodes else 0,
            len([n for n in state.nodes if n.load > 0.1]) / max(len(state.nodes), 1),
            state.total_power / 5000.0,
        ]
        
    def train_offline_epochs(self, data_states: List[GridState], epochs: int = 50):
        if not self._has_torch:
            return
            
        import torch
        import torch.nn as nn
        
        X, y = [], []
        seq = []
        for state in data_states:
            is_gap = getattr(state, 'is_gap_after', False)
            features = self._state_to_vector(state, datetime.fromisoformat(state.timestamp))
            seq.append({'features': features, 'target': state.total_power})
            
            if len(seq) > self.sequence_length:
                s_feat = [d['features'] for d in seq[-self.sequence_length-1:-1]]
                s_targ = seq[-1]['target']
                X.append(s_feat)
                y.append(s_targ)
                
            if is_gap:
                seq.clear() # break sequence 
                
        if len(X) == 0:
            return
            
        X_t = torch.tensor(X, dtype=torch.float32)
        y_t = torch.tensor(y, dtype=torch.float32)
        
        self.model.train()
        for epoch in range(epochs):
            self.optimizer_torch.zero_grad()
            pred = self.model(X_t)
            loss = nn.MSELoss()(pred, y_t)
            loss.backward()
            self.optimizer_torch.step()
            
        self.model.eval()
        self.is_ready = True
    
    def collect(self, state: GridState):
        self.buffer.append({
            'features': self._state_to_vector(state),
            'target': state.total_power
        })
        
        should_retrain = (
            len(self.buffer) >= 200 and
            (datetime.now() - self.last_retrain).seconds > 300
        )
        if should_retrain and self._has_torch:
            self._train()
        elif should_retrain and not self._has_torch:
            self.is_ready = True
    
    def _train(self):
        import torch
        import torch.nn as nn
        data = list(self.buffer)
        if len(data) < self.sequence_length + 1:
            return
        
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            seq = [d['features'] for d in data[i:i+self.sequence_length]]
            X.append(seq)
            y.append(data[i + self.sequence_length]['target'])
        
        X_t = torch.tensor(X, dtype=torch.float32)
        y_t = torch.tensor(y, dtype=torch.float32)
        
        self.model.train()
        for _ in range(5):
            self.optimizer_torch.zero_grad()
            pred = self.model(X_t)
            loss = nn.MSELoss()(pred, y_t)
            loss.backward()
            self.optimizer_torch.step()
        
        self.model.eval()
        self.is_ready = True
        self.last_retrain = datetime.now()
    
    def predict(self, state: GridState) -> Optional[float]:
        if not self.is_ready or len(self.buffer) < self.sequence_length:
            return None
        
        if not self._has_torch:
            return state.total_power * 1.02
            
        import torch
        recent = list(self.buffer)[-self.sequence_length:]
        X = torch.tensor([[d['features'] for d in recent]], dtype=torch.float32)
        
        with torch.no_grad():
            pred = self.model(X).item()
        return pred
