'use client';
import { useCallback } from 'react';
import { useCanvas } from '@/hooks/useCanvas';
import { useDashboard } from '@/contexts/DashboardContext';
import { Cpu } from 'lucide-react';

export default function MultiLineChart() {
  const { traffic, predictions } = useDashboard();

  const drawMultiLine = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.clearRect(0, 0, w, h);
    
    const padL = 36;
    const padR = 20;
    const padB = 28;
    const padT = 18;
    const chartW = w - padL - padR;
    const chartH = h - padT - padB;

    // Horizontal Dotted Grid Lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.font = '8px monospace';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';

    // Metric Units (Intensitas Relatif: 100, 75, 50, 25, 0)
    const yTicks = [0, 25, 50, 75, 100];
    for (let i = 0; i < yTicks.length; i++) {
      const y = padT + (i / (yTicks.length - 1)) * chartH;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(w - padR, y);
      ctx.stroke();
      ctx.fillText(yTicks[yTicks.length - 1 - i].toString(), padL - 6, y + 3);
    }
    ctx.setLineDash([]); // Reset dash

    // ── BANGUN DATA NYATA ─────────────────────────────────────────────
    const N = 10;
    const times = traffic.map(r => new Date(r.timestamp).getTime());
    let min = times.length ? Math.min(...times) : Date.now();
    let max = times.length ? Math.max(...times) : min;
    if (max - min < 1000) max = min + 10000; // span minimal agar bucket stabil
    const span = (max - min) / N;

    const buckets = Array.from({ length: N }, () => ({ pkts: 0, syn: 0, mqtt: 0 }));
    traffic.forEach(r => {
      const t = new Date(r.timestamp).getTime();
      const idx = Math.min(N - 1, Math.floor((t - min) / span));
      buckets[idx].pkts += r.packet_count || 1;
      buckets[idx].syn += r.is_syn ? 1 : 0;
      buckets[idx].mqtt += (r.source_port === 1883 || r.destination_port === 1883) ? 1 : 0;
    });

    const norm = (arr: number[]) => {
      const m = Math.max(...arr);
      return m > 0 ? arr.map(v => Math.round((v / m) * 100)) : arr.map(() => 0);
    };

    const packetRate = norm(buckets.map(b => b.pkts));
    const synRate = norm(buckets.map(b => b.syn));
    const mqttRate = norm(buckets.map(b => b.mqtt));

    // IF Score dari predictions (10 sampel terakhir, normalisasi min-max)
    const preds = [...predictions].sort(
      (a, b) => new Date(a.time_bucket || a.timestamp).getTime() - new Date(b.time_bucket || b.timestamp).getTime()
    );
    const sampled = preds.length === 0
      ? []
      : Array.from({ length: N }, (_, i) => preds[Math.min(preds.length - 1, Math.floor((i * preds.length) / N))]);
    const scores = sampled.map(p => p.if_score);
    const sMin = scores.length ? Math.min(...scores) : 0;
    const sMax = scores.length ? Math.max(...scores) : 0;
    const ifCurve = scores.length
      ? scores.map(v => (sMax === sMin ? 50 : Math.round(((v - sMin) / (sMax - sMin)) * 100)))
      : [];

    const fmt = (t: number) => new Date(t).toLocaleTimeString([], { hour12: false });
    const xLabels = times.length ? Array.from({ length: N }, (_, i) => fmt(min + span * i)) : [];

    // ── GAMBAR KURVA ──────────────────────────────────────────────────
    const drawWave = (color: string, points: number[], fill = false, fillColor = '') => {
      if (points.length === 0) return;
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.2;

      const step = chartW / (points.length - 1);
      const getP = (idx: number) => ({
        x: padL + idx * step,
        y: padT + chartH - (points[idx] * chartH) / 100
      });

      const start = getP(0);
      ctx.moveTo(start.x, start.y);

      for (let i = 0; i < points.length - 1; i++) {
        const curr = getP(i);
        const next = getP(i + 1);
        const mx = (curr.x + next.x) / 2;
        ctx.quadraticCurveTo(curr.x, curr.y, mx, (curr.y + next.y) / 2);
      }
      const end = getP(points.length - 1);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();

      if (fill && fillColor) {
        ctx.lineTo(padL + chartW, padT + chartH);
        ctx.lineTo(padL, padT + chartH);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, padT, 0, padT + chartH);
        grad.addColorStop(0, fillColor);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fill();
      }
    };

    // 1. Packet Ingestion Rate (relatif) — Orange
    drawWave('#f97316', packetRate, true, 'rgba(249, 115, 22, 0.12)');
    // 2. MQTT Ratio (relatif) — Cyan
    drawWave('#06b6d4', mqttRate);
    // 3. TCP SYN Ratio (relatif) — Pink/Red
    drawWave('#ec4899', synRate);
    // 4. ML Isolation Forest Score (normalisasi) — Green
    drawWave('#22c55e', ifCurve);

    // X Axis Timestamps (bucket waktu nyata)
    ctx.textAlign = 'center';
    ctx.fillStyle = '#64748b';
    ctx.font = '8px monospace';
    const xStep = chartW / (xLabels.length - 1 || 1);
    for (let i = 0; i < xLabels.length; i++) {
      ctx.fillText(xLabels[i], padL + i * xStep, h - 8);
    }
  }, [traffic, predictions]);

  const canvasRef = useCanvas(drawMultiLine);

  return (
    <div className="panel p-3 h-52 md:h-56 shrink-0 relative flex flex-col justify-between overflow-hidden">
      <div className="flex justify-between items-center text-[10px] text-slate-400 z-10 px-1">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span>ML Feature Extraction & Traffic Velocity (10s Window)</span>
        </div>
        <div className="hidden sm:flex items-center gap-3 font-mono text-[9px]">
          <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-orange-500 inline-block"></span> Packet Rate</span>
          <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-cyan-400 inline-block"></span> MQTT Ratio</span>
          <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-pink-500 inline-block"></span> SYN Ratio</span>
          <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-green-500 inline-block"></span> IF-Score (ML)</span>
        </div>
      </div>

      <canvas ref={canvasRef} className="w-full h-full"></canvas>
    </div>
  );
}
