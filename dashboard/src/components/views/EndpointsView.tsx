'use client';
import { useDashboard } from '@/contexts/DashboardContext';
import { isHeartbeatFresh } from '@/components/LiveTopologyMap';
import { Cpu, Wifi, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function EndpointsView() {
  const { devices, network, refreshData } = useDashboard();

  return (
    <div className="flex-1 flex flex-col gap-3">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 shrink-0">
        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Total Endpoints</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2">
            {devices.length}
          </div>
          <div className="text-[10px] text-green-400 mt-1">Managed Nodes</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Gateway Subnet</span>
            <Wifi className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2 font-mono">
            {network?.subnet || '—'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Subnet Aktif (Gateway: {network?.gateway || '—'})</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Network Health</span>
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-2xl font-extrabold text-green-400 mt-2 font-mono">
            100%
          </div>
          <div className="text-[10px] text-green-400 mt-1">All Nodes Registered</div>
        </div>
      </div>

      {/* Endpoints Cards Grid */}
      <div className="panel p-4 flex-1 flex flex-col min-h-[450px]">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-bold text-white">Registered IoT Hardware & Nodes</h2>
          <button
            onClick={() => refreshData()}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-white/5 px-2.5 py-1 rounded border border-white/10 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Scan Endpoints</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 overflow-auto">
          {devices.map(dev => (
            <div
              key={dev.id}
              className="panel-subtle p-4 flex flex-col justify-between border border-white/10 hover:border-cyan-500/40 transition-all group"
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-cyan-400 transition-colors">
                      {dev.device_name}
                    </h3>
                    <span className="text-[10px] text-slate-400 font-mono">{dev.ip_address}</span>
                  </div>
                </div>

              {(() => {
                const isOnline = dev.status === 'online' && isHeartbeatFresh(dev.last_seen);
                return (
                  <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                    isOnline ? 'bg-green-500/20 text-green-400 border border-green-500/40' :
                    dev.status === 'registered' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40' :
                    'bg-slate-500/20 text-slate-400 border border-slate-500/40'
                  }`}>
                    {isOnline ? 'online' : (dev.status === 'registered' ? 'registered' : 'offline')}
                  </span>
                );
              })()}
              </div>

              <div className="mt-3 text-xs text-slate-300 font-medium bg-[#0b0e17] p-2.5 rounded border border-white/5">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Sensor Type</div>
                <div>{dev.device_type}</div>
              </div>

              <div className="mt-3 pt-2 border-t border-white/5 flex justify-between items-center text-[10px] text-slate-500 font-mono">
                <span>Last heartbeat:</span>
                <span>{dev.last_seen ? new Date(dev.last_seen.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(dev.last_seen) ? dev.last_seen : dev.last_seen + 'Z').toLocaleTimeString() : 'Never'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
