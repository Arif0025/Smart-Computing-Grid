import pandas as pd
from datetime import datetime, timedelta
from typing import List
from main import GridState, Node

class DataIngestionLayer:
    def __init__(self, gap_threshold_seconds: int = 300, max_interpolate_seconds: int = 1200):
        self.gap_threshold = gap_threshold_seconds
        self.max_interpolate = max_interpolate_seconds

    def load_from_sqlite(self, db_path: str, grid_id: str) -> List[GridState]:
        import sqlite3
        import os
        if not os.path.exists(db_path):
            return []
            
        conn = sqlite3.connect(db_path)
        
        df_snapshots = pd.read_sql_query(
            "SELECT * FROM grid_snapshots WHERE grid_id=? ORDER BY timestamp ASC",
            conn, params=(grid_id,)
        )
        
        df_nodes = pd.read_sql_query(
            "SELECT * FROM node_readings WHERE grid_id=? ORDER BY timestamp ASC",
            conn, params=(grid_id,)
        )
        conn.close()
        
        if df_snapshots.empty:
            return []
            
        df_snapshots['timestamp'] = pd.to_datetime(df_snapshots['timestamp'])
        df_nodes['timestamp'] = pd.to_datetime(df_nodes['timestamp'])
        
        return self._reconstruct_states(df_snapshots, df_nodes)
        
    def _reconstruct_states(self, df_snapshots: pd.DataFrame, df_nodes: pd.DataFrame) -> List[GridState]:
        states = []
        df_snapshots = df_snapshots.sort_values('timestamp')
        df_nodes = df_nodes.sort_values('timestamp')
        
        df_snapshots.set_index('timestamp', inplace=True)
        time_diffs = df_snapshots.index.to_series().diff().dt.total_seconds()
        
        df_snapshots['is_heavy_gap'] = time_diffs.shift(-1) > self.max_interpolate
        
        for ts, row in df_snapshots.iterrows():
            time_window_start = ts - timedelta(seconds=2)
            time_window_end = ts + timedelta(seconds=2)
            
            nodes_in_window = df_nodes[
                (df_nodes['timestamp'] >= time_window_start) & 
                (df_nodes['timestamp'] <= time_window_end)
            ]
            
            node_objs = []
            for _, n_row in nodes_in_window.iterrows():
                node_objs.append(Node(
                    id=n_row['node_id'],
                    name=n_row['node_id'],
                    cores=1, max_power=100, base_power=10, 
                    load=n_row['load'],
                    temperature=n_row['temperature'],
                    power_consumption=n_row['power_watts'],
                    fan_speed=n_row['fan_speed']
                ))
                
            state = GridState(
                nodes=node_objs,
                total_power=row['total_power'],
                unoptimized_power=row['unoptimized_power'],
                avg_load=row['avg_load'],
                avg_temperature=row['avg_temperature'],
                timestamp=ts.isoformat()
            )
            state.__dict__['is_gap_after'] = row['is_heavy_gap']
            states.append(state)
            
        return states
