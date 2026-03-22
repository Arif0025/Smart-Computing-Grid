import numpy as np

class ConformalWrapper:
    def __init__(self, alpha: float = 0.10):
        self.alpha = alpha
        self.is_calibrated = False
        self.calibration_data = [] 
        self._calibration_X = []
        self._calibration_y = []
        self.min_calibration_samples = 100
        
        try:
            from mapie.regression import MapieRegressor
            from sklearn.linear_model import Ridge
            self.mapie = None
            self._base_model = Ridge()
            self._has_mapie = True
        except ImportError:
            self._has_mapie = False
            
    def save(self, filepath: str):
        if self._has_mapie and self.mapie:
            import pickle
            with open(filepath, 'wb') as f:
                pickle.dump(self.mapie, f)

    def load(self, filepath: str):
        if self._has_mapie:
            import pickle
            try:
                with open(filepath, 'rb') as f:
                    self.mapie = pickle.load(f)
                    self.is_calibrated = True
            except FileNotFoundError:
                pass
    
    def add_calibration_point(self, features: dict, actual_power: float):
        feature_vector = list(features.values())
        self._calibration_X.append(feature_vector)
        self._calibration_y.append(actual_power)
        
        if len(self._calibration_X) >= self.min_calibration_samples and not self.is_calibrated:
            self._calibrate()
    
    def _calibrate(self):
        if not self._has_mapie:
            self.is_calibrated = True
            return

        from mapie.regression import MapieRegressor
        X = np.array(self._calibration_X)
        y = np.array(self._calibration_y)
        
        self.mapie = MapieRegressor(
            estimator=self._base_model,
            method="plus",      
            cv=5
        )
        self.mapie.fit(X, y)
        self.is_calibrated = True
    
    def predict_with_interval(self, features: dict, point_estimate: float) -> dict:
        if not self.is_calibrated or not self._has_mapie:
            margin = point_estimate * 0.15
            return {
                "prediction": point_estimate,
                "lower": point_estimate - margin,
                "upper": point_estimate + margin,
                "coverage": 0.85,
                "calibrated": False
            }
        
        X = np.array([list(features.values())])
        _, intervals = self.mapie.predict(X, alpha=self.alpha)
        
        lower = float(intervals[0, 0, 0])
        upper = float(intervals[0, 1, 0])
        
        return {
            "prediction": point_estimate,
            "lower": max(0, lower),
            "upper": upper,
            "coverage": 1 - self.alpha,
            "calibrated": True
        }
