'use client';
import { useDashboard } from '@/contexts/DashboardContext';
import { ShieldAlert, AlertTriangle, ShieldCheck, Flame, Filter } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function ThreatsView() {
  const { alerts, liveAlerts, apiKey } = useDashboard();
  const [alertsList, setAlertsList] = useState<any[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  useEffect(() => {
    fetch('/api/v1/alerts?limit=50', {
      headers: { 'X-API-Key': apiKey }
    })
      .then(res => res.json())
      .then(data => {
        if (data.alerts) setAlertsList(data.alerts);
      })
      .catch(() => {});
  }, [apiKey]);

  // Combine fetched alerts with incoming real-time alerts
  const combinedAlerts = [...liveAlerts, ...alertsList];
  const uniqueAlerts = Array.from(new Map(combinedAlerts.map(a => [a.id, a])).values());

  const filteredAlerts = uniqueAlerts.filter(a => {
    if (severityFilter !== 'ALL' && a.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="flex-1 flex flex-col gap-3">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 shrink-0">
        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Critical Severity</span>
            <Flame className="w-4 h-4 text-red-500" />
          </div>
          <div className="text-2xl font-extrabold text-red-500 mt-2 glow-red">
            {alerts?.by_severity?.['CRITICAL'] ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Requires immediate intervention</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>High Severity</span>
            <AlertTriangle className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-2xl font-extrabold text-orange-400 mt-2 glow-orange">
            {alerts?.by_severity?.['HIGH'] ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Threats quarantined</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Medium / Low</span>
            <ShieldCheck className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-2xl font-extrabold text-green-400 mt-2">
            {(alerts?.by_severity?.['MEDIUM'] ?? 0) + (alerts?.by_severity?.['LOW'] ?? 0)}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Suricata anomaly probes</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Total Threats</span>
            <ShieldAlert className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2">
            {alerts?.total_alerts ?? uniqueAlerts.length}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Logged across all sensors</div>
        </div>
      </div>

      {/* Threats Table */}
      <div className="panel p-4 flex-1 flex flex-col min-h-[450px]">
        <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold text-white">Threat Detection Feed</h2>
            <div className="flex gap-1.5 text-xs">
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-colors ${
                    severityFilter === sev
                      ? 'bg-red-500/20 text-red-300 border border-red-500/50'
                      : 'bg-white/5 text-slate-400 hover:text-white border border-transparent'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            Showing {filteredAlerts.length} incidents
          </span>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto border border-white/5 rounded-lg">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#0b0e17] text-[10px] uppercase font-mono text-slate-400 sticky top-0 border-b border-white/10">
              <tr>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Attack Type</th>
                <th className="py-2.5 px-3">Source IP</th>
                <th className="py-2.5 px-3">Target IP</th>
                <th className="py-2.5 px-3">Confidence</th>
                <th className="py-2.5 px-3">Description</th>
                <th className="py-2.5 px-3">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-[11px]">
              {filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-500 font-medium">
                    No active threats detected. All systems operating normally.
                  </td>
                </tr>
              ) : (
                filteredAlerts.map(a => (
                  <tr key={a.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono ${
                        a.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/40' :
                        a.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40' :
                        a.severity === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' :
                        'bg-green-500/20 text-green-400 border border-green-500/40'
                      }`}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-white">{a.attack_type}</td>
                    <td className="py-2.5 px-3 font-mono text-cyan-400">{a.source_ip}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">{a.target_ip}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-green-400">
                      {(a.confidence * 100).toFixed(0)}%
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate">{a.description}</td>
                    <td className="py-2.5 px-3 text-slate-500 font-mono text-[10px]">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </td>
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
