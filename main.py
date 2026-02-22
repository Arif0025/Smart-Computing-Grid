"""
Enhanced Smart Computing Grid Simulator Backend
- Proactive Load Balancing Optimizer
- Improved ML Model with Peak Detection
- Green Savings Tracking

Installation:
pip install fastapi uvicorn websockets pydantic numpy scikit-learn pandas

Run:
uvicorn main:app --reload
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Union
import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
import uuid
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import pandas as pd

app = FastAPI(title="Computing Grid Simulator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATA MODELS
# ============================================================================

class NodeConfig(BaseModel):
    name: str
    cores: int
    max_power: float
    base_power: float = None
    cooling_efficiency: float = 0.1
    thermal_mass: float = 1.0

class Node(BaseModel):
    id: str
    name: str
    cores: int
    max_power: float
    base_power: float
    load: float = 0.0
    temperature: float = 25.0
    power_consumption: float = 0.0
    fan_speed: float = 0.0
    fan_override: bool = False
    status: str = "idle"
    cooling_efficiency: float = 0.1
    thermal_mass: float = 1.0

class WorkloadInjection(BaseModel):
    intensity: float
    target_node_id: Optional[str] = None

class GridState(BaseModel):
    nodes: List[Node]
    total_power: float
    unoptimized_power: float
    avg_load: float
    avg_temperature: float
    timestamp: str

class OptimizationEvent(BaseModel):
    timestamp: str
    action: str  # "thermal_relief", "load_balance", "consolidation"
    source_id: str
    target_id: str
    amount: float
    before_source_load: float
    after_source_load: float
    before_target_load: float
    after_target_load: float
    source_temp: float
    target_temp: float
    reason: str
    priority: str  # "critical", "high", "medium", "low"

class PowerPrediction(BaseModel):
    current_power: float
    predicted_next_hour: float
    predicted_daily_avg: float
    predicted_daily_peak: float
    predicted_monthly: float
    estimated_monthly_cost: float
    baseline_monthly_cost: float  # Without optimization
    projected_savings: float
    confidence: float
    timestamp: str

class SavingsMetrics(BaseModel):
    total_power_saved: float
    cost_saved_hour: float
    cost_saved_day: float
    cost_saved_month: float
    efficiency_gain_percent: float
    co2_saved_kg: float  # Bonus: Environmental impact


# ============================================================================
# ENHANCED GRID OPTIMIZER - PROACTIVE & EFFICIENT
# ============================================================================

class GridOptimizer:
    """
    Multi-Mode Optimizer:
    1. REACTIVE: Respond to thermal emergencies (>45°C)
    2. PROACTIVE: Balance loads before problems occur
    3. EFFICIENT: Consolidate idle workloads to save power
    """
    
    def __init__(self, grid):
        self.grid = grid
        self.active = False
        self.mode = "hybrid"  # "thermal_only", "balance_only", or "hybrid"
        self.history: List[OptimizationEvent] = []
        self.last_run = datetime.now()
        self.cooldown = 0.3  # Check every 0.3s for responsiveness
        
        # Thresholds
        self.temp_critical = 48.0  # Emergency threshold
        self.temp_warning = 40.0   # Start balancing here
        self.load_high = 0.75      # Balance if node >75%
        self.load_imbalance = 0.20 # Balance if gap >20%
        self.max_safe_load = 0.85  # Never exceed 85%
        
        # Tracking for savings calculation
        self.total_transfers = 0
        self.power_saved_cumulative = 0.0
        
    def run_cycle(self):
        """Enhanced multi-phase optimization"""
        if not self.active:
            return None
            
        now = datetime.now()
        if (now - self.last_run).total_seconds() < self.cooldown:
            return None
        self.last_run = now
        
        nodes_list = list(self.grid.nodes.values())
        if len(nodes_list) < 2:
            return None
        
        # ========================================
        # PHASE 1: EMERGENCY THERMAL RESPONSE
        # Priority: CRITICAL
        # ========================================
        for node in nodes_list:
            if node.temperature > self.temp_critical:
                # Force max cooling
                if not node.fan_override:
                    node.fan_override = True
                    print(f"⚠️  EMERGENCY: {node.name} OVERHEATING at {node.temperature:.1f}°C")
                
                # Offload immediately if possible
                if node.load > 0.1:
                    return self._emergency_offload(node, nodes_list)
            
            # Reset fan override when safe
            elif node.temperature < 35.0 and node.fan_override:
                node.fan_override = False
        
        # ========================================
        # PHASE 2: PROACTIVE LOAD BALANCING
        # Priority: HIGH (But ONLY for overload, not spreading)
        # ========================================
        nodes_by_load = sorted(nodes_list, key=lambda n: n.load)
        busiest = nodes_by_load[-1]
        idlest = nodes_by_load[0]

        load_gap = busiest.load - idlest.load

        # ONLY balance if busiest node is truly overloaded (>85%)
        if busiest.load > 0.85:  # Changed from 0.75
            # Find target that can handle it
            targets = [n for n in nodes_list if n.id != busiest.id and n.load < 0.80]
            if targets:
                target = max(targets, key=lambda n: n.load)  # Use the BUSIEST available server
                return self._proactive_balance(busiest, target, "high_load")

        # Remove the "Strategy B: Equalize moderate imbalances" section entirely
        # We DON'T want to equalize - we want consolidation!
        
        # ========================================
        # PHASE 3: THERMAL-AWARE BALANCING
        # Priority: MEDIUM
        # ========================================
        # Find warm nodes that could benefit from load reduction
        warm_nodes = [n for n in nodes_list if n.temperature > self.temp_warning and n.load > 0.30]
        cool_nodes = [n for n in nodes_list if n.temperature < self.temp_warning and n.load < self.max_safe_load - 0.15]
        
        if warm_nodes and cool_nodes:
            warmest = max(warm_nodes, key=lambda n: n.temperature)
            coolest = min(cool_nodes, key=lambda n: n.temperature)
            return self._thermal_balance(warmest, coolest)
        
        # ========================================
        # PHASE 4: GREEN CONSOLIDATION
        # Priority: HIGH (not LOW - this should be the default!)
        # ========================================

        # Find small workloads to consolidate
        tiny_loads = [n for n in nodes_list if 0.01 < n.load < 0.20]
        # Find servers with room that are ALREADY being used
        targets = [n for n in nodes_list if 0.30 < n.load < 0.75]  # Target medium-loaded servers

        if tiny_loads and targets:
            source = min(tiny_loads, key=lambda n: n.load)
            target = max(targets, key=lambda n: n.load)  # Pack into the busiest available
            
            if (target.load + source.load) < 0.80:
                return self._consolidate(source, target)
        
        return None
    
    def _emergency_offload(self, source: Node, all_nodes: List[Node]) -> OptimizationEvent:
        """Critical thermal emergency - move maximum load immediately"""
        targets = [n for n in all_nodes if n.id != source.id and n.temperature < 40.0]
        if not targets:
            return None
        
        target = min(targets, key=lambda n: n.temperature)
        
        # Move aggressive amount (up to 50% of load)
        transfer = min(0.50, source.load * 0.6)
        transfer = min(transfer, self.max_safe_load - target.load)
        
        if transfer < 0.05:
            return None
        
        return self._execute_transfer(
            source, target, transfer,
            action="thermal_relief",
            reason=f"CRITICAL: Temperature {source.temperature:.1f}°C",
            priority="critical"
        )
    
    def _proactive_balance(self, source: Node, target: Node, strategy: str) -> OptimizationEvent:
        """Balance loads - CONSOLIDATE don't spread"""
        
        # Only balance if source is CRITICALLY overloaded
        if source.load < 0.85:  # Changed from balancing at 75%
            return None  # Don't balance unless actually overloaded
        
        # Move minimal amount to prevent overload
        transfer = max(0.10, source.load - 0.80)  # Just bring it back to 80%
        transfer = min(transfer, self.max_safe_load - target.load)
        
        if transfer < 0.05:
            return None
        
        reasons = {
            "high_load": f"Preventing overload ({source.load*100:.0f}% → 80%)",
            "load_gap": f"Critical rebalancing"
        }
        
        return self._execute_transfer(
            source, target, transfer,
            action="load_balance",
            reason=reasons.get(strategy, "Emergency balancing"),
            priority="high"
        )
    
    def _thermal_balance(self, source: Node, target: Node) -> OptimizationEvent:
        """Move load from warm to cool nodes"""
        # More aggressive if temperature is high
        if source.temperature > 45.0:
            transfer = 0.25
        else:
            transfer = 0.15
        
        transfer = min(transfer, source.load * 0.4)
        transfer = min(transfer, self.max_safe_load - target.load)
        
        if transfer < 0.05:
            return None
        
        return self._execute_transfer(
            source, target, transfer,
            action="thermal_relief",
            reason=f"Cooling {source.name} ({source.temperature:.1f}°C → estimated {(source.temperature-5):.1f}°C)",
            priority="medium"
        )
    
    def _consolidate(self, source: Node, target: Node) -> OptimizationEvent:
        """Consolidate small workloads for efficiency"""
        transfer = source.load  # Move entire load
        
        return self._execute_transfer(
            source, target, transfer,
            action="consolidation",
            reason=f"Power efficiency (sleep {source.name})",
            priority="low"
        )
    
    def _execute_transfer(self, source: Node, target: Node, amount: float, 
                         action: str, reason: str, priority: str) -> OptimizationEvent:
        """Execute the load transfer and log it"""
        
        # Capture before state
        before_source = source.load
        before_target = target.load
        
        # Execute
        source.load = max(0.0, source.load - amount)
        target.load = min(1.0, target.load + amount)
        
        # Log event with full details
        event = OptimizationEvent(
            timestamp=datetime.now().isoformat(),
            action=action,
            source_id=source.name,
            target_id=target.name,
            amount=amount,
            before_source_load=before_source,
            after_source_load=source.load,
            before_target_load=before_target,
            after_target_load=target.load,
            source_temp=source.temperature,
            target_temp=target.temperature,
            reason=reason,
            priority=priority
        )
        
        self.history.append(event)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        self.total_transfers += 1
        
        print(f"✓ OPTIMIZER [{priority.upper()}]: {action} - {source.name} ({before_source*100:.0f}%→{source.load*100:.0f}%) to {target.name} ({before_target*100:.0f}%→{target.load*100:.0f}%)")
        
        return event


