// Complete Enhanced Frontend with:
// - Proactive optimizer
// - Prominent green savings card
// - Collapsible detailed logs
// - Improved predictions
// - Rupee currency (₹)

import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Pause, Plus, Trash2, Zap, Cpu, 
  Thermometer, Activity, AlertTriangle, TrendingUp, Fan,
  IndianRupee, Calendar, Clock, ChevronDown, ChevronUp, Leaf, Target
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer, AreaChart, Area, BarChart, Bar
} from 'recharts';

const API_BASE = '/api';
const WS_URL = 'ws://localhost:8000/ws';

// ============================================================================
// SMOOTH FAN COMPONENT
// ============================================================================
const SmoothFan = ({ speed, isOverride }) => {
  const iconRef = useRef(null);
  const rotation = useRef(0);
  
  useEffect(() => {
    let animationFrame;
    const animate = () => {
      const rotationSpeed = (Math.max(speed, 0) / 100) * 25;
      if (rotationSpeed > 0) {
        rotation.current = (rotation.current + rotationSpeed) % 360;
        if (iconRef.current) {
          iconRef.current.style.transform = `rotate(${rotation.current}deg)`;
        }
      }
      animationFrame = requestAnimationFrame(animate);
    };
    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [speed]);

  return (
    <Fan 
      ref={iconRef} 
      size={18} 
      className={`transition-colors ${isOverride ? 'text-red-400' : 'text-cyan-400'}`} 
    />
  );
};

// ============================================================================
// GREEN SAVINGS CARD - PROMINENT VERSION
// ============================================================================
const GreenSavingsCard = ({ savings, isOptimizing }) => {
  if (!savings) return null;

  return (
    <div className="col-span-1 md:col-span-2 lg:col-span-2 bg-gradient-to-br from-emerald-900/50 via-green-900/30 to-emerald-800/40 backdrop-blur rounded-xl p-6 border-2 border-emerald-500/40 shadow-2xl shadow-emerald-900/50 relative overflow-hidden">
      
      {/* Background Decoration */}
      <div className="absolute -right-8 -top-8 w-40 h-40 bg-emerald-500/10 rounded-full blur-3xl"></div>
      <div className="absolute -left-8 -bottom-8 w-40 h-40 bg-green-500/10 rounded-full blur-3xl"></div>
      
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-emerald-500/20 rounded-xl ring-2 ring-emerald-400/30">
              <Leaf className="text-emerald-300" size={28} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                Green Power Savings
                {isOptimizing && (
                  <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-300 rounded-full border border-emerald-400/30 animate-pulse">
                    ACTIVE
                  </span>
                )}
              </h3>
              <p className="text-xs text-emerald-300/60">Real-time efficiency impact</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-emerald-300">
              {savings.efficiency_gain_percent.toFixed(1)}%
            </div>
            <div className="text-xs text-emerald-400/60">More Efficient</div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-4 mb-4">
          {/* Power Saved */}
          <div className="bg-gray-900/40 rounded-lg p-3 border border-emerald-500/20">
            <div className="text-xs text-gray-400 mb-1">Power Saved</div>
            <div className="text-xl font-bold text-white">
              {savings.total_power_saved.toFixed(0)}W
            </div>
            <div className="text-[10px] text-emerald-400/70 font-mono">
              {(savings.total_power_saved / 1000).toFixed(2)} kW
            </div>
          </div>

          {/* Hourly Savings */}
          <div className="bg-gray-900/40 rounded-lg p-3 border border-emerald-500/20">
            <div className="text-xs text-gray-400 mb-1">Per Hour</div>
            <div className="text-xl font-bold text-emerald-300">
              ₹{savings.cost_saved_hour.toFixed(2)}
            </div>
            <div className="text-[10px] text-gray-500">Cost avoided</div>
          </div>

          {/* Daily Savings */}
          <div className="bg-gray-900/40 rounded-lg p-3 border border-emerald-500/20">
            <div className="text-xs text-gray-400 mb-1">Per Day</div>
            <div className="text-xl font-bold text-emerald-300">
              ₹{savings.cost_saved_day.toFixed(2)}
            </div>
            <div className="text-[10px] text-gray-500">Est. daily</div>
          </div>

          {/* Monthly Savings */}
          <div className="bg-gray-900/40 rounded-lg p-3 border border-green-500/30 ring-1 ring-green-400/20">
            <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
              <IndianRupee size={10} />
              <span>Per Month</span>
            </div>
            <div className="text-xl font-bold text-green-300">
              ₹{savings.cost_saved_month.toFixed(2)}
            </div>
            <div className="text-[10px] text-green-400/70">Projected</div>
          </div>
        </div>

        {/* Environmental Impact */}
        <div className="bg-gray-900/30 rounded-lg p-3 border border-emerald-500/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Leaf className="text-emerald-400" size={16} />
            <span className="text-sm text-gray-300">Carbon Footprint Reduced</span>
          </div>
          <div className="text-right">
            <span className="text-lg font-bold text-emerald-300">{savings.co2_saved_kg.toFixed(2)} kg</span>
            <span className="text-xs text-gray-500 ml-1">CO₂/hour</span>
          </div>
        </div>

        {/* Visual Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-[10px] text-gray-500 mb-1">
            <span>Energy Distribution</span>
            <span>{savings.efficiency_gain_percent.toFixed(1)}% saved</span>
          </div>
          <div className="bg-gray-700/50 h-3 rounded-full overflow-hidden flex shadow-inner">
            {/* Used portion */}
            <div 
              className="bg-gradient-to-r from-gray-500 to-gray-600 h-full transition-all duration-1000"
              style={{ width: `${100 - savings.efficiency_gain_percent}%` }}
            />
            {/* Saved portion */}
            <div 
              className="bg-gradient-to-r from-emerald-500 to-green-400 h-full transition-all duration-1000 animate-pulse shadow-lg shadow-emerald-500/50"
              style={{ width: `${savings.efficiency_gain_percent}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-500 mt-1">
            <span>⚡ Active Power</span>
            <span>💚 Saved by AI</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PREDICTION COMPARISON CARD
// ============================================================================
const PredictionComparisonCard = ({ prediction, current, isOptimizing }) => {
  if (!prediction) return null;

  const accuracy = current > 0 ? (1 - Math.abs(prediction.predicted_next_hour - current) / current) * 100 : 0;

  return (
    <div className="bg-gradient-to-br from-purple-900/30 to-indigo-900/20 backdrop-blur rounded-xl p-5 border border-purple-500/30 shadow-xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-purple-500/20 rounded-lg">
          <Target className="text-purple-400" size={20} />
        </div>
        <div>
          <h3 className="text-lg font-bold">Power Forecast vs Actual</h3>
          <p className="text-xs text-gray-400">ML prediction accuracy</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {/* Current Power */}
        <div className="bg-gray-800/50 rounded-lg p-3 border border-blue-500/30">
          <div className="text-xs text-gray-400 mb-1">Current</div>
          <div className="text-2xl font-bold text-blue-400">{current.toFixed(0)}W</div>
          <div className="text-[10px] text-gray-500">Actual now</div>
        </div>

        {/* Predicted */}
        <div className="bg-gray-800/50 rounded-lg p-3 border border-purple-500/30">
          <div className="text-xs text-gray-400 mb-1">Predicted</div>
          <div className="text-2xl font-bold text-purple-400">
            {prediction.predicted_next_hour.toFixed(0)}W
          </div>
          <div className="text-[10px] text-gray-500">Next hour</div>
        </div>

        {/* Accuracy */}
        <div className="bg-gray-800/50 rounded-lg p-3 border border-green-500/30">
          <div className="text-xs text-gray-400 mb-1">Accuracy</div>
          <div className="text-2xl font-bold text-green-400">{accuracy.toFixed(1)}%</div>
          <div className="text-[10px] text-gray-500">Model confidence</div>
        </div>
      </div>

      {/* Daily Peak Prediction */}
      <div className="bg-gray-900/40 rounded-lg p-3 border border-orange-500/20">
        <div className="flex justify-between items-center">
          <div>
            <div className="text-xs text-gray-400 mb-1">Expected Daily Peak</div>
            <div className="text-xl font-bold text-orange-400">
              {prediction.predicted_daily_peak.toFixed(0)}W
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400 mb-1">Average Load</div>
            <div className="text-xl font-bold text-gray-300">
              {prediction.predicted_daily_avg.toFixed(0)}W
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN APP
// ============================================================================
function App() {
  // State
  const [nodes, setNodes] = useState([]);
  const [gridStats, setGridStats] = useState({
    total_power: 0,
    unoptimized_power: 0,
    avg_load: 0,
    avg_temperature: 0
  });
  const [history, setHistory] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showAddNode, setShowAddNode] = useState(false);
  const [autoOptimize, setAutoOptimize] = useState(false);
  const [optEvents, setOptEvents] = useState([]);
  const [showOptLogs, setShowOptLogs] = useState(true);
  const [prediction, setPrediction] = useState(null);
  const [predictionStatus, setPredictionStatus] = useState(null);
  const [savings, setSavings] = useState(null);
  const [electricityRate, setElectricityRate] = useState(6.50); // ₹ per kWh
  
  const ws = useRef(null);
  
  const [newNode, setNewNode] = useState({
    name: '',
    cores: 16,
    max_power: 300
  });

  // ============================================================================
  // WEBSOCKET & DATA FETCHING
  // ============================================================================
  
  useEffect(() => {
    connectWebSocket();
    fetchInitialData();
    fetchPredictionStatus();
    fetchSavings();
    
    // Poll for predictions and savings
    const interval = setInterval(() => {
      fetchPrediction();
      fetchPredictionStatus();
      fetchSavings();
    }, 10000);
    
    return () => {
      if (ws.current) ws.current.close();
      clearInterval(interval);
    };
  }, [electricityRate]);

  const connectWebSocket = () => {
    ws.current = new WebSocket(WS_URL);
    
    ws.current.onopen = () => console.log('✓ WebSocket connected');
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      setNodes(data.nodes || []);
      setGridStats({
        total_power: data.total_power || 0,
        unoptimized_power: data.unoptimized_power || 0,
        avg_load: data.avg_load || 0,
        avg_temperature: data.avg_temperature || 0
      });
      
      if (data.optimizer_event) {
        setOptEvents(prev => [data.optimizer_event, ...prev].slice(0, 20));
      }
      
      setHistory(prev => {
        const newPoint = {
          time: new Date(data.timestamp).getTime(),
          power: data.total_power,
          load: data.avg_load * 100,
          temp: data.avg_temperature
        };
        return [...prev.slice(-49), newPoint];
      });
    };
    
    ws.current.onerror = (error) => console.error('WebSocket error:', error);
    ws.current.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      setTimeout(connectWebSocket, 3000);
    };
  };

  const fetchInitialData = async () => {
    try {
      const response = await fetch(`${API_BASE}/state`);
      const data = await response.json();
      setNodes(data.nodes || []);
      setGridStats({
        total_power: data.total_power || 0,
        unoptimized_power: data.unoptimized_power || 0,
        avg_load: data.avg_load || 0,
        avg_temperature: data.avg_temperature || 0
      });
    } catch (error) {
      console.error('Failed to fetch initial data:', error);
    }
  };

  const fetchPrediction = async () => {
    try {
      const response = await fetch(`${API_BASE}/prediction?electricity_rate=${electricityRate}`);
      const data = await response.json();
      if (data && !data.message) {
        setPrediction(data);
      }
    } catch (error) {
      console.error('Failed to fetch prediction:', error);
    }
  };

  const fetchPredictionStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/prediction/status`);
      const data = await response.json();
      setPredictionStatus(data);
    } catch (error) {
      console.error('Failed to fetch prediction status:', error);
    }
  };

  const fetchSavings = async () => {
    try {
      const response = await fetch(`${API_BASE}/savings?electricity_rate=${electricityRate}`);
      const data = await response.json();
      setSavings(data);
    } catch (error) {
      console.error('Failed to fetch savings:', error);
    }
  };

  // ============================================================================
  // CONTROL FUNCTIONS
  // ============================================================================

  const toggleSimulation = async () => {
    const endpoint = isRunning ? 'stop' : 'start';
    try {
      await fetch(`${API_BASE}/control/${endpoint}`, { method: 'POST' });
      setIsRunning(!isRunning);
      
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: endpoint }));
      }
    } catch (error) {
      console.error('Failed to toggle simulation:', error);
    }
  };

  const toggleOptimizer = async () => {
    try {
      await fetch(`${API_BASE}/optimizer/toggle?enable=${!autoOptimize}`, { 
        method: 'POST' 
      });
      setAutoOptimize(!autoOptimize);
    } catch (error) {
      console.error('Failed to toggle optimizer:', error);
    }
  };

  const addNode = async () => {
    if (!newNode.name) {
      alert('Please enter a node name');
      return;
    }

    try {
      await fetch(`${API_BASE}/nodes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newNode)
      });
      
      setNewNode({ name: '', cores: 16, max_power: 300 });
      setShowAddNode(false);
      fetchInitialData();
    } catch (error) {
      console.error('Failed to add node:', error);
    }
  };

  const deleteNode = async (nodeId) => {
    try {
      await fetch(`${API_BASE}/nodes/${nodeId}`, { method: 'DELETE' });
      fetchInitialData();
      if (selectedNode?.id === nodeId) {
        setSelectedNode(null);
      }
    } catch (error) {
      console.error('Failed to delete node:', error);
    }
  };

  const adjustNodeLoad = async (nodeId, delta) => {
    try {
      await fetch(`${API_BASE}/nodes/${nodeId}/load?load_delta=${delta}`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Failed to adjust load:', error);
    }
  };

  const injectWorkload = async (intensity) => {
    try {
      await fetch(`${API_BASE}/workload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intensity })
      });
    } catch (error) {
      console.error('Failed to inject workload:', error);
    }
  };

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  const getStatusColor = (status) => {
    const colors = {
      sleep: 'bg-purple-600',
      idle: 'bg-blue-500',
      active: 'bg-emerald-500',
      warning: 'bg-orange-500',
      critical: 'bg-red-600',
      offline: 'bg-gray-600'
    };
    return colors[status] || 'bg-gray-500';
  };
  
  const getStatusBadgeColor = (status) => {
    const colors = {
      sleep: 'bg-purple-500/10 text-purple-400 border border-purple-500/20',
      idle: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
      active: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
      warning: 'bg-orange-500/10 text-orange-400 border border-orange-500/20',
      critical: 'bg-red-500/10 text-red-400 border border-red-500/20',
      offline: 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      critical: 'text-red-400 bg-red-500/10 border-red-500/30',
      high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
      medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
      low: 'text-blue-400 bg-blue-500/10 border-blue-500/30'
    };
    return colors[priority] || 'text-gray-400 bg-gray-500/10 border-gray-500/30';
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Smart Computing Grid
            </h1>
            <p className="text-gray-400">
              Real-time monitoring • {nodes.length} nodes • {autoOptimize ? '🟢 AI Optimizing' : '⚪ Manual Mode'}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={toggleSimulation}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all shadow-lg ${
                isRunning 
                  ? 'bg-red-600 hover:bg-red-700 shadow-red-500/50' 
                  : 'bg-green-600 hover:bg-green-700 shadow-green-500/50'
              }`}
            >
              {isRunning ? <><Pause size={20} />Stop</> : <><Play size={20} />Start</>}
            </button>
            <button
              onClick={toggleOptimizer}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all shadow-lg ${
                autoOptimize 
                  ? 'bg-purple-600 hover:bg-purple-700 shadow-purple-500/50' 
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              <Cpu size={20} />
              {autoOptimize ? 'AI ON' : 'AI OFF'}
            </button>
            <button
              onClick={() => setShowAddNode(!showAddNode)}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-all shadow-lg shadow-blue-500/50"
            >
              <Plus size={20} />
              Add Node
            </button>
          </div>
        </div>

        {/* ADD NODE FORM */}
        {showAddNode && (
          <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 mb-6 border border-gray-700 shadow-xl">
            <h3 className="text-xl font-bold mb-4">Configure New Compute Node</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Node Name</label>
                <input
                  type="text"
                  value={newNode.name}
                  onChange={(e) => setNewNode({...newNode, name: e.target.value})}
                  placeholder="Server-4"
                  className="w-full px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">CPU Cores</label>
                <input
                  type="number"
                  value={newNode.cores}
                  onChange={(e) => setNewNode({...newNode, cores: parseInt(e.target.value)})}
                  className="w-full px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Max Power (W)</label>
                <input
                  type="number"
                  value={newNode.max_power}
                  onChange={(e) => setNewNode({...newNode, max_power: parseInt(e.target.value)})}
                  className="w-full px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={addNode} className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-semibold transition">
                Create Node
              </button>
              <button onClick={() => setShowAddNode(false)} className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-semibold transition">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* GRID STATISTICS WITH GREEN SAVINGS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          {/* GREEN SAVINGS CARD - Takes 2 columns */}
          <GreenSavingsCard savings={savings} isOptimizing={autoOptimize} />

          {/* Total Power */}
          <StatCard
            icon={<Zap className="text-yellow-400" size={28} />}
            label="Total Power"
            value={`${gridStats.total_power.toFixed(0)} W`}
            subtitle={`${(gridStats.total_power / 1000).toFixed(2)} kW`}
            color="yellow"
          />

          {/* Average Load */}
          <StatCard
            icon={<Activity className="text-green-400" size={28} />}
            label="Avg Load"
            value={`${(gridStats.avg_load * 100).toFixed(1)}%`}
            subtitle={gridStats.avg_load > 0.7 ? 'High utilization' : 'Normal'}
            color="green"
          />

          {/* Average Temperature */}
          <StatCard
            icon={<Thermometer className="text-red-400" size={28} />}
            label="Avg Temp"
            value={`${gridStats.avg_temperature.toFixed(1)}°C`}
            subtitle={gridStats.avg_temperature > 50 ? 'Critical' : 'Normal'}
            color="red"
          />

          {/* Active Nodes */}
          <StatCard
            icon={<Cpu className="text-blue-400" size={28} />}
            label="Active Nodes"
            value={nodes.length}
            subtitle={`${nodes.filter(n => n.status !== 'sleep').length} running`}
            color="blue"
          />
        </div>

        {/* WORKLOAD INJECTION */}
        <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 mb-6 border border-gray-700 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="text-purple-400" size={24} />
            <h3 className="text-lg font-bold">Workload Injection</h3>
          </div>
          <div className="flex gap-3">
            <button onClick={() => injectWorkload(0.1)} className="flex-1 px-4 py-3 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/50 rounded-lg transition font-semibold">
              Light Load +10%
            </button>
            <button onClick={() => injectWorkload(0.3)} className="flex-1 px-4 py-3 bg-yellow-600/20 hover:bg-yellow-600/30 border border-yellow-500/50 rounded-lg transition font-semibold">
              Medium Load +30%
            </button>
            <button onClick={() => injectWorkload(0.5)} className="flex-1 px-4 py-3 bg-red-600/20 hover:bg-red-600/30 border border-red-500/50 rounded-lg transition font-semibold">
              Heavy Load +50%
            </button>
          </div>
        </div>

        {/* PREDICTION COMPARISON & MONTHLY FORECAST */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Prediction vs Actual */}
          <PredictionComparisonCard 
            prediction={prediction} 
            current={gridStats.total_power}
            isOptimizing={autoOptimize}
          />

          {/* Monthly Forecast */}
          {prediction && (
            <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/20 backdrop-blur rounded-xl p-5 border border-indigo-500/30 shadow-xl">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-indigo-500/20 rounded-lg">
                  <Calendar className="text-indigo-400" size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold">Monthly Cost Forecast</h3>
                  <p className="text-xs text-gray-400">Based on current patterns</p>
                </div>
                <div className="ml-auto">
                  <input
                    type="number"
                    step="0.10"
                    value={electricityRate}
                    onChange={(e) => setElectricityRate(parseFloat(e.target.value))}
                    className="w-24 px-3 py-1 bg-gray-700/50 border border-gray-600 rounded-lg text-sm text-right"
                  />
                  <div className="text-[10px] text-gray-500 text-right mt-0.5">₹/kWh</div>
                </div>
              </div>

              <div className="space-y-3">
                {/* With Optimization */}
                <div className="bg-emerald-900/20 rounded-lg p-4 border border-emerald-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Leaf className="text-emerald-400" size={16} />
                      <span className="text-sm text-emerald-300 font-semibold">With AI Optimization</span>
                    </div>
                    <div className="text-xs text-emerald-400/60">{prediction.predicted_monthly.toFixed(0)} kWh</div>
                  </div>
                  <div className="text-3xl font-bold text-emerald-300">
                    ₹{prediction.estimated_monthly_cost.toFixed(2)}
                  </div>
                </div>

                {/* Without Optimization */}
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-600/50 relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-red-500/10 px-2 py-1 text-[10px] text-red-400 rounded-bl">
                    BASELINE
                  </div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">Without Optimization</span>
                    <div className="text-xs text-gray-500">Est. consumption</div>
                  </div>
                  <div className="text-3xl font-bold text-gray-300 line-through opacity-60">
                    ₹{prediction.baseline_monthly_cost.toFixed(2)}
                  </div>
                </div>

                {/* Savings Summary */}
                <div className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 rounded-lg p-4 border-2 border-green-500/40 shadow-lg shadow-green-900/30">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs text-green-300/70 mb-1">You Save Per Month</div>
                      <div className="text-2xl font-bold text-green-300">
                        ₹{prediction.projected_savings.toFixed(2)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400 mb-1">Confidence</div>
                      <div className="text-lg font-bold text-white">
                        {(prediction.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Training Progress if not ready */}
          {!prediction && (
            <div className="bg-gray-800/30 backdrop-blur rounded-xl p-6 border border-gray-700 flex flex-col justify-center">
              <div className="flex items-center gap-3 mb-4">
                <Activity className="text-gray-500 animate-pulse" size={24} />
                <div>
                  <h3 className="font-bold text-gray-400">Training AI Model...</h3>
                  <p className="text-xs text-gray-500">Collecting data for accurate predictions</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Progress</span>
                  <span>{predictionStatus?.samples_collected || 0} / 50 samples</span>
                </div>
                <div className="bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-indigo-500 h-3 transition-all duration-500"
                    style={{ 
                      width: `${predictionStatus ? (predictionStatus.samples_collected / 50 * 100) : 0}%` 
                    }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Keep simulation running to train the model...
                </p>
              </div>
            </div>
          )}
        </div>

        {/* REAL-TIME CHARTS */}
        {history.length > 5 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700 shadow-xl">
              <h3 className="text-lg font-bold mb-4">Power Consumption (W)</h3>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={history}>
                  <defs>
                    <linearGradient id="colorPower" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#fbbf24" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" hide />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                    labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="power" 
                    stroke="#fbbf24" 
                    fillOpacity={1} 
                    fill="url(#colorPower)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700 shadow-xl">
              <h3 className="text-lg font-bold mb-4">Load & Temperature</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" hide />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                    labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="load" 
                    stroke="#10b981" 
                    strokeWidth={2} 
                    dot={false}
                    name="Load (%)"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="temp" 
                    stroke="#ef4444" 
                    strokeWidth={2} 
                    dot={false}
                    name="Temp (°C)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* OPTIMIZER LOGS - COLLAPSIBLE & DETAILED */}
        {autoOptimize && (
          <div className="bg-gray-800/50 backdrop-blur rounded-xl border border-gray-700 shadow-xl mb-6 overflow-hidden">
            {/* Header */}
            <div 
              className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition"
              onClick={() => setShowOptLogs(!showOptLogs)}
            >
              <div className="flex items-center gap-3">
                <Activity className="text-purple-400" size={20} />
                <div>
                  <h3 className="font-bold flex items-center gap-2">
                    Optimizer Activity Log
                    {optEvents.length > 0 && (
                      <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full">
                        {optEvents.length} events
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-gray-400">
                    {showOptLogs ? 'Detailed optimization actions' : 'Click to expand'}
                  </p>
                </div>
              </div>
              <button className="text-gray-400 hover:text-white transition">
                {showOptLogs ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>
            </div>

            {/* Content */}
            {showOptLogs && (
              <div className="p-4 pt-0 border-t border-gray-700 max-h-96 overflow-y-auto">
                {optEvents.length === 0 ? (
                  <div className="text-center py-6 text-gray-500">
                    <Activity size={32} className="mx-auto mb-2 opacity-50" />
                    <p className="text-sm">System balanced. No optimization needed.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {optEvents.map((event, i) => (
                      <div 
                        key={i} 
                        className={`bg-gray-900/50 rounded-lg p-3 border ${getPriorityColor(event.priority)} transition-all hover:bg-gray-900/70`}
                      >
                        {/* Header */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase ${getPriorityColor(event.priority)}`}>
                              {event.priority}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <span className="text-xs text-gray-500 uppercase tracking-wide">
                            {event.action.replace('_', ' ')}
                          </span>
                        </div>

                        {/* Main Info */}
                        <div className="grid grid-cols-2 gap-3 mb-2">
                          {/* Source */}
                          <div className="bg-red-900/20 rounded p-2 border border-red-500/20">
                            <div className="text-[10px] text-gray-500 mb-1">FROM</div>
                            <div className="font-bold text-red-400">{event.source_id}</div>
                            <div className="text-xs text-gray-400 mt-1">
                              {(event.before_source_load * 100).toFixed(0)}% → {(event.after_source_load * 100).toFixed(0)}%
                              <span className="text-green-400 ml-1">
                                (-{((event.before_source_load - event.after_source_load) * 100).toFixed(0)}%)
                              </span>
                            </div>
                            <div className="text-[10px] text-gray-500">Temp: {event.source_temp.toFixed(1)}°C</div>
                          </div>

                          {/* Target */}
                          <div className="bg-green-900/20 rounded p-2 border border-green-500/20">
                            <div className="text-[10px] text-gray-500 mb-1">TO</div>
                            <div className="font-bold text-green-400">{event.target_id}</div>
                            <div className="text-xs text-gray-400 mt-1">
                              {(event.before_target_load * 100).toFixed(0)}% → {(event.after_target_load * 100).toFixed(0)}%
                              <span className="text-blue-400 ml-1">
                                (+{((event.after_target_load - event.before_target_load) * 100).toFixed(0)}%)
                              </span>
                            </div>
                            <div className="text-[10px] text-gray-500">Temp: {event.target_temp.toFixed(1)}°C</div>
                          </div>
                        </div>

                        {/* Reason */}
                        <div className="text-sm text-gray-300 bg-gray-800/50 rounded px-2 py-1">
                          <span className="text-gray-500 text-xs">Reason: </span>
                          {event.reason}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* NODES GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {nodes.map(node => (
            <NodeCard
              key={node.id}
              node={node}
              isSelected={selectedNode?.id === node.id}
              onSelect={() => setSelectedNode(node)}
              onDelete={() => deleteNode(node.id)}
              onAdjustLoad={(delta) => adjustNodeLoad(node.id, delta)}
              getStatusColor={getStatusColor}
              getStatusBadgeColor={getStatusBadgeColor}
            />
          ))}
        </div>

        {nodes.length === 0 && (
          <div className="text-center py-12 bg-gray-800/30 rounded-xl border border-gray-700">
            <Cpu className="mx-auto mb-4 text-gray-600" size={48} />
            <p className="text-gray-400 text-lg">No nodes in the grid</p>
            <p className="text-gray-500 text-sm mt-2">Add a compute node to get started</p>
          </div>
        )}

      </div>
    </div>
  );
}

