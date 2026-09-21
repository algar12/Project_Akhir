'use client';
import { useDashboard } from '@/contexts/DashboardContext';
import { Activity, Radio, ArrowDownUp, RefreshCw, Filter } from 'lucide-react';
import { useState } from 'react';

export default function NetworkView() {
  const { traffic, system, network, refreshData } = useDashboard();
  const [selectedProto, setSelectedProto] = useState<string>('ALL');

  const filteredTraffic = traffic.filter(item => {
    if (selectedProto !== 'ALL' && item.protocol !== selectedProto) return false;
    return true;
  });

  const totalBytes = traffic.reduce((acc, curr) => acc + (curr.bytes || 0), 0);

  return (
    <div className="flex-1 flex flex-col gap-3">
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 shrink-0">
        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Captured Packets</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2">
            {(system?.total_traffic ?? traffic.length).toLocaleString()}
          </div>
          <div className="text-[10px] text-green-400 mt-1">Live Sniffer Active ({network?.interface || '—'})</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Traffic Volume</span>
            <ArrowDownUp className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2">
            {(totalBytes / 1024).toFixed(1)} KB
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Buffer Window</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Sniffer Interface</span>
            <Radio className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2 font-mono">
            {network?.interface || '—'}
          </div>
          <div className="text-[10px] text-green-400 mt-1">Promiscuous Mode</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Subnet Monitored</span>
            <Filter className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2 font-mono text-base">
            {network?.subnet || '—'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Local IoT Gateway</div>
        </div>
      </div>

      {/* Network Traffic Records Table */}
      <div className="panel p-4 flex-1 flex flex-col min-h-[450px]">
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold text-white">Live Network Sniffer Traffic</h2>
            {/* Protocol Filter Pills */}
            <div className="flex gap-1.5 text-xs">
              {['ALL', 'TCP', 'UDP', 'ICMP'].map(proto => (
                <button
                  key={proto}
                  onClick={() => setSelectedProto(proto)}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                    selectedProto === proto
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                      : 'bg-white/5 text-slate-400 hover:text-white border border-transparent'
                  }`}
                >
                  {proto}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => refreshData()}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-white/5 px-2.5 py-1 rounded border border-white/10 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Refresh</span>
          </button>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto border border-white/5 rounded-lg">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#0b0e17] text-[10px] uppercase font-mono text-slate-400 sticky top-0 border-b border-white/10">
              <tr>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Source IP</th>
                <th className="py-2.5 px-3">Src Port</th>
                <th className="py-2.5 px-3">Destination IP</th>
                <th className="py-2.5 px-3">Dst Port</th>
                <th className="py-2.5 px-3">Protocol</th>
                <th className="py-2.5 px-3">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-[11px]">
              {filteredTraffic.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-500">
                    No traffic records matching current filter.
                  </td>
                </tr>
              ) : (
                filteredTraffic.map(item => (
                  <tr key={item.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-2 px-3 text-slate-500">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-2 px-3 text-cyan-400 font-semibold">{item.source_ip}</td>
                    <td className="py-2 px-3 text-slate-400">{item.source_port || '-'}</td>
                    <td className="py-2 px-3 text-slate-300">{item.destination_ip}</td>
                    <td className="py-2 px-3 text-slate-400">{item.destination_port || '-'}</td>
                    <td className="py-2 px-3">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                        item.protocol === 'TCP' ? 'bg-blue-500/20 text-blue-400' :
                        item.protocol === 'UDP' ? 'bg-purple-500/20 text-purple-400' :
                        'bg-orange-500/20 text-orange-400'
                      }`}>
                        {item.protocol}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-400">{item.bytes} B</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
