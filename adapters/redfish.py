import numpy as np
from datetime import datetime
from adapters.base import DataSourceAdapter, Node, NodeReading
from adapters.fault_detector import FaultDetector

class RedfishAdapter(DataSourceAdapter):
    """
    Reads hardware sensors using the Redfish REST API.
    """
    
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self.fault_detector = FaultDetector()
    
    async def get_reading(self, node: Node) -> NodeReading:
        try:
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f'https://{self.host}/redfish/v1/Chassis/1/Power',
                    auth=(self.username, self.password),
                    timeout=5.0
                )
                data = response.json()
                power_watts = data.get('PowerControl', [{}])[0].get('PowerConsumedWatts', node.power_consumption)
                
                response_thermal = await client.get(
                    f'https://{self.host}/redfish/v1/Chassis/1/Thermal',
                    auth=(self.username, self.password),
                    timeout=5.0
                )
                thermal_data = response_thermal.json()
                temps = [t.get('ReadingCelsius', 0) for t in thermal_data.get('Temperatures', []) if t.get('ReadingCelsius') is not None]
                temperature = max(temps) if temps else node.temperature
                
                fans = [f.get('Reading', 0) for f in thermal_data.get('Fans', []) if f.get('Reading') is not None]
                fan_pct = np.mean(fans) if fans else 0.0
                
            load_estimate = max(0.0, min(1.0, (power_watts - node.base_power) / max(1.0, (node.max_power - node.base_power))))
            quality, reason = self.fault_detector.check(node.id, temperature, "temperature")
            
            return NodeReading(
                node_id=node.id,
                timestamp=datetime.now(),
                load=load_estimate,
                temperature=temperature,
                power_watts=power_watts,
                fan_speed_pct=fan_pct,
                source="redfish",
                reading_quality=quality,
                fault_reason=reason
            )
            
        except Exception as e:
            return NodeReading(
                node_id=node.id,
                timestamp=datetime.now(),
                load=node.load,
                temperature=node.temperature,
                power_watts=node.power_consumption,
                fan_speed_pct=node.fan_speed,
                source="redfish",
                reading_quality="fault",
                fault_reason=f"connection_error: {str(e)[:80]}"
            )
    
    async def health_check(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(f'https://{self.host}/redfish/v1/', timeout=3.0)
                return resp.status_code == 200
        except:
            return False
