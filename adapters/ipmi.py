import numpy as np
from datetime import datetime
from adapters.base import DataSourceAdapter, Node, NodeReading
from adapters.fault_detector import FaultDetector

class IPMIAdapter(DataSourceAdapter):
    """
    Reads real hardware sensors via IPMI/BMC.
    Requires network access to the server's management interface.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 623):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.fault_detector = FaultDetector()
        self._connection = None
    
    async def _ensure_connected(self):
        if self._connection is None:
            import pyipmi
            import pyipmi.interfaces
            interface = pyipmi.interfaces.create_interface(
                'rmcp', slave_address=0x20, host_target_address=0x20
            )
            self._connection = pyipmi.create_connection(interface)
            self._connection.session.set_session_type_rmcp(self.host, port=self.port)
            self._connection.session.set_auth_type_user(self.username, self.password)
            self._connection.session.establish()
    
    async def get_reading(self, node: Node) -> NodeReading:
        try:
            await self._ensure_connected()
            
            cpu_temps, fan_rpms, psu_power = [], [], []
            
            for sensor in self._connection.sensor_repository.sensors():
                reading = sensor.get_reading()
                if reading is None or reading.value is None:
                    continue
                name_lower = sensor.name.lower()
                
                if 'cpu' in name_lower and 'temp' in name_lower:
                    cpu_temps.append(reading.value)
                elif 'fan' in name_lower and reading.units == 'RPM':
                    fan_rpms.append(reading.value)
                elif 'psu' in name_lower and 'power' in name_lower:
                    psu_power.append(reading.value)
            
            temperature = max(cpu_temps) if cpu_temps else node.temperature
            power_watts = sum(psu_power) if psu_power else node.power_consumption
            
            # Normalize fan RPM to 0-100% (typical max RPM is 6000)
            max_rpm = 6000.0
            fan_pct = (np.mean(fan_rpms) / max_rpm * 100) if fan_rpms else 0.0
            fan_pct = np.clip(fan_pct, 0.0, 100.0)
            
            # Load from CPU utilization via OS (IPMI doesn't expose this directly)
            # Fallback: estimate from power draw
            load_estimate = max(0.0, min(1.0, (power_watts - node.base_power) / (max(1.0, node.max_power - node.base_power))))
            
            quality, reason = self.fault_detector.check(node.id, temperature, "temperature")
            
            return NodeReading(
                node_id=node.id,
                timestamp=datetime.now(),
                load=load_estimate,
                temperature=temperature,
                power_watts=power_watts,
                fan_speed_pct=fan_pct,
                source="ipmi",
                reading_quality=quality,
                fault_reason=reason
            )
        
        except Exception as e:
            self._connection = None  # Reset on error so next call reconnects
            return NodeReading(
                node_id=node.id,
                timestamp=datetime.now(),
                load=node.load,
                temperature=node.temperature,
                power_watts=node.power_consumption,
                fan_speed_pct=node.fan_speed,
                source="ipmi",
                reading_quality="fault",
                fault_reason=f"connection_error: {str(e)[:80]}"
            )
    
    async def health_check(self) -> bool:
        try:
            await self._ensure_connected()
            return True
        except:
            return False
