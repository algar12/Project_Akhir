'use client';
import { useDashboard } from '@/contexts/DashboardContext';
import { AlertOctagon, CheckCircle, Clock, ShieldCheck } from 'lucide-react';
import { useState, useEffect } from 'react';

type Incident = {
  id: number;
  title: string;
  target: string;
  source: string;
  status: 'ACTIVE' | 'INVESTIGATING' | 'RESOLVED';
  severity: string;
  time: string;
  details: string;
};

function timeAgo(ts?: string): string {
  if (!ts) return '—';
  const diffMs = Date.now() - new Date(ts).getTime();
  const mins = Math.max(0, Math.floor(diffMs / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m ago`;
}

export default function IncidentsView() {
  const { system, alerts, liveAlerts, apiKey } = useDashboard();
  const [resolvedIds, setResolvedIds] = useState<number[]>([]);
  const [alertList, setAlertList] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/v1/alerts?limit=30', { headers: { 'X-API-Key': apiKey } })
      .then(res => res.json())
      .then(data => { if (data.alerts) setAlertList(data.alerts); })
      .catch(() => {});
  }, [apiKey]);

  // Gabungkan alert DB + live, dedupe by id → incident nyata
  const incidents: Incident[] = Array.from(
    new Map([...liveAlerts, ...alertList].map(a => [a.id, a])).values()
  ).map(a => ({
    id: a.id,
    title: a.attack_type || 'Security Alert',
    target: a.target_ip || '—',
    source: a.source_ip || '—',
    // Status dari API (a.mitigated) + resolve lokal sesi ini — persisten antar refresh
    status: (a.mitigated || resolvedIds.includes(a.id)) ? 'RESOLVED' : (a.severity === 'CRITICAL' ? 'ACTIVE' : 'INVESTIGATING'),
    severity: a.severity || 'LOW',
    time: timeAgo(a.timestamp),
    details: a.description || 'Detected by detection engine.',
  }));

  const activeIncidents = incidents.filter(i => i.status !== 'RESOLVED').length;

  const handleResolve = async (id: number) => {
    // Tandai mitigated di backend (persisten), lalu update UI
    try {
      await fetch(`/api/v1/alerts/${id}/mitigate`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
      });
      setAlertList(prev => prev.map(a => a.id === id ? { ...a, mitigated: true, mitigated_at: new Date().toISOString() } : a));
    } catch {
      // Fallback: tetap tandai di sesi ini walau API gagal
    } finally {
      setResolvedIds(prev => prev.includes(id) ? prev : [...prev, id]);
    }
  };

  return (
    <div className="flex-1 flex flex-col gap-3">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 shrink-0">
        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Active Incidents</span>
            <AlertOctagon className="w-4 h-4 text-red-500" />
          </div>
          <div className="text-2xl font-extrabold text-red-500 mt-2 glow-red">
            {activeIncidents}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Dari alert terdeteksi</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>ML Anomalies</span>
            <Clock className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-2xl font-extrabold text-white mt-2">
            {system?.total_anomalies ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Isolation Forest Flagged</div>
        </div>

        <div className="panel p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>Resolved (Sesi Ini)</span>
            <CheckCircle className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-2xl font-extrabold text-green-400 mt-2">
            {resolvedIds.length}
          </div>
          <div className="text-[10px] text-green-400 mt-1">Diresolve via tombol Mitigate</div>
        </div>
      </div>

      {/* Incidents List */}
      <div className="panel p-4 flex-1 flex flex-col min-h-[450px]">
        <h2 className="text-sm font-bold text-white mb-3">Security Incident Management</h2>

        {incidents.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center">
            <ShieldCheck className="w-8 h-8 text-green-500/50" />
            <span className="text-sm text-slate-400">Tidak ada incident — semua sistem normal</span>
            <span className="text-[10px] text-slate-600">Incident akan muncul otomatis saat ada alert terdeteksi</span>
          </div>
        ) : (
          <div className="space-y-3 overflow-auto">
            {incidents.map(inc => (
              <div
                key={inc.id}
                className="panel-subtle p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 border border-white/5 hover:border-white/20 transition-all"
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono ${
                      inc.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/40' :
                      inc.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40' :
                      inc.severity === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' :
                      'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                    }`}>
                      {inc.severity}
                    </span>
                    <h3 className="text-sm font-bold text-white">{inc.title}</h3>
                    <span className="text-[10px] text-slate-500 font-mono">#{inc.id}</span>
                  </div>
                  <p className="text-xs text-slate-400">{inc.details}</p>
                  <div className="flex items-center gap-4 text-[10px] text-slate-500 font-mono mt-1">
                    <span>Source: <b className="text-cyan-400">{inc.source}</b></span>
                    <span>Target: <b className="text-slate-300">{inc.target}</b></span>
                    <span>Detected: {inc.time}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end md:self-center">
                  <span className={`px-2.5 py-1 rounded text-[10px] font-bold font-mono uppercase ${
                    inc.status === 'RESOLVED' ? 'bg-green-500/20 text-green-400' :
                    inc.status === 'ACTIVE' ? 'bg-red-500/20 text-red-400 animate-pulse' :
                    'bg-orange-500/20 text-orange-400'
                  }`}>
                    {inc.status}
                  </span>

                  {inc.status !== 'RESOLVED' && (
                    <button
                      onClick={() => handleResolve(inc.id)}
                      className="px-3 py-1 bg-green-600/80 hover:bg-green-600 text-white rounded text-xs font-semibold transition-colors"
                    >
                      Mitigate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}