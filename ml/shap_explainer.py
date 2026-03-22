import numpy as np
from typing import List, Tuple

def _generate_text_explanation(top_3: List[Tuple[str, float]]) -> str:
    parts = []
    readable = {
        'avg_load': 'average server load',
        'avg_temp': 'average temperature',
        'hour_sin': 'time of day',
        'hour_cos': 'time of day',
        'load_variance': 'load imbalance',
        'active_nodes': 'number of active servers',
    }
    for feature, impact in top_3:
        name = readable.get(feature, feature)
        direction = "high" if impact > 0 else "low"
        parts.append(f"{direction} {name} (+{impact:.0f}W)" if impact > 0 else f"{direction} {name} ({impact:.0f}W)")
    return "Prediction driven by: " + ", ".join(parts)

class SHAPExplainer:
    def __init__(self):
        self.background_data = []
        self.is_ready = False
        self.feature_names = [
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'avg_load', 'load_variance', 'avg_temp', 'temp_variance',
            'active_nodes', 'num_nodes'
        ]
        try:
            import shap
            self.explainer = None
            self._has_shap = True
        except ImportError:
            self._has_shap = False
    
    def add_background_sample(self, features: dict):
        self.background_data.append(list(features.values()))
        if len(self.background_data) >= 50 and not self.is_ready:
            self._build_explainer()
    
    def _build_explainer(self):
        if not self._has_shap:
            self.is_ready = True
            return
            
        import shap
        background = np.array(self.background_data[-50:])
        self.explainer = shap.KernelExplainer(
            model=self._dummy_predict,
            data=shap.kmeans(background, 10)
        )
        self.is_ready = True
    
    def _dummy_predict(self, X):
        return np.zeros(len(X))
    
    def explain(self, features: dict, prediction: float) -> dict:
        if not self.is_ready:
            return {
                "available": False,
                "reason": f"Collecting background data ({len(self.background_data)}/50)"
            }
            
        if not self._has_shap:
            return {
                "available": False,
                "prediction": prediction,
                "reason": "SHAP library not available in environment"
            }
        
        X = np.array([list(features.values())])
        shap_values = self.explainer.shap_values(X, silent=True)[0]
        
        contributions = sorted(
            zip(self.feature_names, shap_values.tolist()),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        return {
            "available": True,
            "prediction": prediction,
            "top_contributors": [
                {
                    "feature": name,
                    "impact": round(value, 2),
                    "direction": "increases_power" if value > 0 else "decreases_power"
                }
                for name, value in contributions[:5]
            ],
            "explanation": _generate_text_explanation(contributions[:3])
        }
