import numpy as np
from datetime import datetime
from adapters.base import DataSourceAdapter, Node, NodeReading
from adapters.fault_detector import FaultDetector
from typing import Optional

class PrometheusAdapter(DataSourceAdapter):
    """
    Reads from an existing Prometheus/node_exporter stack.
    No new hardware access required — works if Prometheus is already deployed.
    """
    
    def __init__(self, prometheus_url: str, node_hostname: str):
        self.prometheus_url = prometheus_url.rstrip('/')
        self.node_hostname = node_hostname
        self.fault_detector = FaultDetector()
    
    async def _query(self, promql: str) -> Optional[float]:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": promql},
                timeout=5.0
            )
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if results:
                return float(results[0]["value"][1])
        return None
    
    async def get_reading(self, node: Node) -> NodeReading:
        try:
            h = self.node_hostname
            
            # CPU load: 1 - idle percentage
            idle = await self._query(
                f'avg(rate(node_cpu_seconds_total{{instance="{h}",mode="idle"}}[30s]))'
            )
            load = 1.0 - (idle or 0.0)
            
            # Temperature via hwmon (requires node_hwmon collector)
            temp = await self._query(
                f'max(node_hwmon_temp_celsius{{instance="{h}"}})'
            )
            temperature = temp or node.temperature
            
            quality, reason = self.fault_detector.check(node.id, temperature, "temperature")
            
            # Power: estimate from load if no direct sensor
            power = node.base_power + (node.max_power - node.base_power) * (load ** 1.4)
            
            return NodeReading(
                node_id=node.id,
                timestamp=datetime.now(),
                load=np.clip(load, 0.0, 1.0),
                temperature=temperature,
                power_watts=power,
                fan_speed_pct=node.fan_speed,  # Not available via Prometheus
                source="prometheus",
                reading_quality=quality,
                fault_reason=reason
            )
        
        except Exception as e:
            return NodeReading(
                node_id=node.id, timestamp=datetime.now(),
                load=node.load, temperature=node.temperature,
                power_watts=node.power_consumption, fan_speed_pct=node.fan_speed,
                source="prometheus", reading_quality="fault",
                fault_reason=f"query_error: {str(e)[:80]}"
            )
    
    async def health_check(self) -> bool:
        try:
            result = await self._query("up")
            return result is not None
        except:
            return False
