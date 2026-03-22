from abc import ABC, abstractmethod
from pydantic import BaseModel
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict

from main import Node

@dataclass
class NodeReading:
    node_id: str
    timestamp: datetime
    
    # Core metrics (mandatory — every adapter must provide these)
    load: float           # 0.0–1.0 CPU utilization
    temperature: float    # °C (hottest CPU socket or equivalent)
    power_watts: float    # Actual power draw in watts
    fan_speed_pct: float  # 0.0–100.0 normalized fan speed
    
    # Quality metadata (mandatory)
    source: str           # "ipmi" | "snmp" | "redfish" | "prometheus" | "simulated"
    reading_quality: str  # "good" | "degraded" | "fault"
    fault_reason: Optional[str] = None  # e.g. "stuck_sensor", "dropout", "spike"
    
    # Extended metrics (optional — populate when available)
    inlet_temp: Optional[float] = None
    outlet_temp: Optional[float] = None
    psu_efficiency: Optional[float] = None
    voltage_12v: Optional[float] = None


class DataSourceAdapter(ABC):
    """
    All data sources implement this interface.
    The simulation loop only calls get_reading() — it never knows
    whether data came from IPMI, Prometheus, or the physics simulator.
    """
    
    @abstractmethod
    async def get_reading(self, node: Node) -> NodeReading:
        """Fetch one reading for the given node. Never raises — returns fault reading on error."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if the data source is reachable."""
        pass
    
    def get_source_name(self) -> str:
        return self.__class__.__name__.replace("Adapter", "").lower()


class AdapterRegistry:
    """Maps node IDs to their data source adapters."""
    
    def __init__(self):
        self._adapters: Dict[str, DataSourceAdapter] = {}
        
    def register(self, node_id: str, adapter: DataSourceAdapter):
        self._adapters[node_id] = adapter
    
    def get(self, node_id: str) -> Optional[DataSourceAdapter]:
        return self._adapters.get(node_id)
    
    async def health_summary(self) -> Dict[str, bool]:
        results = {}
        seen_adapters = set()
        for node_id, adapter in self._adapters.items():
            adapter_key = id(adapter)
            if adapter_key not in seen_adapters:
                seen_adapters.add(adapter_key)
                results[adapter.get_source_name()] = await adapter.health_check()
        return results
