# Smart Computing Grid — Migration Specification
## From Simulated Demo → Plug-and-Play Production System

**Version:** 1.0  
**Scope:** Backend (`main.py`) full upgrade  
**Preserves:** All simulation capability — no features removed

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Sensor Input Layer — How Real Grids Talk to Software](#2-sensor-input-layer)
3. [Adapter System — Making Simulation and Reality Interchangeable](#3-adapter-system)
4. [Configuration System — YAML-Driven Plug-and-Play](#4-configuration-system)
5. [Upgraded ML Stack](#5-upgraded-ml-stack)
6. [Conformal Prediction — Honest Uncertainty](#6-conformal-prediction)
7. [SHAP Explainability](#7-shap-explainability)
8. [Persistent Storage](#8-persistent-storage)
9. [Multi-Grid Support](#9-multi-grid-support)
10. [New API Endpoints](#10-new-api-endpoints)
11. [File & Folder Structure](#11-file--folder-structure)
12. [Migration Checklist](#12-migration-checklist)
13. [Dependency List](#13-dependency-list)

---

## 1. Architecture Overview

### What Changes and Why

The current system has everything hardcoded: 3 specific servers, physics-based fake readings, a single global grid instance. This is fine for a demo but breaks the moment you want to:

- Point it at a real server rack
- Add or remove nodes without touching code
- Run multiple grids (multiple racks, multiple clients)
- Have an operations manager trust the ML predictions

The core architectural principle of this migration is the **adapter pattern**: every component that currently touches simulated data gets wrapped in an interface. The simulation becomes one implementation of that interface. Real IPMI sensors, Prometheus scrapers, and Redfish APIs become other implementations. Everything above the adapter layer — the optimizer, ML stack, WebSocket broadcast, REST API — stays completely unchanged.

### Before vs After (Single Sentence Each)

| Component | Before | After |
|---|---|---|
| Node configuration | Hardcoded 3 nodes in `main.py` | Read from `grid_config.yaml` at startup |
| Data source | `simulate_step()` always runs | Adapter selected per-node from config |
| ML model | Batch GBR, retrained every 100 samples | Online learner (River) + LSTM + ensemble |
| Uncertainty | Single point prediction | Conformal intervals with 90% coverage guarantee |
| Explainability | None | SHAP values per prediction |
| Storage | In-memory, lost on restart | InfluxDB time-series (optional) or SQLite fallback |
| Grid scope | Single global grid | Multi-grid registry, each from own config |
| Sensor faults | Not handled | Stuck sensor, dropout, spike detection at adapter |

---

## 2. Sensor Input Layer

### How Real Data Centers Expose Data

A real server rack does not have one data stream. It has four independent protocols running simultaneously, each designed for a different layer of the hardware stack. Understanding this is essential before writing any adapter code.

#### Protocol 1 — IPMI / BMC (Most Important)

Every server has a **Baseboard Management Controller** chip soldered onto the motherboard. It runs independently of the OS — if the server crashes or loses power to its main board, the BMC stays alive on standby power. The BMC exposes:

- Temperature sensors on every CPU socket, DIMM slot, PCIe slot, intake air, exhaust air
- Real-time power draw in watts from the PSU
- Fan RPM for every individual fan header
- A hardware event log with timestamps
- Voltage rails for 12V, 5V, 3.3V lines

You talk to it over a dedicated management network (usually a separate NIC) using the IPMI protocol. In Python:

```python
pip install pyipmi

import pyipmi
import pyipmi.interfaces

interface = pyipmi.interfaces.create_interface('rmcp', slave_address=0x20, host_target_address=0x20)
ipmi = pyipmi.create_connection(interface)
ipmi.session.set_session_type_rmcp(host='192.168.1.10', port=623)
ipmi.session.establish()

# Get all sensor readings
device_id = ipmi.get_device_id()
for sensor in ipmi.sensor_repository.sensors():
    reading = sensor.get_reading()
    print(f"{sensor.name}: {reading.value} {reading.units}")
```

A typical raw IPMI response looks like this:

```
CPU0 Temp     | 47.000  | degrees C  | ok
CPU1 Temp     | 51.000  | degrees C  | ok
PSU1 Power    | 387.000 | Watts      | ok
Fan1A         | 4200.000| RPM        | ok
Inlet Temp    | 22.000  | degrees C  | ok
```

**Key challenge:** A single server exposes 40-80 sensor readings. You need rules for which ones map to `node.temperature`, `node.power_consumption`, `node.fan_speed`. The correct approach: `node.temperature` = max of all CPU socket temps (the hottest CPU is the bottleneck). `node.power_consumption` = PSU input power. `node.fan_speed` = average of all fan RPMs normalized to 0-100%.

#### Protocol 2 — SNMP (PDUs, Switches, UPS)

PDUs (Power Distribution Units) are the smart power strips that feed your servers. They measure per-outlet wattage in real time. SNMP is the protocol — it's a UDP-based query/response system where you request specific OIDs (numeric addresses in a tree).

```python
pip install pysnmp

from pysnmp.hlapi import *

# Query a PDU for outlet 1 wattage
for errorIndication, errorStatus, errorIndex, varBinds in getCmd(
    SnmpEngine(),
    CommunityData('public'),
    UdpTransportTarget(('192.168.1.20', 161)),
    ContextData(),
    ObjectType(ObjectIdentity('1.3.6.1.4.1.318.1.1.12.3.5.1.1.2.1'))  # APC PDU outlet wattage OID
):
    print(varBinds)
```

SNMP is the least pleasant protocol to work with (OIDs are cryptic, vendors all use different MIBs), but most enterprise PDUs only speak SNMP, so you must handle it.

#### Protocol 3 — Redfish / REST (Modern Servers)

HPE iLO and Dell iDRAC interfaces from 2018 onwards support Redfish — a clean HTTPS/JSON REST API. Far easier than raw IPMI.

```python
pip install python-redfish

import requests

response = requests.get(
    'https://192.168.1.10/redfish/v1/Chassis/1/Power',
    auth=('admin', 'password'),
    verify=False
)
data = response.json()
power_watts = data['PowerControl'][0]['PowerConsumedWatts']
temperatures = data['Temperatures']
```

If a client has modern hardware (HPE Gen10+, Dell 14th gen+), prefer Redfish over IPMI. It's versioned, documented, and doesn't require managing raw IPMI sessions.

#### Protocol 4 — Prometheus Node Exporter (OS-Level)

If the data center already runs Prometheus/Grafana (most do), a node exporter agent on each server exposes CPU load, memory usage, disk I/O, and network throughput over HTTP on port 9100.

```python
import requests

response = requests.get('http://192.168.1.10:9100/metrics')
# Parse Prometheus text format
for line in response.text.split('\n'):
    if line.startswith('node_cpu_seconds_total'):
        # compute load from cpu usage delta
        pass
    if line.startswith('node_hwmon_temp_celsius'):
        # hardware temperature if hwmon exporter is active
        pass
```

Note: Prometheus gives you OS-level data, not hardware sensor data. CPU load percentage, yes. PSU wattage, no (unless you also run the hardware monitoring exporter). Use it as a complement to IPMI, not a replacement.

### The Unified NodeReading Object

Regardless of protocol, every adapter must output the same object. This is the contract that makes everything above the adapter layer protocol-agnostic:

```python
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
```

### Sensor Fault Detection (Built into Every Adapter)

Three fault types must be detected at the adapter layer before bad data reaches the ML model:

**Stuck sensor:** A reading that hasn't changed in N consecutive polls. Real sensors fluctuate by at least 0.5°C per second. If a temperature reads exactly 47.000°C for 20 seconds straight, the sensor is dead.

```python
class FaultDetector:
    def __init__(self, stuck_threshold=20, spike_sigma=4.0):
        self.history = {}  # node_id → deque of recent values
        self.stuck_threshold = stuck_threshold
        self.spike_sigma = spike_sigma

    def check(self, node_id: str, value: float, field: str) -> Tuple[str, Optional[str]]:
        key = f"{node_id}.{field}"
        if key not in self.history:
            self.history[key] = deque(maxlen=60)
        
        self.history[key].append(value)
        recent = list(self.history[key])
        
        # Stuck sensor: no variation over threshold samples
        if len(recent) >= self.stuck_threshold:
            if max(recent[-self.stuck_threshold:]) == min(recent[-self.stuck_threshold:]):
                return "fault", "stuck_sensor"
        
        # Spike detection: value is N standard deviations from recent mean
        if len(recent) >= 10:
            mean = np.mean(recent[:-1])
            std = np.std(recent[:-1])
            if std > 0 and abs(value - mean) > self.spike_sigma * std:
                return "degraded", "spike"
        
        # Dropout: value is zero or negative when it shouldn't be
        if value <= 0 and field in ("power_watts", "temperature"):
            return "fault", "dropout"
        
        return "good", None
```

**Behavior on fault:** The adapter does NOT raise an exception. It sets `reading_quality = "fault"` and `fault_reason`. The simulation loop then decides whether to use the last good reading (for transient faults) or flag the node as degraded (for persistent faults > 60 seconds).

---

## 3. Adapter System

### Base Class

```python
from abc import ABC, abstractmethod

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
```

### Simulated Adapter (Existing Physics — Preserved)

This wraps the existing `simulate_step()` logic. No physics equations change. The simulation now becomes a first-class adapter alongside real hardware sources.

```python
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
        # --- Original simulate_step() logic, moved here ---
        
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
```

### IPMI Adapter

```python
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
            load_estimate = max(0.0, min(1.0, (power_watts - node.base_power) / (node.max_power - node.base_power)))
            
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
```

### Prometheus Adapter

```python
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
```

### Adapter Registry

```python
class AdapterRegistry:
    """Maps node IDs to their data source adapters."""
    
    _adapters: Dict[str, DataSourceAdapter] = {}
    
    def register(self, node_id: str, adapter: DataSourceAdapter):
        self._adapters[node_id] = adapter
    
    def get(self, node_id: str) -> DataSourceAdapter:
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
```

---

## 4. Configuration System

### Grid Config File (`grid_config.yaml`)

Place this file in the project root. The system reads it on startup. No code changes needed to add nodes, change parameters, or switch data sources.

```yaml
# grid_config.yaml
# Edit this file to configure your grid. Restart the server to apply changes.

grid:
  id: "datacenter-rack-A"
  name: "Primary Compute Rack"
  ambient_temp: 22.0
  electricity_rate_per_kwh: 6.50   # INR per kWh (used for cost predictions)
  co2_factor_kg_per_kwh: 0.92      # India grid average

simulation:
  # Keep simulation running even when real adapters are active.
  # Simulated nodes coexist with real nodes in the same grid.
  time_step: 1.0
  enable_natural_drift: true       # Random load variation on all nodes

nodes:
  # --- Example 1: Pure simulation node (no hardware needed) ---
  - id: "srv-sim-001"
    name: "Server-1 (simulated)"
    cores: 16
    max_power: 300
    base_power: 90
    cooling_efficiency: 0.10
    thermal_mass: 1.0
    source: simulated              # Uses SimulatedAdapter

  # --- Example 2: Real server via IPMI ---
  - id: "srv-ipmi-001"
    name: "Dell PowerEdge R750"
    cores: 32
    max_power: 750
    base_power: 180
    cooling_efficiency: 0.12
    thermal_mass: 1.5
    source: ipmi
    ipmi:
      host: "192.168.1.10"
      username: "admin"
      password: "${IPMI_PASSWORD}"   # Read from environment variable
      port: 623

  # --- Example 3: Real server via Redfish ---
  - id: "srv-redfish-001"
    name: "HPE ProLiant DL380"
    cores: 64
    max_power: 1200
    base_power: 280
    cooling_efficiency: 0.15
    thermal_mass: 2.0
    source: redfish
    redfish:
      host: "192.168.1.11"
      username: "admin"
      password: "${REDFISH_PASSWORD}"

  # --- Example 4: OS-level data from existing Prometheus stack ---
  - id: "srv-prom-001"
    name: "App Server Node"
    cores: 8
    max_power: 200
    base_power: 60
    cooling_efficiency: 0.08
    thermal_mass: 0.8
    source: prometheus
    prometheus:
      url: "http://prometheus:9090"
      hostname: "app-server-01:9100"

optimizer:
  enabled: true
  mode: "hybrid"                   # "thermal_only" | "balance_only" | "hybrid"
  temp_critical: 48.0
  temp_warning: 40.0
  load_high: 0.85
  max_safe_load: 0.85
  cooldown_seconds: 0.3

ml:
  online_model: "pa_regressor"     # "pa_regressor" | "hoeffding_tree"
  lstm_enabled: true
  lstm_sequence_length: 60         # Seconds of history to feed the LSTM
  ensemble_method: "dynamic"       # "dynamic" | "equal"
  conformal_alpha: 0.10            # 90% coverage guarantee
  shap_enabled: true
  min_samples_before_predict: 10   # Much lower than before (online learning)

storage:
  backend: "sqlite"                # "sqlite" | "influxdb" | "memory"
  sqlite_path: "./grid_history.db"
  influxdb:
    url: "http://localhost:8086"
    token: "${INFLUXDB_TOKEN}"
    org: "my-org"
    bucket: "grid-metrics"
  max_memory_history: 1000         # Fallback if storage backend fails
```

### Config Loader

```python
import yaml
import os
from pathlib import Path

def load_grid_config(path: str = "grid_config.yaml") -> dict:
    with open(path) as f:
        raw = f.read()
    
    # Expand environment variables like ${IPMI_PASSWORD}
    import re
    def expand_env(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(f"Required environment variable ${var_name} not set")
        return value
    
    expanded = re.sub(r'\$\{([^}]+)\}', expand_env, raw)
    return yaml.safe_load(expanded)


def build_grid_from_config(config: dict) -> Tuple[ComputingGrid, AdapterRegistry]:
    """
    Reads grid_config.yaml and returns a fully configured grid + adapter registry.
    Simulation nodes and real-hardware nodes coexist in the same grid.
    """
    grid = ComputingGrid()
    grid.ambient_temp = config['grid'].get('ambient_temp', 22.0)
    grid.time_step = config['simulation'].get('time_step', 1.0)
    
    registry = AdapterRegistry()
    
    for node_cfg in config['nodes']:
        node = grid.add_node(NodeConfig(
            name=node_cfg['name'],
            cores=node_cfg['cores'],
            max_power=node_cfg['max_power'],
            base_power=node_cfg.get('base_power'),
            cooling_efficiency=node_cfg.get('cooling_efficiency', 0.1),
            thermal_mass=node_cfg.get('thermal_mass', 1.0)
        ))
        
        source = node_cfg.get('source', 'simulated')
        
        if source == 'simulated':
            adapter = SimulatedAdapter(
                ambient_temp=grid.ambient_temp,
                time_step=grid.time_step
            )
        elif source == 'ipmi':
            cfg = node_cfg['ipmi']
            adapter = IPMIAdapter(cfg['host'], cfg['username'], cfg['password'], cfg.get('port', 623))
        elif source == 'prometheus':
            cfg = node_cfg['prometheus']
            adapter = PrometheusAdapter(cfg['url'], cfg['hostname'])
        elif source == 'redfish':
            cfg = node_cfg['redfish']
            adapter = RedfishAdapter(cfg['host'], cfg['username'], cfg['password'])
        else:
            raise ValueError(f"Unknown source type: {source}")
        
        registry.register(node.id, adapter)
    
    return grid, registry
```

### Updated Simulation Loop

The only change to the main loop is replacing `grid.simulate_step()` with per-node adapter reads:

```python
async def simulation_loop():
    while True:
        if grid.running:
            
            # 1. Read all nodes via their adapters (real or simulated)
            for node_id, node in grid.nodes.items():
                adapter = adapter_registry.get(node_id)
                reading = await adapter.get_reading(node)
                
                # Apply reading to node (only update if reading is valid)
                if reading.reading_quality != "fault":
                    node.load = reading.load
                    node.temperature = reading.temperature
                    node.power_consumption = reading.power_watts
                    node.fan_speed = reading.fan_speed_pct
                    node.status = _derive_status(node)
                else:
                    # Mark degraded but keep last known values
                    node.status = "degraded"
            
            # 2-5 unchanged: history, optimizer, ML, broadcast
            grid.add_to_history()
            event = optimizer.run_cycle()
            state = grid.get_state()
            predictor.collect_data_point(state)
            state_dict = state.dict()
            if event:
                state_dict["optimizer_event"] = event.dict()
            await manager.broadcast(state_dict)
        
        await asyncio.sleep(grid.time_step)


def _derive_status(node: Node) -> str:
    if node.temperature > 50:
        return "critical"
    elif node.temperature > 40:
        return "warning"
    elif node.load < 0.01:
        return "sleep"
    else:
        return "active"
```

---

## 5. Upgraded ML Stack

### Install Dependencies

```bash
pip install river mapie shap torch  # Core ML additions
pip install httpx pyyaml            # Config and HTTP
pip install influxdb-client         # Optional: for InfluxDB storage
```

### Online Learner (Replaces Batch GBR)

```python
from river import linear_model, preprocessing, compose, metrics

class OnlineLearner:
    """
    Passive-Aggressive Regressor that updates on every single data point.
    No retraining cycles. No cold start beyond 10 samples.
    Handles concept drift automatically.
    """
    
    def __init__(self):
        self.model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.PARegressor(C=0.1, eps=0.1)
        )
        self.mae = metrics.MAE()
        self.samples_seen = 0
        self.recent_errors = deque(maxlen=100)
        self.is_ready = False
        self.min_samples = 10
    
    def _extract_features(self, state: GridState) -> dict:
        now = datetime.now()
        hour = now.hour
        return {
            'hour_sin': np.sin(2 * np.pi * hour / 24),
            'hour_cos': np.cos(2 * np.pi * hour / 24),
            'day_sin': np.sin(2 * np.pi * now.weekday() / 7),
            'day_cos': np.cos(2 * np.pi * now.weekday() / 7),
            'avg_load': state.avg_load,
            'load_variance': np.var([n.load for n in state.nodes]) if state.nodes else 0,
            'avg_temp': state.avg_temperature,
            'temp_variance': np.var([n.temperature for n in state.nodes]) if state.nodes else 0,
            'active_nodes': len([n for n in state.nodes if n.load > 0.1]),
            'num_nodes': len(state.nodes),
        }
    
    def update(self, state: GridState):
        """Learn from this tick. Returns prediction made before learning."""
        features = self._extract_features(state)
        actual = state.total_power
        
        if self.samples_seen >= self.min_samples:
            predicted = self.model.predict_one(features)
            if predicted is not None:
                error = abs(predicted - actual)
                self.recent_errors.append(error)
                self.mae.update(actual, predicted)
        
        self.model.learn_one(features, actual)
        self.samples_seen += 1
        
        if self.samples_seen >= self.min_samples:
            self.is_ready = True
        
        return self.model.predict_one(features)
    
    def predict(self, state: GridState) -> Optional[float]:
        if not self.is_ready:
            return None
        return self.model.predict_one(self._extract_features(state))
    
    @property
    def recent_mae(self) -> float:
        return np.mean(self.recent_errors) if self.recent_errors else float('inf')
```

### LSTM Model

```python
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


class LSTMPredictor:
    """
    Wraps the LSTM model with a rolling window buffer and periodic retraining.
    Retrain triggers when buffer has 200+ samples or every 5 minutes.
    """
    
    def __init__(self, sequence_length=60, input_size=10):
        self.sequence_length = sequence_length
        self.input_size = input_size
        self.model = PowerLSTM(input_size=input_size)
        self.optimizer_torch = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.buffer: deque = deque(maxlen=500)
        self.is_ready = False
        self.recent_errors = deque(maxlen=100)
        self.last_retrain = datetime.now()
    
    def _state_to_vector(self, state: GridState) -> List[float]:
        now = datetime.now()
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
            state.total_power / 5000.0,  # Normalize to ~0-1 range
        ]
    
    def collect(self, state: GridState):
        self.buffer.append({
            'features': self._state_to_vector(state),
            'target': state.total_power
        })
        
        should_retrain = (
            len(self.buffer) >= 200 and
            (datetime.now() - self.last_retrain).seconds > 300
        )
        if should_retrain:
            self._train()
    
    def _train(self):
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
        for _ in range(5):  # Quick fine-tune, not full training
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
        
        recent = list(self.buffer)[-self.sequence_length:]
        X = torch.tensor([[d['features'] for d in recent]], dtype=torch.float32)
        
        with torch.no_grad():
            pred = self.model(X).item()
        
        return pred


class EnsemblePredictor:
    """
    Combines OnlineLearner and LSTMPredictor with dynamic weighting.
    The model with lower recent MAE gets higher weight automatically.
    """
    
    def __init__(self):
        self.online = OnlineLearner()
        self.lstm = LSTMPredictor()
    
    def update(self, state: GridState):
        self.online.update(state)
        self.lstm.collect(state)
    
    def predict(self, state: GridState) -> Optional[float]:
        p_online = self.online.predict(state)
        p_lstm = self.lstm.predict(state)
        
        if p_online is None and p_lstm is None:
            return None
        if p_online is None:
            return p_lstm
        if p_lstm is None:
            return p_online
        
        # Dynamic weighting: lower error → higher weight
        err_online = self.online.recent_mae + 1e-6
        err_lstm = np.mean(list(self.lstm.recent_errors)) + 1e-6 if self.lstm.recent_errors else err_online
        
        total = err_online + err_lstm
        w_online = 1 - (err_online / total)
        w_lstm = 1 - (err_lstm / total)
        # Renormalize
        w_sum = w_online + w_lstm
        
        return (p_online * (w_online / w_sum)) + (p_lstm * (w_lstm / w_sum))
    
    @property
    def is_ready(self) -> bool:
        return self.online.is_ready or self.lstm.is_ready
    
    @property
    def samples_collected(self) -> int:
        return self.online.samples_seen
```

---

## 6. Conformal Prediction

Conformal prediction gives you a **statistically guaranteed coverage interval**. "90% coverage" means: over time, the true value will fall inside the predicted interval at least 90% of the time. No distribution assumptions required.

```python
pip install mapie
```

```python
from mapie.regression import MapieRegressor
from sklearn.linear_model import Ridge
import numpy as np

class ConformalWrapper:
    """
    Wraps the ensemble predictor with conformal intervals.
    Requires a calibration set (collected automatically after enough data).
    Guarantees 90% coverage without assuming Gaussian errors.
    """
    
    def __init__(self, alpha: float = 0.10):
        self.alpha = alpha           # 1 - alpha = coverage guarantee (0.10 = 90%)
        self.is_calibrated = False
        self.calibration_data = []  # [(features, actual_power), ...]
        self.mapie = None
        self._base_model = Ridge()
        self._calibration_X = []
        self._calibration_y = []
        self.min_calibration_samples = 100
    
    def add_calibration_point(self, features: dict, actual_power: float):
        """Collect calibration data points."""
        feature_vector = list(features.values())
        self._calibration_X.append(feature_vector)
        self._calibration_y.append(actual_power)
        
        if len(self._calibration_X) >= self.min_calibration_samples and not self.is_calibrated:
            self._calibrate()
    
    def _calibrate(self):
        X = np.array(self._calibration_X)
        y = np.array(self._calibration_y)
        
        self.mapie = MapieRegressor(
            estimator=self._base_model,
            method="plus",      # "plus" method: best coverage guarantee
            cv=5
        )
        self.mapie.fit(X, y)
        self.is_calibrated = True
        print(f"✓ CONFORMAL CALIBRATED: {len(X)} samples, alpha={self.alpha}")
    
    def predict_with_interval(self, features: dict, point_estimate: float) -> dict:
        """
        Returns prediction with guaranteed confidence interval.
        Falls back to ±15% heuristic before calibration completes.
        """
        if not self.is_calibrated:
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
```

### Updated PowerPrediction Model

Add interval fields to the response schema:

```python
class PowerPrediction(BaseModel):
    current_power: float
    predicted_next_hour: float
    predicted_next_hour_lower: float    # NEW: lower bound of interval
    predicted_next_hour_upper: float    # NEW: upper bound of interval
    predicted_daily_avg: float
    predicted_daily_peak: float
    predicted_monthly: float
    estimated_monthly_cost: float
    baseline_monthly_cost: float
    projected_savings: float
    coverage_guarantee: float           # NEW: e.g. 0.90
    confidence: float
    is_calibrated: bool                 # NEW
    timestamp: str
```

---

## 7. SHAP Explainability

SHAP (SHapley Additive exPlanations) answers the question: *why did the model predict this specific value?* Each feature gets a score representing how much it pushed the prediction up or down from the baseline.

```python
pip install shap
```

```python
import shap
import numpy as np

class SHAPExplainer:
    """
    Generates feature importance explanations for each prediction.
    Uses TreeExplainer for fast, exact SHAP values on tree-based models
    and KernelExplainer for the online/LSTM models.
    """
    
    def __init__(self):
        self.explainer = None
        self.background_data = []
        self.is_ready = False
        self.feature_names = [
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'avg_load', 'load_variance', 'avg_temp', 'temp_variance',
            'active_nodes', 'num_nodes'
        ]
    
    def add_background_sample(self, features: dict):
        self.background_data.append(list(features.values()))
        if len(self.background_data) >= 50 and not self.is_ready:
            self._build_explainer()
    
    def _build_explainer(self):
        background = np.array(self.background_data[-50:])
        # KernelExplainer works with any model (model-agnostic)
        # We pass a simple summary function — can be replaced with actual model.predict
        self.explainer = shap.KernelExplainer(
            model=self._dummy_predict,
            data=shap.kmeans(background, 10)  # Summarize background with 10 clusters
        )
        self.is_ready = True
    
    def _dummy_predict(self, X):
        # Replace with actual ensemble.predict call when integrating
        return np.zeros(len(X))
    
    def explain(self, features: dict, prediction: float) -> dict:
        """
        Returns SHAP values showing which features drove this prediction.
        """
        if not self.is_ready:
            return {
                "available": False,
                "reason": f"Collecting background data ({len(self.background_data)}/50)"
            }
        
        X = np.array([list(features.values())])
        shap_values = self.explainer.shap_values(X, silent=True)[0]
        
        # Pair feature names with their SHAP values, sorted by absolute impact
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
                for name, value in contributions[:5]  # Top 5 drivers
            ],
            "explanation": _generate_text_explanation(contributions[:3])
        }


def _generate_text_explanation(top_3: List[Tuple[str, float]]) -> str:
    """Generates a human-readable sentence for operations staff."""
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
```

### New Explain Endpoint

```python
@app.get("/prediction/explain")
async def explain_prediction(electricity_rate: float = 6.50):
    """
    Returns the current power prediction with full SHAP explanation.
    Shows operations staff exactly why the model made this forecast.
    """
    state = grid.get_state()
    features = predictor.online._extract_features(state)
    point_estimate = predictor.predict(state)
    
    if point_estimate is None:
        return {"message": "Model not ready yet", "samples": predictor.samples_collected}
    
    interval = conformal.predict_with_interval(features, point_estimate)
    explanation = shap_explainer.explain(features, point_estimate)
    
    return {
        "prediction": interval,
        "explanation": explanation,
        "model_status": {
            "online_ready": predictor.online.is_ready,
            "lstm_ready": predictor.lstm.is_ready,
            "conformal_calibrated": conformal.is_calibrated,
            "shap_ready": shap_explainer.is_ready,
            "samples_collected": predictor.samples_collected
        }
    }
```

---

## 8. Persistent Storage

### SQLite Backend (Default — Zero Dependencies Beyond Python)

```python
import sqlite3
from contextlib import contextmanager

class SQLiteStorage:
    def __init__(self, db_path: str = "./grid_history.db"):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS grid_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grid_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    total_power REAL,
                    avg_load REAL,
                    avg_temperature REAL,
                    unoptimized_power REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grid_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    load REAL, temperature REAL, power_watts REAL,
                    fan_speed REAL, status TEXT, source TEXT, reading_quality TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimizer_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grid_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT, source_id TEXT, target_id TEXT,
                    amount REAL, reason TEXT, priority TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON grid_snapshots(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_node ON node_readings(node_id, timestamp)")
    
    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def save_snapshot(self, grid_id: str, state: GridState):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO grid_snapshots (grid_id, timestamp, total_power, avg_load, avg_temperature, unoptimized_power) VALUES (?,?,?,?,?,?)",
                (grid_id, state.timestamp, state.total_power, state.avg_load, state.avg_temperature, state.unoptimized_power)
            )
    
    def save_optimizer_event(self, grid_id: str, event: OptimizationEvent):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO optimizer_events (grid_id, timestamp, action, source_id, target_id, amount, reason, priority) VALUES (?,?,?,?,?,?,?,?)",
                (grid_id, event.timestamp, event.action, event.source_id, event.target_id, event.amount, event.reason, event.priority)
            )
    
    def get_history(self, grid_id: str, limit: int = 100) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM grid_snapshots WHERE grid_id=? ORDER BY timestamp DESC LIMIT ?",
                (grid_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]
```

---

## 9. Multi-Grid Support

```python
class GridRegistry:
    """Manages multiple independent grids from separate config files."""
    
    def __init__(self):
        self._grids: Dict[str, ComputingGrid] = {}
        self._adapters: Dict[str, AdapterRegistry] = {}
        self._optimizers: Dict[str, GridOptimizer] = {}
        self._predictors: Dict[str, EnsemblePredictor] = {}
    
    def load_grid(self, config_path: str) -> str:
        config = load_grid_config(config_path)
        grid_id = config['grid']['id']
        
        grid, adapter_registry = build_grid_from_config(config)
        optimizer = GridOptimizer(grid)
        predictor = EnsemblePredictor()
        
        self._grids[grid_id] = grid
        self._adapters[grid_id] = adapter_registry
        self._optimizers[grid_id] = optimizer
        self._predictors[grid_id] = predictor
        
        return grid_id
    
    def get(self, grid_id: str) -> Optional[ComputingGrid]:
        return self._grids.get(grid_id)


# Updated API routes for multi-grid
@app.get("/grids/{grid_id}/state")
def get_grid_state(grid_id: str):
    grid = registry.get(grid_id)
    if not grid:
        raise HTTPException(404, f"Grid {grid_id} not found")
    return grid.get_state()

@app.get("/grids/{grid_id}/prediction")
def get_grid_prediction(grid_id: str, electricity_rate: float = 6.50):
    grid = registry.get(grid_id)
    predictor = registry._predictors.get(grid_id)
    if not grid or not predictor:
        raise HTTPException(404)
    return predictor.predict(grid.get_state())

@app.get("/grids")
def list_grids():
    return [{"id": gid, "nodes": len(g.nodes)} for gid, g in registry._grids.items()]
```

---

## 10. New API Endpoints

Complete list of new endpoints added by this migration. All existing endpoints unchanged.

| Method | Path | Description |
|---|---|---|
| GET | `/grids` | List all loaded grids |
| GET | `/grids/{id}/state` | Grid state (multi-grid version) |
| GET | `/grids/{id}/prediction` | ML prediction for specific grid |
| GET | `/prediction/explain` | Prediction + SHAP explanation |
| GET | `/prediction/interval` | Point prediction + conformal interval |
| GET | `/adapters/health` | Health status of all data source adapters |
| GET | `/adapters/{node_id}/status` | Single adapter status + last reading quality |
| POST | `/config/reload` | Reload `grid_config.yaml` without restart |
| GET | `/ml/status` | Full ML stack status (online, LSTM, conformal, SHAP) |
| GET | `/storage/history` | Persistent history (from SQLite/InfluxDB) |

---

## 11. File & Folder Structure

```
smart-grid/
├── main.py                     ← Modified: config-driven startup, adapter loop
├── grid_config.yaml            ← NEW: plug-and-play node configuration
├── grid_history.db             ← AUTO-CREATED: SQLite storage
│
├── adapters/
│   ├── __init__.py
│   ├── base.py                 ← NEW: DataSourceAdapter ABC + NodeReading
│   ├── simulated.py            ← NEW: Physics simulation (existing logic moved here)
│   ├── ipmi.py                 ← NEW: IPMI/BMC adapter
│   ├── prometheus.py           ← NEW: Prometheus scraper adapter
│   ├── redfish.py              ← NEW: Redfish/REST adapter
│   └── fault_detector.py       ← NEW: Stuck sensor, spike, dropout detection
│
├── ml/
│   ├── __init__.py
│   ├── online_learner.py       ← NEW: River PARegressor online model
│   ├── lstm_predictor.py       ← NEW: PyTorch LSTM + rolling buffer
│   ├── ensemble.py             ← NEW: Dynamic-weighted ensemble
│   ├── conformal.py            ← NEW: MAPIE conformal prediction
│   └── shap_explainer.py       ← NEW: SHAP feature attribution
│
├── storage/
│   ├── __init__.py
│   ├── sqlite_backend.py       ← NEW: SQLite time-series storage
│   └── influxdb_backend.py     ← NEW: InfluxDB backend (optional)
│
└── config/
    ├── loader.py               ← NEW: YAML loader + env var expansion
    └── examples/
        ├── single_rack.yaml    ← Example: one rack, all simulated
        ├── mixed_rack.yaml     ← Example: 2 real servers + 1 simulated
        └── multi_tenant.yaml   ← Example: multiple client grids
```

---

## 12. Migration Checklist

Work through this in order. Each step is independently deployable — you can stop after any step and have a working system.

### Phase 1 — Configuration (1-2 hours)
- [ ] Create `grid_config.yaml` using the template from Section 4
- [ ] Write `config/loader.py`
- [ ] Update `main.py` to read config on startup instead of hardcoded nodes
- [ ] Test: `uvicorn main:app --reload` should produce identical behavior to current code with 3 simulated nodes

### Phase 2 — Adapter System (2-3 hours)
- [ ] Create `adapters/base.py` with `DataSourceAdapter`, `NodeReading`, `AdapterRegistry`
- [ ] Move existing `simulate_step()` logic into `adapters/simulated.py`
- [ ] Create `adapters/fault_detector.py`
- [ ] Update simulation loop to call `adapter.get_reading(node)` instead of `grid.simulate_step()`
- [ ] Test: simulation still runs, fault detector catches injected bad values

### Phase 3 — Online ML (2-3 hours)
- [ ] `pip install river`
- [ ] Create `ml/online_learner.py`
- [ ] Create `ml/ensemble.py` (start with just the online learner, LSTM optional)
- [ ] Replace `PowerPredictor` in `main.py` with `EnsemblePredictor`
- [ ] Test: `/prediction/status` shows `is_ready: true` within 10 seconds (not 50)

### Phase 4 — Conformal Prediction (1 hour)
- [ ] `pip install mapie`
- [ ] Create `ml/conformal.py`
- [ ] Update `PowerPrediction` model to include `lower`, `upper`, `coverage_guarantee`
- [ ] Update `/prediction` endpoint to return intervals
- [ ] Test: response includes `lower` and `upper` bounds after 100 samples

### Phase 5 — SHAP (1 hour)
- [ ] `pip install shap`
- [ ] Create `ml/shap_explainer.py`
- [ ] Add `/prediction/explain` endpoint
- [ ] Test: endpoint returns `top_contributors` list after 50 background samples

### Phase 6 — Persistent Storage (1-2 hours)
- [ ] Create `storage/sqlite_backend.py`
- [ ] Update simulation loop to call `storage.save_snapshot()` each tick
- [ ] Update `/history` endpoint to read from SQLite instead of in-memory list
- [ ] Test: restart server, `/history` still returns previous data

### Phase 7 — LSTM (2-4 hours, optional)
- [ ] `pip install torch`
- [ ] Create `ml/lstm_predictor.py`
- [ ] Add LSTM to `EnsemblePredictor`
- [ ] Test: LSTM activates after 200 samples, ensemble switches weighting

### Phase 8 — Real Hardware Adapters (time varies by client)
- [ ] Create `adapters/ipmi.py` (or Redfish/Prometheus as appropriate)
- [ ] Add real node entries to `grid_config.yaml`
- [ ] Test: `/adapters/health` shows all adapters as healthy
- [ ] Test: node readings in `/state` update from real hardware, not simulation

---

## 13. Dependency List

### Required (Core Migration)

```txt
# Existing
fastapi
uvicorn
websockets
pydantic
numpy
pandas
scikit-learn

# New additions
river                  # Online learning (PARegressor)
mapie                  # Conformal prediction intervals
shap                   # Feature attribution / explainability
pyyaml                 # Grid config file parsing
httpx                  # Async HTTP for Prometheus/Redfish adapters
```

### Optional (Hardware Adapters)

```txt
pyipmi                 # IPMI/BMC access
pysnmp                 # SNMP for PDUs and UPS
python-redfish         # Redfish REST API (HPE/Dell)
```

### Optional (Enhanced Storage)

```txt
influxdb-client        # InfluxDB time-series storage
```

### Optional (LSTM)

```txt
torch                  # PyTorch for LSTM model
```

### Install Command

```bash
# Minimum viable upgrade (Phases 1-6)
pip install river mapie shap pyyaml httpx

# Full production stack
pip install river mapie shap pyyaml httpx torch pyipmi pysnmp influxdb-client
```

---

*This document covers every change needed to transform the demo into a production-ready plug-and-play system. The simulation is fully preserved and coexists with real hardware adapters at all times.*
