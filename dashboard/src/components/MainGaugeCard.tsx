'use client';
import { useCallback } from 'react';
import { useCanvas } from '@/hooks/useCanvas';
import { useDashboard } from '@/contexts/DashboardContext';

export default function MainGaugeCard() {
  const { system, alerts } = useDashboard();

  const calculateScore = () => {
    if (!system) return 20;
    const totalAlerts = system.total_alerts || 0;
    const critical = alerts?.by_severity?.['CRITICAL'] || 0;
    const high = alerts?.by_severity?.['HIGH'] || 0;
    const medium = alerts?.by_severity?.['MEDIUM'] || 0;
    const low = alerts?.by_severity?.['LOW'] || 0;

    // Skor risiko berbobot severity — 0 alert = LOW (hijau), serangan menaikkan skor.
    const score = Math.min(
      99,
      Math.round(20 + critical * 15 + high * 8 + medium * 4 + low * 1 + totalAlerts * 0.5)
    );
    return score;
  };

  const score = calculateScore();
  const isHigh = score >= 70;
  const isMedium = score >= 40 && score < 70;
  const riskLabel = isHigh ? 'HIGH' : isMedium ? 'MEDIUM' : 'LOW';
  const strokeColor = isHigh ? '#ef4444' : isMedium ? '#f97316' : '#22c55e';
  const glowColor = isHigh ? 'rgba(239, 68, 68, 0.85)' : isMedium ? 'rgba(249, 115, 22, 0.85)' : 'rgba(34, 197, 94, 0.85)';

  const draw = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    const cx = w / 2;
    const cy = h / 2 + 15;
    const r = Math.min(w, h) / 2.3;
    
    ctx.clearRect(0, 0, w, h);
    
    // Outer subtle tick ring
    ctx.save();
    ctx.translate(cx, cy);
    const numTicks = 60;
    for (let i = 0; i < numTicks; i++) {
      const angle = (Math.PI * 0.75) + (i / numTicks) * (Math.PI * 1.5);
      const isMajor = i % 5 === 0;
      const tickLen = isMajor ? 8 : 4;
      const startR = r + 16;
      const x1 = Math.cos(angle) * startR;
      const y1 = Math.sin(angle) * startR;
      const x2 = Math.cos(angle) * (startR + tickLen);
      const y2 = Math.sin(angle) * (startR + tickLen);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = isMajor ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.08)';
      ctx.lineWidth = isMajor ? 1.5 : 1;
      ctx.stroke();
    }
    ctx.restore();

    // Background track arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI * 0.75, Math.PI * 2.25);
    ctx.lineWidth = Math.max(14, w * 0.048);
    ctx.strokeStyle = '#141a29';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Inner guide circle
    ctx.beginPath();
    ctx.arc(cx, cy, r - 26, Math.PI * 0.75, Math.PI * 2.25);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.stroke();

    // Active Glowing Value Arc
    const startAngle = Math.PI * 0.75;
    const sweepRange = Math.PI * 1.5;
    const endAngle = startAngle + sweepRange * (score / 100);

    // Outer subtle glow arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.lineWidth = Math.max(20, w * 0.058);
    ctx.strokeStyle = strokeColor === '#ef4444' ? 'rgba(239, 68, 68, 0.22)' : strokeColor === '#f97316' ? 'rgba(249, 115, 22, 0.22)' : 'rgba(34, 197, 94, 0.22)';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Active Value Arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.lineWidth = Math.max(14, w * 0.048);
    ctx.strokeStyle = strokeColor;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Decorative Nodes on outer ring
    const drawNode = (angleRatio: number, color: string, radius: number) => {
      const angle = startAngle + sweepRange * angleRatio;
      const nx = cx + Math.cos(angle) * (r + 18);
      const ny = cy + Math.sin(angle) * (r + 18);
      
      ctx.beginPath();
      ctx.arc(nx, ny, radius + 2, 0, Math.PI * 2);
      ctx.fillStyle = color === '#ef4444' ? 'rgba(239, 68, 68, 0.3)' : color === '#06b6d4' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(234, 179, 8, 0.3)';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(nx, ny, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    };

    drawNode(0.08, '#06b6d4', 3.5); // Cyan node
    drawNode(0.25, '#ef4444', 4.5); // Red glowing node
    drawNode(0.85, '#eab308', 3);   // Yellow node
  }, [score, strokeColor]);

  const canvasRef = useCanvas(draw);

  return (
    <div className="col-span-1 md:col-span-3 panel p-4 relative flex flex-col items-center justify-center min-h-[260px] overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full"></canvas>
      
      <div className="relative z-10 flex flex-col items-center justify-center mt-6 select-none">
        <span 
          className={`text-6xl md:text-7xl font-extrabold tracking-tight transition-all duration-300 ${
            isHigh ? 'text-red-500 glow-red' : isMedium ? 'text-orange-500 glow-orange' : 'text-green-400'
          }`}
        >
          {score}
        </span>
        
        {/* Capsule Badge — warna mengikuti level risiko */}
        <div className={`mt-2 px-4 py-1 rounded-md border ${
          isHigh
            ? 'bg-red-950/70 border-red-500/40 shadow-[0_0_15px_rgba(239,68,68,0.4)]'
            : isMedium
              ? 'bg-orange-950/70 border-orange-500/40 shadow-[0_0_15px_rgba(249,115,22,0.4)]'
              : 'bg-green-950/70 border-green-500/40 shadow-[0_0_15px_rgba(34,197,94,0.4)]'
        }`}>
          <span className={`text-xs md:text-sm font-black tracking-widest uppercase ${
            isHigh ? 'text-red-400' : isMedium ? 'text-orange-400' : 'text-green-400'
          }`}>
            {riskLabel}
          </span>
        </div>
      </div>
    </div>
  );
}
