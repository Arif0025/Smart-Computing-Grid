import numpy as np
from datetime import datetime
from adapters.base import DataSourceAdapter, Node, NodeReading
from adapters.fault_detector import FaultDetector

class SimulatedAdapter(DataSourceAdapter):
    """
    Wraps the existing physics simulation.
    Used for: development, testing, demos, nodes without real hardware access.
    All original thermodynamics, fan inertia, and load variation preserved.
    """
    
    def __init__(self, ambient_temp: float = 22.0, time_step: float = 1.0):
        self.ambient_temp = ambient_temp
        self.time_step = time_step
        self.fault_detector = FaultDetector()
    
    async def get_reading(self, node: Node) -> NodeReading:
        load_variation = np.random.normal(0, 0.01)
        new_load = np.clip(node.load + load_variation, 0.0, 1.0)
        
        if new_load < 0.01:
            power = 10.0
            fan_pct = 0.0
            temp_delta = -0.1 if node.temperature > self.ambient_temp else 0
            new_temp = node.temperature + temp_delta
        else:
            theoretical_active = (node.max_power - node.base_power) * (new_load ** 1.4)
            power = node.base_power + theoretical_active
            
            if node.fan_override:
                target_fan = 100.0
            elif node.temperature < 30:
                target_fan = 10.0
            elif node.temperature < 50:
                target_fan = 10.0 + (node.temperature - 30.0) * 4.5
            else:
                target_fan = 100.0
            
            # Fan inertia
            if target_fan > node.fan_speed:
                new_fan = min(node.fan_speed + 5.0, target_fan)
            else:
                new_fan = max(node.fan_speed - 2.0, target_fan)
            fan_pct = np.clip(new_fan, 0.0, 100.0)
            
            thermal_capacity = node.thermal_mass * 500.0
            passive_cooling = node.cooling_efficiency * 10.0
            active_cooling = (fan_pct / 100.0) * (node.cooling_efficiency * 150.0)
            energy_in = power * self.time_step
            energy_out = (passive_cooling + active_cooling) * (node.temperature - self.ambient_temp) * self.time_step
            new_temp = node.temperature + (energy_in - energy_out) / thermal_capacity
            new_temp = np.clip(new_temp, self.ambient_temp, 150.0)
        
        return NodeReading(
            node_id=node.id,
            timestamp=datetime.now(),
            load=new_load,
            temperature=new_temp,
            power_watts=power,
            fan_speed_pct=fan_pct,
            source="simulated",
            reading_quality="good"
        )
    
    async def health_check(self) -> bool:
        return True  # Simulation never goes down
