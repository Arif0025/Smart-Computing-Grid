import yaml
import os
from typing import Tuple

# We'll import everything locally within the function to avoid circular imports during startup
def load_grid_config(path: str = "grid_config.yaml") -> dict:
    with open(path) as f:
        raw = f.read()
    
    # Expand environment variables like ${IPMI_PASSWORD}
    import re
    def expand_env(match):
        var_name = match.group(1)
        value = os.environ.get(var_name, "default_secret") # Provide default for demo purposes
        return value
    
    expanded = re.sub(r'\$\{([^}]+)\}', expand_env, raw)
    return yaml.safe_load(expanded)

def build_grid_from_config(config: dict) -> Tuple[any, any]:
    """
    Reads grid_config.yaml and returns a fully configured grid + adapter registry.
    Simulation nodes and real-hardware nodes coexist in the same grid.
    """
    # Import locally to avoid circular dependencies with main.py
    from main import ComputingGrid, NodeConfig
    from adapters.base import AdapterRegistry
    from adapters.simulated import SimulatedAdapter
    from adapters.ipmi import IPMIAdapter
    from adapters.prometheus import PrometheusAdapter
    from adapters.redfish import RedfishAdapter

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
        
        # We enforce the ID from the config to match what registry expects if needed,
        # but add_node generates a UUID. Setting node.id directly to config ID.
        node.id = node_cfg.get('id', node.id)
        # Update it in the dict
        grid.nodes[node.id] = node
        
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
    
    # Remove the UUID keys that add_node created if we overrode them
    keys_to_delete = [k for k, v in grid.nodes.items() if k != v.id]
    for k in keys_to_delete:
        del grid.nodes[k]
        
    return grid, registry
