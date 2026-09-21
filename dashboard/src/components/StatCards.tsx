'use client';
import { useDashboard } from '@/contexts/DashboardContext';
import { isHeartbeatFresh } from '@/components/LiveTopologyMap';
import { ArrowUp, Radio, Cpu, ShieldAlert, Sliders, RefreshCw, Activity } from 'lucide-react';

export default function StatCards() {
  const { system, alerts, devices, refreshData, network } = useDashboard();
  
  const totalTraffic = system?.total_traffic ?? 0;
  const criticalAlerts = (alerts?.by_severity?.['CRITICAL'] ?? 0);
  const totalAlerts = (alerts?.total_alerts ?? 0);
  const endpointsCount = devices.length > 0 ? devices.length : 5;
  const onlineCount = devices.filter(d => d.status === 'online' && isHeartbeatFresh(d.last_seen)).length;
  const captureInterface = network?.interface ?? '—';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 shrink-0">
      {/* Card 1: Total Captured Packets (Scapy Raw Sniffer) */}
      <div className="sm:col-span-4 panel p-4 flex flex-col justify-between group hover:border-cyan-500/30 transition-all cursor-pointer">
        <div className="flex justify-between items-start">
          <div className="text-3xl font-extrabold text-white flex items-center gap-1.5 tracking-tight font-mono">
            <ArrowUp className="w-5 h-5 text-cyan-400 stroke-[3]" />
            <span>{totalTraffic.toLocaleString()}</span>
          </div>
          <Activity className="w-4 h-4 text-cyan-400/80" />
        </div>
        <div className="text-xs text-slate-400 mt-3 flex items-center gap-2 font-medium">
          <div className="w-4 h-4 bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center rounded text-[10px]">
            <Radio className="w-2.5 h-2.5" />
          </div>
          <span>Scapy Captured Packets ({captureInterface})</span>
        </div>
      </div>

      {/* Card 2: Security Alerts (Suricata & Rule Engine) */}
      <div className="sm:col-span-4 panel p-4 flex flex-col justify-between group hover:border-red-500/30 transition-all cursor-pointer">
        <div className="flex justify-between items-start">
          <div className="text-3xl font-extrabold text-white tracking-tight font-mono">
            {totalAlerts.toLocaleString()}
          </div>
          <ShieldAlert className={`w-4 h-4 ${criticalAlerts > 0 ? 'text-red-500' : 'text-slate-500'}`} />
        </div>
        <div className="text-xs text-slate-400 mt-3 flex items-center gap-2 font-medium">
          <div className="w-4 h-4 bg-red-600/80 text-white flex items-center justify-center rounded text-[10px] shadow-[0_0_8px_rgba(239,68,68,0.7)] font-bold">
            !
          </div>
          <span>Suricata & Anomaly Alerts ({criticalAlerts} Critical)</span>
        </div>
      </div>

      {/* Card 3: Monitored IoT Hardware Nodes (ESP32 Nodes) */}
      <div className="sm:col-span-4 panel p-4 flex justify-between items-center group hover:border-green-500/30 transition-all cursor-pointer relative overflow-hidden">
        <div className="flex flex-col justify-between h-full">
          <div className="text-3xl font-extrabold text-white tracking-tight font-mono">
            {onlineCount}/{endpointsCount}
            <span className="text-xs font-normal text-slate-400 ml-2">Online</span>
          </div>
          <div className="text-xs text-slate-400 mt-3 flex items-center gap-2 font-medium">
            <div className={`w-4 h-4 rounded text-[10px] flex items-center justify-center border ${
              onlineCount > 0
                ? 'bg-green-500/20 border-green-500/40 text-green-400'
                : 'bg-amber-500/20 border-amber-500/40 text-amber-400'
            }`}>
              <Cpu className="w-2.5 h-2.5" />
            </div>
            <span>
              {onlineCount > 0
                ? 'ESP32 Node Terhubung'
                : 'ESP32 Hardware (Menunggu Koneksi)'}
            </span>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-col gap-2 border-l border-white/10 pl-3 text-slate-500">
          <button 
            onClick={(e) => { e.stopPropagation(); refreshData(); }}
            title="Refresh metrics" 
            className="hover:text-cyan-400 transition-colors p-0.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button title="Subnet filter" className="hover:text-white transition-colors p-0.5">
            <Sliders className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