// ============================================================================
// STAT CARD COMPONENT
// ============================================================================
function StatCard({ icon, label, value, subtitle, color }) {
  const colorClasses = {
    yellow: 'from-yellow-500/10 to-yellow-600/5 border-yellow-500/30',
    green: 'from-green-500/10 to-green-600/5 border-green-500/30',
    red: 'from-red-500/10 to-red-600/5 border-red-500/30',
    blue: 'from-blue-500/10 to-blue-600/5 border-blue-500/30'
  };

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} backdrop-blur rounded-xl p-5 border shadow-xl`}>
      <div className="flex items-center gap-3 mb-3">
        {icon}
        <span className="text-gray-400 text-sm font-medium">{label}</span>
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm text-gray-500">{subtitle}</div>
    </div>
  );
}

// ============================================================================
// NODE CARD COMPONENT
// ============================================================================
function NodeCard({ node, isSelected, onSelect, onDelete, onAdjustLoad, getStatusColor, getStatusBadgeColor }) {
  return (
    <div
      onClick={onSelect}
      className={`bg-gray-800/50 backdrop-blur rounded-xl p-5 cursor-pointer transition-all border shadow-xl hover:shadow-2xl hover:scale-[1.02] ${
        isSelected ? 'ring-2 ring-blue-500 border-blue-500/50' : 'border-gray-700'
      } ${node.fan_override ? 'shadow-red-900/20 border-red-500/30' : ''}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(node.status)} shadow-lg`} />
          <h3 className="font-bold text-lg">{node.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-semibold ${getStatusBadgeColor(node.status)}`}>
            {node.status.toUpperCase()}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="text-red-400 hover:text-red-300 transition p-1"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      
      <div className="space-y-3">
        {/* CPU Load */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">CPU Load</span>
            <span className="font-semibold">{(node.load * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-2.5 rounded-full transition-all duration-300 shadow-lg ${
                node.fan_override 
                  ? 'bg-red-500 shadow-red-500/50' 
                  : 'bg-gradient-to-r from-blue-500 to-blue-600 shadow-blue-500/50'
              }`}
              style={{ width: `${node.load * 100}%` }}
            />
          </div>
        </div>

        {/* Fan UI */}
        <div className={`flex items-center justify-between p-2 rounded-lg border transition-colors ${
          node.fan_override 
            ? 'bg-red-900/20 border-red-500/50' 
            : 'bg-gray-700/30 border-gray-600/30'
        }`}>
          <div className="flex items-center gap-2">
            <SmoothFan speed={node.fan_speed} isOverride={node.fan_override} />
            <span className={`text-sm ${node.fan_override ? 'text-red-300 font-bold' : 'text-gray-300'}`}>
              {node.fan_override ? 'AI OVERRIDE' : 'Cooling'}
            </span>
          </div>
          <div className="text-right">
            <span className={`text-sm font-bold ${node.fan_override ? 'text-red-400' : 'text-cyan-400'}`}>
              {node.fan_speed.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Temperature */}
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-400">Core Temp</span>
          <span className={`font-mono font-bold text-lg ${
            node.temperature > 50 ? 'text-red-500' : 
            node.temperature > 40 ? 'text-orange-400' : 
            'text-emerald-400'
          }`}>
            {node.temperature.toFixed(1)}°C
          </span>
        </div>

        {/* Power & Cores */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Power</span>
            <span className="font-semibold">{node.power_consumption.toFixed(0)}W</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Cores</span>
            <span className="font-semibold">{node.cores}</span>
          </div>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-gray-700">
        <button
          onClick={(e) => { e.stopPropagation(); onAdjustLoad(-0.2); }}
          className="flex-1 px-3 py-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg transition text-sm font-semibold border border-gray-600"
        >
          - Load
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onAdjustLoad(0.2); }}
          className="flex-1 px-3 py-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg transition text-sm font-semibold border border-gray-600"
        >
          + Load
        </button>
      </div>

      {/* Warning Badge */}
      {node.temperature > 40 && (
        <div className="flex items-center gap-2 mt-3 px-3 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg">
          <AlertTriangle size={14} className="text-orange-400" />
          <span className="text-xs text-orange-300">High temperature</span>
        </div>
      )}
    </div>
  );
}

export default App;