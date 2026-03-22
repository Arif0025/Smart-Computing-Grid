import os
import argparse
from ml.data_ingestion import DataIngestionLayer
from ml.ensemble import EnsemblePredictor
from ml.conformal import ConformalWrapper
from ml.shap_explainer import SHAPExplainer
from datetime import datetime, timedelta
import json

def generate_dummy_data(db_path, grid_id="default-grid"):
    from storage.sqlite_backend import SQLiteStorage
    import math
    from main import GridState, Node
    storage = SQLiteStorage(db_path)
    
    base_time = datetime.now() - timedelta(days=7)
    for i in range(5000):
        ts = base_time + timedelta(seconds=i)
        
        hour = ts.hour
        base_load = 0.2 + (math.sin(hour / 24 * 2 * math.pi) * 0.1)
        
        n1 = Node(id="node1", name="node1", cores=8, max_power=200, base_power=50, load=base_load, temperature=30 + base_load*20)
        n2 = Node(id="node2", name="node2", cores=8, max_power=200, base_power=50, load=base_load*1.2, temperature=32 + base_load*20)
        
        p = 100 + (base_load * 300)
        state = GridState(
            nodes=[n1, n2],
            total_power=p,
            unoptimized_power=p*1.1,
            avg_load=base_load,
            avg_temperature=31 + base_load*20,
            timestamp=ts.isoformat()
        )
        storage.save_snapshot(grid_id, state)
    print(f"Generated 5000 dummy records in {db_path}")

def run_pretraining(db_path: str, grid_id: str):
    print("Initializing components...")
    ingestion = DataIngestionLayer()
    states = ingestion.load_from_sqlite(db_path, grid_id)
    
    if not states:
        print("No data found! Run with --dummy to generate data.")
        return
        
    print(f"Loaded {len(states)} historical states.")
    
    prompt = input(f"Do you want to proceed with training on these {len(states)} records? (y/n): ")
    if prompt.lower() != 'y':
        print("Training aborted by user.")
        return
        
    split_idx = int(len(states) * 0.8)
    train_states = states[:split_idx]
    calib_states = states[split_idx:]
    
    print(f"Splitting data: {len(train_states)} train, {len(calib_states)} calibration.")
    
    predictor = EnsemblePredictor()
    conformal = ConformalWrapper()
    shap_explainer = SHAPExplainer()
    
    print("Training Online Learner on 80% split...")
    for i, state in enumerate(train_states):
        ts = datetime.fromisoformat(state.timestamp)
        features = predictor.online._extract_features(state, custom_timestamp=ts)
        actual = state.total_power
        
        if predictor.online._has_river:
            predictor.online.model.learn_one(features, actual)
            predictor.online.samples_seen += 1
            if predictor.online.samples_seen >= predictor.online.min_samples:
                predictor.online.is_ready = True
        
        if i % 50 == 0:
            shap_explainer.add_background_sample(features)
            
        if i % 1000 == 0 and i > 0:
            print(f"  ...processed {i} rows")
    
    print("Training LSTM on 80% split (epochs=10)...")
    predictor.lstm.train_offline_epochs(train_states, epochs=10)
    
    print("Calibrating Conformal on held-out 20% split...")
    for state in calib_states:
        ts = datetime.fromisoformat(state.timestamp)
        features = predictor.online._extract_features(state, custom_timestamp=ts)
        conformal.add_calibration_point(features, state.total_power)
        
    print("Saving artifacts to model_weights/...")
    os.makedirs("model_weights", exist_ok=True)
    predictor.save("model_weights")
    conformal.save("model_weights/conformal.pkl")
    
    print("Pre-training complete! Artifacts saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="./grid_history.db")
    parser.add_argument("--grid", default="default-grid")
    parser.add_argument("--dummy", action="store_true", help="Generate dummy data first")
    args = parser.parse_args()
    
    if args.dummy:
        generate_dummy_data(args.db, args.grid)
        
    run_pretraining(args.db, args.grid)
