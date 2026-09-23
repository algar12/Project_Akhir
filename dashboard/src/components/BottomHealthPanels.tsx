'use client';
import { useDashboard } from '@/contexts/DashboardContext';
import { isHeartbeatFresh } from '@/components/LiveTopologyMap';
import { ArrowUpRight, Check, ShieldAlert } from 'lucide-react';

export default function BottomHealthPanels() {
  const { system, alerts, isConnected, devices, latestAlerts, liveAlerts, predictions } = useDashboard();

  const endpointsCount = devices.length > 0 ? devices.length : 3;
  const now = Date.now();
  const onlineCount = devices.filter(d => d.status === 'online' && isHeartbeatFresh(d.last_seen, now)).length;

  // Statistik nyata
  const totalAlerts = alerts?.total_alerts ?? system?.total_alerts ?? 0;
  const totalAnomalies = system?.total_anomalies ?? 0;
  const criticalCount = alerts?.by_severity?.['CRITICAL'] ?? 0;
  const highCount = alerts?.by_severity?.['HIGH'] ?? 0;
  const medLowCount = (alerts?.by_severity?.['MEDIUM'] ?? 0) + (alerts?.by_severity?.['LOW'] ?? 0);

  // Distribusi severity (progress bar)
  const sevTotal = Math.max(1, criticalCount + highCount + medLowCount);
  const criticalPct = Math.round((criticalCount / sevTotal) * 100);
  const highPct = Math.round((highCount / sevTotal) * 100);
  const medLowPct = Math.max(0, 100 - criticalPct - highPct);

  // Tingkat anomali dari prediksi ML nyata
  const anomalyRate = predictions.length > 0
    ? Math.round((predictions.filter(p => p.is_anomaly).length / predictions.length) * 100)
    : 0;

  // Persentase node online
  const onlinePct = endpointsCount > 0 ? Math.round((onlineCount / endpointsCount) * 100) : 0;

  // Feed respons: gabungkan alert live + terbaru (dedupe, ambil 3)
  const feedAlerts = Array.from(
    new Map([...liveAlerts, ...latestAlerts].map(a => [a.id, a])).values()
  ).slice(0, 3);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1">
      {/* LEFT COLUMN: Dual-Layer Engine & Edge Infrastructure Table */}
      <div className="flex flex-col gap-3">
        {/* Panel 1: Dual-Layer Engine Status */}
        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-xs font-bold text-white">Dual-Layer Detection Engine</h3>
            {/* Live Connection status dot */}
            <div className="flex items-center gap-1.5 text-[9px] text-slate-400">
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-400 shadow-[0_0_6px_#22c55e]' : 'bg-red-500 shadow-[0_0_6px_#ef4444]'}`}></span>
              <span>{isConnected ? 'WebSocket Stream Active' : 'Offline'}</span>
            </div>
          </div>

          <div className="flex justify-between font-extrabold text-xl my-1 px-1">
            <div className="flex flex-col">
              <span className="text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]">{totalAlerts}</span>
              <span className="text-[9px] text-slate-400 font-normal">Alert Aktif</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-teal-400 drop-shadow-[0_0_8px_rgba(45,212,191,0.5)]">{totalAnomalies}</span>
              <span className="text-[9px] text-slate-400 font-normal">ML Anomali</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-green-400 drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]">{onlineCount}/{endpointsCount}</span>
              <span className="text-[9px] text-slate-400 font-normal">Node Online</span>
            </div>
          </div>

          {/* Triple-Segmented Progress Bar: distribusi severity nyata */}
          <div className="w-full h-2 bg-[#0b0e17] flex overflow-hidden my-2 border border-white/10 rounded-full">
            <div className="h-full bg-purple-500 shadow-[0_0_8px_#a855f7]" style={{ width: `${criticalPct}%` }}></div>
            <div className="h-full bg-teal-400 shadow-[0_0_8px_#2dd4bf]" style={{ width: `${highPct}%` }}></div>
            <div className="h-full bg-green-500 shadow-[0_0_8px_#22c55e]" style={{ width: `${medLowPct}%` }}></div>
          </div>

          {/* Filter Checkboxes with Colored Accents */}
          <div className="flex justify-between text-[11px] text-slate-400 pt-1 font-medium">
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors">
              <input type="checkbox" defaultChecked className="accent-purple-500 w-3 h-3 rounded cursor-pointer" /> 
              <span>Suricata IDS</span>
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors">
              <input type="checkbox" defaultChecked className="accent-teal-400 w-3 h-3 rounded cursor-pointer" /> 
              <span>Isolation Forest</span>
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors">
              <input type="checkbox" defaultChecked className="accent-green-500 w-3 h-3 rounded cursor-pointer" /> 
              <span>MQTT Guard</span>
            </label>
          </div>
        </div>
        
        {/* Panel 2: Edge Infrastructure Hardware Health */}
        <div className="panel p-4 flex-1 flex flex-col justify-between">
          <h3 className="text-xs font-bold text-white mb-2">Edge Testbed Infrastructure</h3>
          <div className="space-y-2.5 flex-1 justify-center flex flex-col">
            <div className="flex justify-between items-center text-xs border-b border-white/5 pb-2 hover:bg-white/5 px-2 py-1 rounded transition-colors cursor-pointer">
              <span className="text-slate-300 font-medium">Edge PC Server</span>
              <span className="font-mono text-slate-400">Ryzen 5 5500GT</span>
              <span className={`font-bold font-mono ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                {isConnected ? 'ONLINE' : 'OFFLINE'}
              </span>
              <span className="text-slate-500 text-[10px] font-mono">RAM 8GB</span>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-white/5 pb-2 hover:bg-white/5 px-2 py-1 rounded transition-colors cursor-pointer">
              <span className="text-slate-300 font-medium">TP-Link Router (IoT)</span>
              <span className="font-mono text-slate-400">TL-WR820N</span>
              <span className={`font-bold font-mono ${system ? 'text-green-400' : 'text-red-400'}`}>
                {system ? 'ACTIVE' : 'OFFLINE'}
              </span>
              <span className="text-slate-500 text-[10px] font-mono">192.168.20.1</span>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-white/5 pb-2 hover:bg-white/5 px-2 py-1 rounded transition-colors cursor-pointer">
              <span className="text-slate-300 font-medium">ESP32 IoT Nodes</span>
              <span className="font-mono text-slate-400">{endpointsCount} Nodes</span>
              <span className={`font-bold font-mono ${onlineCount > 0 ? 'text-green-400' : 'text-amber-400'}`}>
                {onlineCount}/{endpointsCount} UP
              </span>
              <span className="text-slate-500 text-[10px] font-mono">MQTT 1883</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* RIGHT COLUMN: Evaluation SLA Metrics & Live Alert Feed */}
      <div className="flex flex-col gap-3">
        {/* Panel 3: Model Accuracy & SLA Metrics (data nyata) */}
        <div className="panel p-4 flex flex-col justify-between">
          <h3 className="text-xs font-bold text-white mb-3">Real-Time System Metrics</h3>
          <div className="space-y-3.5 my-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex-1 mr-3 h-2 bg-[#141a29] rounded-full overflow-hidden">
                <div className="bg-green-500 h-full shadow-[0_0_8px_#22c55e]" style={{ width: `${isConnected ? 100 : 0}%` }}></div>
              </div> 
              <div className="flex gap-2 font-mono text-[11px] font-bold text-green-400">
                <span>{isConnected ? '100%' : '0%'}</span>
                <span className="text-slate-400">WS Connected</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <div className="flex-1 mr-3 h-2 bg-[#141a29] rounded-full overflow-hidden">
                <div className="bg-teal-400 h-full shadow-[0_0_8px_#2dd4bf]" style={{ width: `${anomalyRate}%` }}></div>
              </div> 
              <div className="flex gap-2 font-mono text-[11px] font-bold text-teal-400">
                <span>{anomalyRate}%</span>
                <span className="text-slate-400">IF Anomaly Rate</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <div className="flex-1 mr-3 h-2 bg-[#141a29] rounded-full overflow-hidden">
                <div className="bg-orange-500 h-full shadow-[0_0_8px_#f97316]" style={{ width: `${highPct + criticalPct}%` }}></div>
              </div> 
              <div className="flex gap-2 font-mono text-[11px] font-bold text-orange-400">
                <span>{criticalPct + highPct}%</span>
                <span className="text-slate-400">Alert HIGH/CRIT</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <div className="flex-1 mr-3 h-2 bg-[#141a29] rounded-full overflow-hidden">
                <div className="bg-cyan-400 h-full shadow-[0_0_8px_#22d3ee]" style={{ width: `${onlinePct}%` }}></div>
              </div> 
              <div className="flex gap-2 font-mono text-[11px] font-bold text-cyan-400">
                <span>{onlinePct}%</span>
                <span className="text-slate-400">Node Online</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Panel 4: Live Alert Response Feed (data nyata, bukan mitigasi palsu) */}
        <div className="panel p-4 flex-1 flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center gap-1.5 font-bold text-xs text-white">
              <span>Live Alert Response Feed</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
            </div>
          </div>

          {feedAlerts.length === 0 ? (
            <div className="flex-1 flex flex-col justify-center items-center text-center gap-1">
              <ShieldAlert className="w-5 h-5 text-slate-600" />
              <span className="text-xs text-slate-500">Tidak ada alert — sistem dalam kondisi normal</span>
            </div>
          ) : (
            <div className="space-y-2.5 flex-1 justify-center flex flex-col">
              {feedAlerts.map(a => (
                <div key={a.id} className="flex justify-between items-center text-xs hover:bg-white/5 px-2 py-1 rounded transition-colors cursor-pointer">
                  <span className="flex items-center gap-2">
                    <div className={`${
                      a.severity === 'CRITICAL' || a.severity === 'HIGH'
                        ? 'bg-red-500/20 border-red-500/40 text-red-500'
                        : 'bg-orange-500/20 border-orange-500/40 text-orange-500'
                    } w-4 h-4 flex items-center justify-center rounded text-[10px] border`}>
                      <Check className="w-2.5 h-2.5 stroke-[3]" />
                    </div>
                    <span className="text-slate-300 font-medium">{a.attack_type || 'Security Alert'}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="text-slate-500 font-mono text-[10px]">{a.source_ip}</span>
                    <span className={`font-mono font-bold text-[10px] ${
                      a.severity === 'CRITICAL' || a.severity === 'HIGH' ? 'text-red-400' : 'text-orange-400'
                    }`}>{a.severity}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}