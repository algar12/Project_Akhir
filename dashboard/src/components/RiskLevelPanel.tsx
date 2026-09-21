'use client';
import { useCallback } from 'react';
import { useCanvas } from '@/hooks/useCanvas';
import { useDashboard } from '@/contexts/DashboardContext';
import { ArrowUpRight } from 'lucide-react';

export default function RiskLevelPanel() {
  const { alerts, system } = useDashboard();

  const totalAlerts = alerts?.total_alerts || (system?.total_alerts ?? 0);
  const criticalCount = alerts?.by_severity?.['CRITICAL'] ?? 0;
  const highCount = alerts?.by_severity?.['HIGH'] ?? 0;
  const mediumCount = alerts?.by_severity?.['MEDIUM'] ?? 0;
  const lowCount = alerts?.by_severity?.['LOW'] ?? 0;

  // Distribusi severity — persentase nyata (0% saat tidak ada alert)
  const criticalPct = totalAlerts > 0 ? Math.round((criticalCount / totalAlerts) * 100) : 0;
  const highPct = totalAlerts > 0 ? Math.round((highCount / totalAlerts) * 100) : 0;
  const lowPct = totalAlerts > 0
    ? Math.round(((lowCount + mediumCount) / totalAlerts) * 100)
    : 100;
  const isLowText = `${lowPct}%`;

  // Skor risiko berbobot severity — 0 alert = rendah, serangan menaikkan skor
  const gaugeScore = Math.min(
    99,
    Math.round(20 + criticalCount * 15 + highCount * 8 + mediumCount * 4 + lowCount * 1 + totalAlerts * 0.5)
  );
  const riskLevel = gaugeScore >= 70 ? 'HIGH' : gaugeScore >= 40 ? 'MEDIUM' : 'LOW';
  const riskColor = riskLevel === 'HIGH' ? '#ef4444' : riskLevel === 'MEDIUM' ? '#f97316' : '#22c55e';
  const riskGlow = riskLevel === 'HIGH'
    ? 'rgba(239, 68, 68, 0.85)'
    : riskLevel === 'MEDIUM'
      ? 'rgba(249, 115, 22, 0.85)'
      : 'rgba(34, 197, 94, 0.85)';

  const drawCircularGauge = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2 - 2;
    const r = Math.min(w, h) / 2.3;
    const lineWidth = Math.max(10, Math.min(16, w * 0.068));
    
    // Background Dark Track
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI * 0.75, Math.PI * 2.25);
    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = '#131926';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Vibrant Yellow -> Orange -> Coral Red Gradient Arc
    let grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
    grad.addColorStop(0, '#facc15');   // Golden Yellow
    grad.addColorStop(0.5, '#f97316'); // Radiant Orange
    grad.addColorStop(1, '#ef4444');   // Coral Red
    
    const startAngle = Math.PI * 0.75;
    const endAngle = startAngle + (Math.PI * 1.5) * (gaugeScore / 100);

    // Glow under-arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.lineWidth = lineWidth + 4;
    ctx.strokeStyle = 'rgba(249, 115, 22, 0.25)';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Foreground arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = grad;
    ctx.lineCap = 'round';
    ctx.stroke();
  }, [gaugeScore]);

  const smallGaugeRef = useCanvas(drawCircularGauge);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 shrink-0">
      {/* Left Sub-Panel: Threat Severity Distribution */}
      <div className="panel p-4 flex flex-col justify-between">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-1.5 font-bold text-xs text-white">
            <span>Risk Level</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="flex flex-col items-end">
            <span className="text-[11px] font-mono font-bold bg-[#0b0e17] px-2 py-0.5 rounded border border-white/10 text-white shadow-inner">
              {`${totalAlerts} ALERTS`}
            </span>
            <span className="text-[8px] text-red-400 font-semibold tracking-tight mt-0.5">Danger Level</span>
          </div>
        </div>

        {/* 3 Progress Bars */}
        <div className="flex flex-col gap-3 my-2">
          {/* Critical Bar */}
          <div className="flex items-center text-xs">
            <div className="w-24 h-2 bg-[#141a29] rounded-full overflow-hidden mr-3">
              <div className="bg-orange-500 h-full shadow-[0_0_8px_#f97316]" style={{ width: `${criticalPct}%` }}></div>
            </div>
            <div className="flex justify-between flex-1 text-[11px] font-medium text-slate-300">
              <span>Critical</span>
              <span className="text-slate-400">High</span>
              <span className="text-red-400 font-bold">{criticalPct}%</span>
            </div>
          </div>

          {/* High Bar */}
          <div className="flex items-center text-xs">
            <div className="w-24 h-2 bg-[#141a29] rounded-full overflow-hidden mr-3">
              <div className="bg-orange-600 h-full shadow-[0_0_8px_#ea580c]" style={{ width: `${highPct}%` }}></div>
            </div>
            <div className="flex justify-between flex-1 text-[11px] font-medium text-slate-300">
              <span>High</span>
              <span className="text-slate-400">Medium</span>
              <span className="text-orange-400 font-bold">{highPct}%</span>
            </div>
          </div>

          {/* Low Bar */}
          <div className="flex items-center text-xs">
            <div className="w-24 h-2 bg-[#141a29] rounded-full overflow-hidden mr-3">
              <div className="bg-green-500 h-full shadow-[0_0_8px_#22c55e]" style={{ width: `${lowPct}%` }}></div>
            </div>
            <div className="flex justify-between flex-1 text-[11px] font-medium text-slate-300">
              <span>Low</span>
              <span className="text-slate-400">Low</span>
              <span className="text-green-400 font-bold">{isLowText}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Right Sub-Panel: Circular Risk Level Gauge (Exact parity with Gambar yang ditempelkan.png) */}
      <div className="panel p-3 relative flex flex-col items-center justify-center min-h-[165px] overflow-hidden">
        {/* Top-left decorative cyan star */}
        <span className="absolute top-2.5 left-3 text-cyan-400 text-xs">✦</span>

        {/* Top-right subtle ML model tag */}
        <span className="absolute top-2.5 right-3 text-[9px] font-mono text-slate-500">
          ML Isolation
        </span>
        
        {/* Canvas Arc */}
        <canvas ref={smallGaugeRef} className="absolute inset-0 w-full h-full"></canvas>
        
        {/* Centered Typography: Cleanly proportioned without overlap */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none z-10 pt-1">
          <span className="text-4xl font-extrabold text-white tracking-tight leading-none drop-shadow-md">
            {gaugeScore}%
          </span>
          <span className="text-[9px] text-slate-400 uppercase tracking-[0.2em] font-bold mt-1.5 leading-none">
            Risk Level
          </span>
          <span className="text-[12px] glow-orange font-black tracking-wider mt-1.5 leading-none" style={{ color: riskColor, textShadow: `0 0 10px ${riskGlow}` }}>
            {riskLevel}
          </span>
        </div>
      </div>
    </div>
  );
}
