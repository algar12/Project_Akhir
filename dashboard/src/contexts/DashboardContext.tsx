'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';

export type SystemStatus = {
  total_devices: number;
  total_alerts: number;
  total_traffic: number;
  total_anomalies: number;
  database: string;
  suricata_online?: boolean;
};

export type AlertStats = {
  total_alerts: number;
  by_severity: Record<string, number>;
  by_attack_type: Record<string, number>;
  most_active_sources?: Array<{ source_ip: string; count: number }>;
};

export type Device = {
  id: number;
  device_name: string;
  ip_address: string;
  mac_address: string | null;
  device_type: string;
  status: string;
  last_seen: string;
};

export type TrafficRecord = {
  id: number;
  timestamp: string;
  source_ip: string;
  destination_ip: string;
  protocol: string;
  source_port: number;
  destination_port: number;
  packet_count: number;
  bytes: number;
  is_syn?: boolean;
};

export type PredictionRecord = {
  id: number;
  timestamp: string;
  source_ip: string;
  time_bucket: string;
  if_score: number;
  is_anomaly: boolean;
  attack_class: string;
  confidence: number;
};

export type NetworkInfo = {
  interface: string;
  subnet: string;
  local_ip: string | null;
  gateway: string | null;
};

export type DashboardContextType = {
  system: SystemStatus | null;
  alerts: AlertStats | null;
  latestAlerts: any[];
  liveAlerts: any[];
  clearLiveAlerts: () => void;
  devices: Device[];
  traffic: TrafficRecord[];
  predictions: PredictionRecord[];
  network: NetworkInfo | null;
  isConnected: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  timeRangeHours: number;
  setTimeRangeHours: (hours: number) => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  refreshData: () => Promise<void>;
};

const defaultContext: DashboardContextType = {
  system: null,
  alerts: null,
  latestAlerts: [],
  liveAlerts: [],
  clearLiveAlerts: () => {},
  devices: [],
  traffic: [],
  predictions: [],
  network: null,
  isConnected: false,
  activeTab: 'Dashboard',
  setActiveTab: () => {},
  searchQuery: '',
  setSearchQuery: () => {},
  timeRangeHours: 24,
  setTimeRangeHours: () => {},
  apiKey: 'dummy_key',
  setApiKey: () => {},
  refreshData: async () => {},
};

