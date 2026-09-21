'use client';
import { useCallback } from 'react';
import { Network, ShieldAlert } from 'lucide-react';
import { useCanvas } from '@/hooks/useCanvas';
import { useDashboard } from '@/contexts/DashboardContext';
import LiveTopologyMap, { checkIsAttackActive, getActiveAttackerIp } from '@/components/LiveTopologyMap';

export default function ThreatsPanel() {
  const { alerts, system, traffic, latestAlerts, liveAlerts, network } = useDashboard();
  const isAttackActive = checkIsAttackActive(traffic, latestAlerts, liveAlerts);
  const attackerIp = getActiveAttackerIp(latestAlerts, liveAlerts);

  const totalAlerts = alerts?.total_alerts || (system?.total_alerts ?? 0);

  // Bar chart of research attack classes
  const drawBarChart = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.clearRect(0, 0, w, h);
    
    const padL = 28;
    const padB = 28;
    const padT = 16;
    const chartW = w - padL - 10;
    const chartH = h - padT - padB;

    // Y-Axis Ticks (Packet Spike / Alert Intensity: 100, 75, 50, 25, 0)
    ctx.fillStyle = '#64748b';
    ctx.font = '8px monospace';
    ctx.textAlign = 'right';
    const yVals = [100, 75, 50, 25, 0];
    for (let i = 0; i < yVals.length; i++) {
      const y = padT + (i / (yVals.length - 1)) * chartH;
      ctx.fillText(yVals[i].toString(), padL - 6, y + 3);
      
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.moveTo(padL, y);
      ctx.lineTo(w - 10, y);
      ctx.stroke();
    }

    // 5 Kelas serangan penelitian (kunci UPPERCASE sesuai API by_attack_type)
    const byType = alerts?.by_attack_type || {};
    const shareOf = (keys: string[]) => {
      if (totalAlerts === 0) return 0;
      let sum = 0;
      for (const k of keys) sum += byType[k] || 0;
      return Math.round((sum / totalAlerts) * 100);
    };
    const attackKeys = ['PORT_SCAN', 'SYN_FLOOD', 'ICMP_FLOOD', 'MQTT_ANOMALY', 'MQTT_RATE_ABUSE', 'TRAFFIC_SPIKE'];

    const attackClasses = [
      { label: 'Port Scan', val: shareOf(['PORT_SCAN']), colTop: '#ef4444', colBot: '#7f1d1d' },
      { label: 'SYN Flood', val: shareOf(['SYN_FLOOD']), colTop: '#ea580c', colBot: '#7c2d12' },
      { label: 'ICMP Flood', val: shareOf(['ICMP_FLOOD']), colTop: '#eab308', colBot: '#713f12' },
      { label: 'MQTT Anom', val: shareOf(['MQTT_ANOMALY', 'MQTT_RATE_ABUSE']), colTop: '#a855f7', colBot: '#581c87' },
      { label: 'Spike DoS', val: shareOf(['TRAFFIC_SPIKE']), colTop: '#f43f5e', colBot: '#881337' },
      { label: 'Normal Base', val: totalAlerts === 0 ? 100 : Math.max(0, 100 - shareOf(attackKeys)), colTop: '#22c55e', colBot: '#14532d' }
    ];

    const barW = Math.max(8, (chartW / attackClasses.length) - 10);
    for (let i = 0; i < attackClasses.length; i++) {
      const b = attackClasses[i];
      const bh = (b.val / 100) * chartH;
      const x = padL + i * (barW + 10) + 4;
      const y = padT + chartH - bh;

      // Vertical 3D-like Gradient
      const grad = ctx.createLinearGradient(0, y, 0, y + bh);
      grad.addColorStop(0, b.colTop);
      grad.addColorStop(1, b.colBot);

      ctx.fillStyle = grad;
      ctx.fillRect(x, y, barW, bh);

      // Top cap highlight
      ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
      ctx.fillRect(x, y, barW, 2);
    }

    // X Axis Labels
    ctx.textAlign = 'center';
    ctx.fillStyle = '#94a3b8';
    ctx.font = '8px -apple-system, sans-serif';
    for (let i = 0; i < attackClasses.length; i++) {
      const x = padL + i * (barW + 10) + 4 + barW / 2;
      ctx.fillText(attackClasses[i].label, x, h - 8);
    }
  }, [totalAlerts, alerts]);

  const barCanvasRef = useCanvas(drawBarChart);

  return (
    <div className="panel p-4 flex-1 flex flex-col min-h-[350px] justify-between">
      {/* Title Bar */}
      <div className="flex justify-between items-center mb-2 shrink-0">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          <h3 className="text-xs font-bold text-white tracking-wide">
            Attack Classification & IoT Testbed Topology
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-cyan-400 font-mono bg-[#0b0e17] px-2.5 py-1 rounded border border-white/10">
          <Network className="w-3 h-3 text-cyan-400" />
          <span>Subnet: {network?.subnet || '—'}</span>
        </div>
      </div>

      {/* Dual Visuals: Research Attack Classifier + Interactive Real-time Topology */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 my-1">
        {/* Left: Attack Types Histogram */}
        <div className="flex flex-col relative w-full h-full min-h-[170px]">
          <span className="text-[10px] font-mono text-slate-400 mb-1">
            Attack Distribution (Suricata Rules & ML)
          </span>
          <div className="relative flex-1 w-full">
            <canvas ref={barCanvasRef} className="absolute inset-0 w-full h-full"></canvas>
          </div>
        </div>

        {/* Right: Live Interactive Real-Time Topology Map */}
        <div className="flex flex-col relative w-full h-full min-h-[170px]">
          <LiveTopologyMap />
        </div>
      </div>
      
      {/* Footer Indicators directly aligned with project specifications */}
      <div className="flex flex-wrap justify-between items-center border-t border-white/5 pt-2 text-[11px] font-semibold shrink-0 gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-white">
            <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]"></span>
            <span>3 ESP32 Nodes</span>
          </div>
          <div className="flex items-center gap-1.5 text-white">
            <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_6px_#22c55e]"></span>
            <span>Mosquitto (1883)</span>
          </div>
          <div className="flex items-center gap-1.5 text-white">
            <span className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_6px_#a855f7]"></span>
            <span>Isolation Forest</span>
          </div>
          <div className="flex items-center gap-1.5 text-white">
            <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_6px_#ef4444]"></span>
            <span>Suricata IDS</span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-slate-400 text-[10px] ml-auto font-mono">
          <span>Gateway: <b className="text-slate-200">{network?.gateway || '—'}</b></span>
          <span>Edge PC: <b className="text-green-400">{network?.local_ip || '—'}</b></span>
          <span>
            Lab Attacker:{' '}
            <b className={isAttackActive ? 'text-red-400 font-bold' : 'text-slate-400'}>
              {isAttackActive ? (attackerIp || '?') : 'Standby'} {isAttackActive ? '(AKTIF)' : ''}
            </b>
          </span>
        </div>
      </div>
    </div>
  );
}
