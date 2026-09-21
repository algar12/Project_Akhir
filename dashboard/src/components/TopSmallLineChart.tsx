'use client';
import { useCallback } from 'react';
import { useCanvas } from '@/hooks/useCanvas';
import { useDashboard } from '@/contexts/DashboardContext';
import { Radio } from 'lucide-react';

export default function TopSmallLineChart() {
  const { traffic } = useDashboard();

  const draw = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.clearRect(0, 0, w, h);
    
    // Background Grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i++) {
      const y = (i * h) / 5;
      ctx.beginPath();
      ctx.moveTo(10, y);
      ctx.lineTo(w - 10, y);
      ctx.stroke();
    }

    // Baseline Normal Zone Silhouette (zona aman bawah — referensi desain)
    ctx.save();
    ctx.fillStyle = 'rgba(34, 197, 94, 0.06)';
    ctx.fillRect(10, h * 0.55, w - 20, h * 0.35);
    ctx.restore();

    // Helper to draw smooth bezier lines
    const drawCurve = (color: string, points: number[], dashed = false) => {
      if (points.length === 0) return;
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      if (dashed) ctx.setLineDash([4, 4]); else ctx.setLineDash([]);

      const step = (w - 20) / (points.length - 1);
      const getCoord = (idx: number) => ({
        x: 10 + idx * step,
        y: h - 35 - (points[idx] * (h - 55)) / 100
      });

      const first = getCoord(0);
      ctx.moveTo(first.x, first.y);

      for (let i = 0; i < points.length - 1; i++) {
        const curr = getCoord(i);
        const next = getCoord(i + 1);
        const mx = (curr.x + next.x) / 2;
        ctx.quadraticCurveTo(curr.x, curr.y, mx, (curr.y + next.y) / 2);
      }
      const last = getCoord(points.length - 1);
      ctx.lineTo(last.x, last.y);
      ctx.stroke();
      ctx.setLineDash([]);
    };

    // ── BANGUN DATA NYATA ─────────────────────────────────────────────
    const N = 9;
    const times = traffic.map(r => new Date(r.timestamp).getTime());
    let min = times.length ? Math.min(...times) : Date.now();
    let max = times.length ? Math.max(...times) : min;
    if (max - min < 1000) max = min + 9000;
    const span = (max - min) / N;

    const buckets = Array.from({ length: N }, () => ({ pkts: 0, mqtt: 0, bytes: 0 }));
    traffic.forEach(r => {
      const t = new Date(r.timestamp).getTime();
      const idx = Math.min(N - 1, Math.floor((t - min) / span));
      buckets[idx].pkts += r.packet_count || 1;
      buckets[idx].mqtt += (r.source_port === 1883 || r.destination_port === 1883) ? 1 : 0;
      buckets[idx].bytes += r.bytes || 0;
    });

    const norm = (arr: number[]) => {
      const m = Math.max(...arr);
      return m > 0 ? arr.map(v => Math.round((v / m) * 100)) : arr.map(() => 0);
    };

    // 1. MQTT Ingestion Rate (Cyan) — paket port 1883 relatif
    drawCurve('#06b6d4', norm(buckets.map(b => b.mqtt)));
    // 2. Packet Baseline / Normal (Green) — packet rate relatif
    drawCurve('#22c55e', norm(buckets.map(b => b.pkts)));
    // 3. Spike / Volume (Orange) — bytes relatif
    drawCurve('#f97316', norm(buckets.map(b => b.bytes)));
    // 4. Anomaly Threshold Ceiling (Dashed Red Line) — referensi batas (70)
    drawCurve('#ef4444', [70, 70, 70, 70, 70, 70, 70, 70, 70], true);
  }, [traffic]);

  const canvasRef = useCanvas(draw);

  return (
    <div className="col-span-1 md:col-span-2 panel p-3 flex flex-col justify-between relative min-h-[260px] overflow-hidden">
      {/* Top status */}
      <div className="flex justify-between items-center z-10">
        <div className="flex items-center gap-1.5">
          <Radio className="w-3 h-3 text-cyan-400" />
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider font-semibold">
            IoT Traffic Baseline & Anomaly Threshold
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_6px_#22c55e]"></span>
          <span className="text-[9px] font-mono text-green-400">Normal</span>
        </div>
      </div>

      {/* Main Canvas */}
      <div className="relative flex-1 w-full my-1">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full"></canvas>
      </div>

      {/* Bottom X-axis and Legend */}
      <div className="z-10 border-t border-white/5 pt-1.5 flex flex-col gap-1.5 font-mono text-[9px]">
        {/* X Axis labels (time windows: 10s, 20s, 30s, 40s, 50s, 60s) */}
        <div className="flex justify-between text-slate-500 px-1">
          <span>-60s</span>
          <span>-45s</span>
          <span>-30s</span>
          <span>-15s</span>
          <span>Now</span>
        </div>

        {/* Legend */}
        <div className="flex justify-between items-center text-slate-400 px-1">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span> Baseline
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span> MQTT (1883)
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-orange-400"></span> Spike
            </span>
            <span className="flex items-center gap-1 text-red-400">
              <span className="w-1.5 h-0.5 bg-red-500"></span> Limit (70/m)
            </span>
          </div>
          <span className="font-bold text-green-400 text-[10px]">
            {traffic.length > 0 ? `${traffic.length} sampel live` : 'Menunggu data'}
          </span>
        </div>
      </div>
    </div>
  );
}