const DashboardContext = createContext<DashboardContextType>(defaultContext);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [alerts, setAlerts] = useState<AlertStats | null>(null);
  const [latestAlerts, setLatestAlerts] = useState<any[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<any[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [traffic, setTraffic] = useState<TrafficRecord[]>([]);
  const [predictions, setPredictions] = useState<PredictionRecord[]>([]);
  const [network, setNetwork] = useState<NetworkInfo | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRangeHours, setTimeRangeHours] = useState(24);
  const [apiKey, setApiKey] = useState('dummy_key');

  const clearLiveAlerts = useCallback(() => {
    setLiveAlerts([]);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const headers = { 'X-API-Key': apiKey };
      
      const [sysRes, alertRes, devRes, trafRes, alertListRes, predRes, netRes] = await Promise.all([
        fetch('/api/v1/system/status', { headers }).catch(() => null),
        fetch(`/api/v1/alerts/stats?hours=${timeRangeHours}`, { headers }).catch(() => null),
        fetch('/api/v1/devices?limit=50', { headers }).catch(() => null),
        fetch('/api/v1/traffic?limit=100', { headers }).catch(() => null),
        fetch('/api/v1/alerts?limit=10', { headers }).catch(() => null),
        fetch('/api/v1/predictions?limit=60', { headers }).catch(() => null),
        fetch('/api/v1/system/network', { headers }).catch(() => null),
      ]);

      if (sysRes?.ok) {
        const sysData: SystemStatus = await sysRes.json();
        setSystem(prev => {
          if (prev && 
              prev.total_devices === sysData.total_devices &&
              prev.total_alerts === sysData.total_alerts &&
              prev.total_traffic === sysData.total_traffic &&
              prev.total_anomalies === sysData.total_anomalies &&
              prev.database === sysData.database) {
            return prev;
          }
          return sysData;
        });
      }
      if (alertRes?.ok) {
        const alertData: AlertStats = await alertRes.json();
        setAlerts(prev => {
          if (prev && prev.total_alerts === alertData.total_alerts) {
            return prev;
          }
          return alertData;
        });
      }
      if (alertListRes?.ok) {
        const listData = await alertListRes.json();
        if (listData.alerts) {
          setLatestAlerts(listData.alerts);
        }
      }
      if (devRes?.ok) {
        const devData = await devRes.json();
        if (devData.devices) {
          setDevices(prev => {
            if (prev.length === devData.devices.length) {
              const unchanged = prev.every((d, i) => {
                const nd = devData.devices[i];
                return nd && d.id === nd.id && d.status === nd.status && d.last_seen === nd.last_seen;
              });
              if (unchanged) return prev;
            }
            return devData.devices;
          });
        }
      }
      if (trafRes?.ok) {
        const trafData = await trafRes.json();
        if (trafData.traffic) {
          setTraffic(prev => {
            if (prev.length === trafData.traffic.length && prev[0]?.id === trafData.traffic[0]?.id) {
              return prev;
            }
            return trafData.traffic;
          });
        }
      }
      if (predRes?.ok) {
        const predData = await predRes.json();
        if (predData.predictions) {
          setPredictions(predData.predictions);
        }
      }
      if (netRes?.ok) {
        const netData: NetworkInfo = await netRes.json();
        setNetwork(netData);
      }
    } catch (err) {
      console.error('[DashboardContext] Failed to fetch data', err);
    }
  }, [apiKey, timeRangeHours]);

  useEffect(() => {
    fetchData();
    // 2.5 second polling interval with diff-checking keeps UI responsive and low CPU
    const interval = setInterval(fetchData, 2500);

    // Direct WebSocket connection to FastAPI backend (Port 8000)
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isUnmounted = false;

    const connectWs = () => {
      if (isUnmounted) return;
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Connect directly to FastAPI port 8000 to avoid Next.js dev server proxy WS incompatibilities
        const hostName = window.location.hostname || 'localhost';
        const wsPort = (window.location.port === '3000' || window.location.port === '3001') ? '8000' : (window.location.port || '8000');
        const wsUrl = `${protocol}//${hostName}:${wsPort}/ws/alerts?token=${apiKey}`;
        
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!isUnmounted) setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const alert = JSON.parse(event.data);
            if (alert.event === 'new_alert') {
              setLiveAlerts(prev => [alert, ...prev].slice(0, 50));
              setLatestAlerts(prev => [alert, ...prev].slice(0, 20));
            }
          } catch {
            // ignore heartbeat or parse errors
          }
        };

        ws.onclose = () => {
          if (!isUnmounted) {
            setIsConnected(false);
            reconnectTimeout = setTimeout(connectWs, 4000);
          }
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch {
        if (!isUnmounted) {
          reconnectTimeout = setTimeout(connectWs, 4000);
        }
      }
    };

    connectWs();

    return () => {
      isUnmounted = true;
      clearInterval(interval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
      }
    };
  }, [fetchData, apiKey]);

  const value = useMemo(() => ({
    system,
    alerts,
    latestAlerts,
    liveAlerts,
    clearLiveAlerts,
    devices,
    traffic,
    predictions,
    network,
    isConnected,
    activeTab,
    setActiveTab,
    searchQuery,
    setSearchQuery,
    timeRangeHours,
    setTimeRangeHours,
    apiKey,
    setApiKey,
    refreshData: fetchData,
  }), [
    system,
    alerts,
    latestAlerts,
    liveAlerts,
    clearLiveAlerts,
    devices,
    traffic,
    predictions,
    network,
    isConnected,
    activeTab,
    searchQuery,
    timeRangeHours,
    apiKey,
    fetchData,
  ]);

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  return useContext(DashboardContext);
}