# ============================================================================
# ENHANCED ML POWER PREDICTOR with Peak Detection
# ============================================================================

class PowerPredictor:
    """
    Enhanced ML model that:
    - Learns daily patterns and peaks
    - Predicts with higher accuracy
    - Estimates savings from optimization
    """
    
    def __init__(self):
        # Use Gradient Boosting for better accuracy
        self.model = GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_data = []
        self.min_training_samples = 50
        
        # Track peaks for better prediction
        self.daily_peaks = []
        self.hourly_patterns = {}
        
    def collect_data_point(self, grid_state: GridState):
        """Collect training data with enhanced features"""
        now = datetime.now()
        
        # Calculate additional features
        load_variance = np.var([n.load for n in grid_state.nodes]) if grid_state.nodes else 0
        temp_variance = np.var([n.temperature for n in grid_state.nodes]) if grid_state.nodes else 0
        active_nodes = len([n for n in grid_state.nodes if n.load > 0.1])
        
        features = {
            'hour': now.hour,
            'minute': now.minute,
            'day_of_week': now.weekday(),
            'num_nodes': len(grid_state.nodes),
            'active_nodes': active_nodes,
            'avg_load': grid_state.avg_load,
            'load_variance': load_variance,
            'avg_temp': grid_state.avg_temperature,
            'temp_variance': temp_variance,
            'total_power': grid_state.total_power,
            'unoptimized_power': grid_state.unoptimized_power,
        }
        
        self.training_data.append(features)
        
        # Track hourly patterns
        hour_key = now.hour
        if hour_key not in self.hourly_patterns:
            self.hourly_patterns[hour_key] = []
        self.hourly_patterns[hour_key].append(grid_state.total_power)
        
        # Keep last 2000 samples
        if len(self.training_data) > 2000:
            self.training_data = self.training_data[-2000:]
        
        # Auto-train
        if len(self.training_data) >= self.min_training_samples and not self.is_trained:
            self.train()
        elif self.is_trained and len(self.training_data) % 100 == 0:
            # Retrain periodically for adaptation
            self.train()
    
    def train(self):
        """Train the enhanced prediction model"""
        if len(self.training_data) < self.min_training_samples:
            return False
        
        df = pd.DataFrame(self.training_data)
        
        # Enhanced feature set
        feature_cols = ['hour', 'minute', 'day_of_week', 'num_nodes', 'active_nodes', 
                       'avg_load', 'load_variance', 'avg_temp', 'temp_variance']
        X = df[feature_cols].values
        y = df['total_power'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        score = self.model.score(X_scaled, y)
        print(f"✓ ML MODEL TRAINED: {len(self.training_data)} samples, R² score: {score:.3f}")
        return True
    
    def predict(self, grid_state: GridState, electricity_rate_per_kwh: float = 6.50) -> Optional[PowerPrediction]:
        """Generate comprehensive power predictions"""
        if not self.is_trained:
            return None
        
        now = datetime.now()
        current_power = grid_state.total_power
        
        # Predict next hour
        next_hour_features = np.array([[
            (now.hour + 1) % 24,
            now.minute,
            now.weekday(),
            len(grid_state.nodes),
            len([n for n in grid_state.nodes if n.load > 0.1]),
            grid_state.avg_load,
            np.var([n.load for n in grid_state.nodes]) if grid_state.nodes else 0,
            grid_state.avg_temperature,
            np.var([n.temperature for n in grid_state.nodes]) if grid_state.nodes else 0
        ]])
        
        scaled = self.scaler.transform(next_hour_features)
        predicted_next_hour = max(0, self.model.predict(scaled)[0])
        
        # Predict daily average and peak
        daily_predictions = []
        for hour in range(24):
            features = np.array([[
                hour,
                30,  # mid-hour
                now.weekday(),
                len(grid_state.nodes),
                len([n for n in grid_state.nodes if n.load > 0.1]),
                grid_state.avg_load,
                np.var([n.load for n in grid_state.nodes]) if grid_state.nodes else 0,
                grid_state.avg_temperature,
                np.var([n.temperature for n in grid_state.nodes]) if grid_state.nodes else 0
            ]])
            scaled = self.scaler.transform(features)
            pred = max(0, self.model.predict(scaled)[0])
            daily_predictions.append(pred)
        
        predicted_daily_avg = np.mean(daily_predictions)
        predicted_daily_peak = np.max(daily_predictions)
        
        # Monthly prediction (kWh)
        predicted_monthly_kwh = predicted_daily_avg * 24 * 30 / 1000
        
        # Cost calculations with and without optimization
        optimized_cost = predicted_monthly_kwh * electricity_rate_per_kwh
        
        # Estimate baseline (without optimizer) - use unoptimized_power if available
        baseline_power = grid_state.unoptimized_power if grid_state.unoptimized_power > current_power else current_power * 1.15
        baseline_monthly_kwh = baseline_power * 24 * 30 / 1000
        baseline_cost = baseline_monthly_kwh * electricity_rate_per_kwh
        
        projected_savings = baseline_cost - optimized_cost
        
        # Confidence based on training data and model performance
        confidence = min(0.95, len(self.training_data) / 1000.0)
        
        return PowerPrediction(
            current_power=current_power,
            predicted_next_hour=predicted_next_hour,
            predicted_daily_avg=predicted_daily_avg,
            predicted_daily_peak=predicted_daily_peak,
            predicted_monthly=predicted_monthly_kwh,
            estimated_monthly_cost=optimized_cost,
            baseline_monthly_cost=baseline_cost,
            projected_savings=projected_savings,
            confidence=confidence,
            timestamp=now.isoformat()
        )


# ============================================================================
# COMPUTING GRID (Same as before, no changes needed)
# ============================================================================

class ComputingGrid:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.running = False
        self.time_step = 1.0
        self.ambient_temp = 22.0
        self.history: List[Dict] = []
        self.max_history = 1000
        
    def add_node(self, config: NodeConfig) -> Node:
        node_id = str(uuid.uuid4())[:8]
        base_power = config.base_power if config.base_power else config.max_power * 0.3
        
        node = Node(
            id=node_id,
            name=config.name,
            cores=config.cores,
            max_power=config.max_power,
            base_power=base_power,
            load=np.random.uniform(0.1, 0.3),
            temperature=self.ambient_temp + np.random.uniform(0, 10),
            cooling_efficiency=config.cooling_efficiency,
            thermal_mass=config.thermal_mass
        )
        
        self.nodes[node_id] = node
        return node
    
    def remove_node(self, node_id: str) -> bool:
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False
    
    def update_node_load(self, node_id: str, load_delta: float) -> Node:
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        node = self.nodes[node_id]
        node.load = np.clip(node.load + load_delta, 0.0, 1.0)
        return node
    
    def inject_workload(self, injection: WorkloadInjection):
        if injection.target_node_id:
            if injection.target_node_id in self.nodes:
                node = self.nodes[injection.target_node_id]
                node.load = np.clip(node.load + injection.intensity, 0.0, 1.0)
        else:
            for node in self.nodes.values():
                node.load = np.clip(node.load + injection.intensity, 0.0, 1.0)
    
    def simulate_step(self):
        """Physics simulation with power management"""
        for node in self.nodes.values():
            # 1. Natural load variation
            load_variation = np.random.normal(0, 0.01)
            node.load = np.clip(node.load + load_variation, 0.0, 1.0)
            
            # 2. Power calculation with sleep mode
            theoretical_active = (node.max_power - node.base_power) * (node.load ** 1.4)
            theoretical_total = node.base_power + theoretical_active
            
            # Deep sleep if idle
            if node.load < 0.01:
                node.status = "sleep"
                node.power_consumption = 10.0  # Minimal power
                node.fan_speed = 0.0
                node.fan_override = False
                
                # Cool down to ambient
                if node.temperature > self.ambient_temp:
                    node.temperature -= 0.1
            else:
                node.power_consumption = theoretical_total
                
                # 3. Fan control
                if node.fan_override:
                    target_fan_speed = 100.0
                else:
                    if node.temperature < 30:
                        target_fan_speed = 10.0
                    elif node.temperature < 50:
                        target_fan_speed = 10.0 + (node.temperature - 30.0) * 4.5
                    else:
                        target_fan_speed = 100.0
                
                target_fan_speed = np.clip(target_fan_speed, 0.0, 100.0)
                
                # Fan inertia
                if target_fan_speed > node.fan_speed:
                    node.fan_speed += 5.0
                else:
                    node.fan_speed -= 2.0
                node.fan_speed = np.clip(node.fan_speed, 0.0, 100.0)
                
                # 4. Thermodynamics
                thermal_capacity = node.thermal_mass * 500.0
                passive_cooling = node.cooling_efficiency * 10.0
                active_cooling = (node.fan_speed / 100.0) * (node.cooling_efficiency * 150.0)
                
                energy_in = node.power_consumption * self.time_step
                energy_out = (passive_cooling + active_cooling) * (node.temperature - self.ambient_temp) * self.time_step
                
                node.temperature += (energy_in - energy_out) / thermal_capacity
                
                # Status determination
                if node.temperature > 50:
                    node.status = "critical"
                elif node.temperature > 40:
                    node.status = "warning"
                else:
                    node.status = "active"
            
            node.temperature = np.clip(node.temperature, self.ambient_temp, 150.0)
    
    def get_state(self) -> GridState:
        """Get current grid state with optimization metrics"""
        nodes = list(self.nodes.values())
        total_power = sum(n.power_consumption for n in nodes)
        
        # Calculate unoptimized baseline
        unoptimized_power = sum(
            n.base_power + (n.max_power - n.base_power) * (n.load ** 1.4) 
            for n in nodes
        )
        
        avg_load = np.mean([n.load for n in nodes]) if nodes else 0.0
        avg_temp = np.mean([n.temperature for n in nodes]) if nodes else self.ambient_temp
        
        return GridState(
            nodes=nodes,
            total_power=total_power,
            unoptimized_power=unoptimized_power,
            avg_load=avg_load,
            avg_temperature=avg_temp,
            timestamp=datetime.now().isoformat()
        )
    
    def add_to_history(self):
        state = self.get_state()
        self.history.append({
            "timestamp": state.timestamp,
            "total_power": state.total_power,
            "avg_load": state.avg_load,
            "avg_temperature": state.avg_temperature
        })
        
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

grid = ComputingGrid()
optimizer = GridOptimizer(grid)
predictor = PowerPredictor()

# Initialize with default nodes
default_nodes = [
    NodeConfig(name="Server-1", cores=16, max_power=300),
    NodeConfig(name="Server-2", cores=32, max_power=500),
    NodeConfig(name="Server-3", cores=8, max_power=200),
]

for node_config in default_nodes:
    grid.add_node(node_config)


# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {"message": "Enhanced Grid Simulator API", "version": "3.0.0"}

@app.get("/state", response_model=GridState)
def get_state():
    return grid.get_state()

@app.get("/nodes", response_model=List[Node])
def get_nodes():
    return list(grid.nodes.values())

@app.post("/nodes", response_model=Node)
def create_node(config: NodeConfig):
    return grid.add_node(config)

@app.delete("/nodes/{node_id}")
def delete_node(node_id: str):
    if not grid.remove_node(node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    return {"message": "Node deleted", "node_id": node_id}

@app.post("/nodes/{node_id}/load")
def adjust_load(node_id: str, load_delta: float):
    try:
        node = grid.update_node_load(node_id, load_delta)
        return {"message": "Load updated", "node": node}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/workload")
def inject_workload(injection: WorkloadInjection):
    grid.inject_workload(injection)
    return {"message": "Workload injected", "injection": injection}

@app.get("/history")
def get_history(limit: int = 100):
    return grid.history[-limit:]

@app.post("/control/start")
def start_simulation():
    grid.running = True
    return {"message": "Simulation started", "running": grid.running}

@app.post("/control/stop")
def stop_simulation():
    grid.running = False
    return {"message": "Simulation stopped", "running": grid.running}

@app.post("/optimizer/toggle")
def toggle_optimizer(enable: bool):
    optimizer.active = enable
    return {
        "status": "active" if optimizer.active else "inactive",
        "mode": optimizer.mode,
        "total_transfers": optimizer.total_transfers
    }

@app.get("/optimizer/events")
def get_optimizer_events(limit: int = 20):
    return optimizer.history[-limit:]

@app.get("/optimizer/stats")
def get_optimizer_stats():
    """Get optimizer performance statistics"""
    state = grid.get_state()
    power_saved = state.unoptimized_power - state.total_power
    
    return {
        "active": optimizer.active,
        "total_transfers": optimizer.total_transfers,
        "power_saved_watts": power_saved,
        "efficiency_gain_percent": (power_saved / state.unoptimized_power * 100) if state.unoptimized_power > 0 else 0
    }

@app.get("/prediction", response_model=Union[PowerPrediction, Dict])
def get_power_prediction(electricity_rate: float = 6.50):
    """Get ML prediction with savings estimates"""
    state = grid.get_state()
    prediction = predictor.predict(state, electricity_rate)
    
    if not prediction:
        return {
            "message": "Model training",
            "progress": f"{len(predictor.training_data)}/{predictor.min_training_samples}"
        }
    
    return prediction

@app.get("/prediction/status")
def get_prediction_status():
    return {
        "is_trained": predictor.is_trained,
        "samples_collected": len(predictor.training_data),
        "min_samples_needed": predictor.min_training_samples,
        "ready": predictor.is_trained
    }

@app.get("/savings")
def get_savings_metrics(electricity_rate: float = 6.50):
    """Calculate real-time savings metrics"""
    state = grid.get_state()
    
    power_saved_w = max(0, state.unoptimized_power - state.total_power)
    power_saved_kw = power_saved_w / 1000
    
    # CO2 savings (avg 0.92 kg CO2 per kWh in India)
    co2_saved = power_saved_kw * 0.92
    
    return SavingsMetrics(
        total_power_saved=power_saved_w,
        cost_saved_hour=power_saved_kw * electricity_rate,
        cost_saved_day=power_saved_kw * electricity_rate * 24,
        cost_saved_month=power_saved_kw * electricity_rate * 24 * 30,
        efficiency_gain_percent=(power_saved_w / state.unoptimized_power * 100) if state.unoptimized_power > 0 else 0,
        co2_saved_kg=co2_saved
    )

# WebSocket and simulation loop remain the same as before
# ============================================================================
# WEBSOCKET
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        await websocket.send_json(grid.get_state().dict())
        
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)
            
            if command.get("type") == "start":
                grid.running = True
            elif command.get("type") == "stop":
                grid.running = False
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================================
# BACKGROUND SIMULATION LOOP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulation_loop())

async def simulation_loop():
    """Main simulation loop that runs continuously"""
    while True:
        if grid.running:
            # 1. Physics step
            grid.simulate_step()
            grid.add_to_history()
            
            # 2. Optimizer step (runs proactively)
            event = optimizer.run_cycle()
            
            # 3. Collect ML training data
            state = grid.get_state()
            predictor.collect_data_point(state)
            
            # 4. Broadcast state to all connected clients
            state_dict = state.dict()
            
            # Include optimizer event if one occurred
            if event:
                state_dict["optimizer_event"] = event.dict()
            
            await manager.broadcast(state_dict)
        
        await asyncio.sleep(grid.time_step)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 Smart Computing Grid Simulator v3.0")
    print("=" * 60)
    print("Features:")
    print("  ✓ Proactive Load Balancing Optimizer")
    print("  ✓ ML Power Prediction with Peak Detection")
    print("  ✓ Real-time Green Savings Tracking")
    print("  ✓ WebSocket for Live Updates")
    print("=" * 60)
    print("Starting server on http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)