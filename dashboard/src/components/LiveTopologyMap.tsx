'use client';
import { useRef, useEffect, useState } from 'react';
import { useDashboard } from '@/contexts/DashboardContext';

type TopologyNode = {
  id: string;
  name: string;
  ip: string;
  type: 'router' | 'edge' | 'esp' | 'attacker';
  xRel: number;
  yRel: number;
  status: 'online' | 'offline' | 'registered';
  isOnline: boolean;
  activityLabel: string;
  sensorType?: string;
  lastSeen?: string;
};

// Safely parse timestamp to UTC milliseconds (supports ISO UTC, local, and timezone offset)
export function parseUtcTimestamp(dateStr?: string | null): number {
  if (!dateStr) return 0;
  if (dateStr.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(dateStr)) {
    const ms = new Date(dateStr).getTime();
    return isNaN(ms) ? 0 : ms;
  }
  // Try naive parsing
  const localMs = new Date(dateStr).getTime();
  const now = Date.now();
  if (!isNaN(localMs) && Math.abs(now - localMs) < 86400000) {
    return localMs;
  }
  const utcMs = new Date(dateStr + 'Z').getTime();
  if (!isNaN(utcMs) && Math.abs(now - utcMs) < 86400000) {
    return utcMs;
  }
  return !isNaN(localMs) ? localMs : (!isNaN(utcMs) ? utcMs : 0);
}

export function isHeartbeatFresh(lastSeen?: string | null, currentTime = Date.now(), maxAgeMs = 12000): boolean {
  if (!lastSeen) return false;
  const ms = parseUtcTimestamp(lastSeen);
  if (ms <= 0) return false;
  const diff = currentTime - ms;
  // Fresh if seen in the last maxAgeMs (with 5s tolerance for clock skew)
  return diff >= -5000 && diff < maxAgeMs;
}

export function checkIsAttackActive(
  traffic: any[] = [],
  latestAlerts: any[] = [],
  liveAlerts: any[] = [],
  currentTime = Date.now(),
  windowMs = 15000
): boolean {
  // 1. Live WebSocket alerts
  for (const a of liveAlerts) {
    const ts = a.timestamp || a.created_at;
    if (isHeartbeatFresh(ts, currentTime, windowMs)) return true;
  }

  // 2. Latest DB alerts
  for (const a of latestAlerts) {
    const ts = a.timestamp || a.created_at;
    if (isHeartbeatFresh(ts, currentTime, windowMs)) return true;
  }

  return false;
}

// IP pelaku serangan aktif (dari alert segar terbaru) — untuk node Attacker dinamis
export function getActiveAttackerIp(
  latestAlerts: any[] = [],
  liveAlerts: any[] = [],
  currentTime = Date.now(),
  windowMs = 15000
): string | null {
  const all = [...liveAlerts, ...latestAlerts]
    .filter(a => isHeartbeatFresh(a.timestamp || a.created_at, currentTime, windowMs));
  if (all.length === 0) return null;
  return all[0].source_ip || null;
}

const ESP_COORDINATES = [
  { xRel: 0.15, yRel: 0.28 }, // ESP32-01 Top Left
  { xRel: 0.15, yRel: 0.60 }, // ESP32-02 Mid Left
  { xRel: 0.22, yRel: 0.88 }, // ESP32-03 Bottom Left
  { xRel: 0.52, yRel: 0.88 }, // ESP32-04 Bottom Mid
  { xRel: 0.78, yRel: 0.82 }, // ESP32-05 Bottom Right
];

type Particle = {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  progress: number;
  speed: number;
  color: string;
  size: number;
};

export default function LiveTopologyMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { devices, traffic, liveAlerts, latestAlerts, network } = useDashboard();

  // Keep refs updated for 60fps canvas loop
  const devicesRef = useRef(devices);
  devicesRef.current = devices;
  const trafficRef = useRef(traffic);
  trafficRef.current = traffic;
  const latestAlertsRef = useRef(latestAlerts);
  latestAlertsRef.current = latestAlerts;
  const liveAlertsRef = useRef(liveAlerts);
  liveAlertsRef.current = liveAlerts;

  // Active attacks check: evaluates real-time freshness (15s window)
  const [hasActiveAttack, setHasActiveAttack] = useState(false);

  useEffect(() => {
    const updateAttackStatus = () => {
      const active = checkIsAttackActive(
        trafficRef.current,
        latestAlertsRef.current,
        liveAlertsRef.current,
        Date.now(),
        15000
      );
      setHasActiveAttack(active);
    };

    updateAttackStatus();
    const interval = setInterval(updateAttackStatus, 1000);
    return () => clearInterval(interval);
  }, [traffic, latestAlerts, liveAlerts]);
  
  // Real count of online IoT nodes (evaluated with 12s heartbeat freshness)
  const now = Date.now();
  const onlineDevicesCount = devices.filter(d => d.status === 'online' && isHeartbeatFresh(d.last_seen, now)).length;
  const totalDevicesCount = devices.length > 0 ? devices.length : 5;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;

    let animId: number;
    let width = 0;
    let height = 0;

    const handleResize = () => {
      const rect = parent.getBoundingClientRect();
      const targetW = Math.floor(rect.width);
      const targetH = Math.floor(rect.height);
      if (width !== targetW || height !== targetH) {
        width = targetW;
        height = targetH;
        canvas.width = targetW;
        canvas.height = targetH;
      }
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(parent);
    handleResize();

    const particles: Particle[] = [];

    // Animation Loop (Runs at 60 FPS without heavy shadowBlur)
    const render = (time: number) => {
      // Pause drawing if tab is hidden to save 100% CPU
      if (typeof document !== 'undefined' && document.hidden) {
        animId = requestAnimationFrame(render);
        return;
      }

      const ctx = canvas.getContext('2d');
      if (!ctx || width === 0 || height === 0) {
        animId = requestAnimationFrame(render);
        return;
      }

      ctx.clearRect(0, 0, width, height);
      const currentTime = Date.now();
      const currentAttackActive = checkIsAttackActive(
        trafficRef.current,
        latestAlertsRef.current,
        liveAlertsRef.current,
        currentTime,
        15000
      );

      // Read latest devices directly from ref
      const currentDevices = devicesRef.current;
      const rawDevices = currentDevices.length > 0 ? currentDevices : [
        { id: 1, device_name: 'ESP32-01', ip_address: '192.168.20.101', device_type: 'Climate (Temp/Hum)', status: 'registered', last_seen: '' },
        { id: 2, device_name: 'ESP32-02', ip_address: '192.168.20.102', device_type: 'Security (Motion/Light)', status: 'registered', last_seen: '' },
        { id: 3, device_name: 'ESP32-03', ip_address: '192.168.20.103', device_type: 'Energy (Power/Volt)', status: 'registered', last_seen: '' },
        { id: 4, device_name: 'ESP32-04', ip_address: '192.168.20.104', device_type: 'Air Quality (CO2)', status: 'registered', last_seen: '' },
        { id: 5, device_name: 'ESP32-05', ip_address: '192.168.20.105', device_type: 'Heartbeat / Gateway', status: 'registered', last_seen: '' },
      ];

      // Central Gateway Router — IP dinamis dari jaringan yang tersambung
      const routerNode: TopologyNode = {
        id: 'router',
        name: 'Router (Gateway)',
        ip: network?.gateway || '—',
        type: 'router',
        xRel: 0.46,
        yRel: 0.18,
        status: 'online',
        isOnline: true,
        activityLabel: 'AP & Gateway (Reachable)'
      };

      // Edge Computing Server — IP lokal mesin yang sedang menangkap paket
      const edgeNode: TopologyNode = {
        id: 'edge',
        name: 'Edge PC (Sniffer)',
        ip: network?.local_ip || '—',
        type: 'edge',
        xRel: 0.46,
        yRel: 0.52,
        status: 'online',
        isOnline: true,
        activityLabel: `Sniffer Active (${(trafficRef.current.length || 0).toLocaleString()} pkts)`
      };

      // Attacker Node — dinamis: IP pelaku dari alert segar terbaru
      const attackerIp = getActiveAttackerIp(
        latestAlertsRef.current,
        liveAlertsRef.current,
        currentTime,
        15000
      );
      const attackerNode: TopologyNode = {
        id: 'attacker',
        name: 'Lab Attacker',
        ip: currentAttackActive ? (attackerIp || '?') : '—',
        type: 'attacker',
        xRel: 0.85,
        yRel: 0.35,
        status: currentAttackActive ? 'online' : 'offline',
        isOnline: currentAttackActive,
        activityLabel: currentAttackActive ? '⚠️ Pen-test Active' : '○ Standby (Perimeter Aman)'
      };

      // Map real devices to topology nodes with HEARTBEAT FRESHNESS CHECK
      const espNodes: TopologyNode[] = rawDevices.slice(0, 5).map((dev, idx) => {
        const coords = ESP_COORDINATES[idx] || { xRel: 0.15, yRel: 0.3 + idx * 0.15 };
        const isFresh = isHeartbeatFresh(dev.last_seen, currentTime);
        const isDeviceTrulyOnline = dev.status === 'online' && isFresh;

        return {
          id: `esp-${dev.id}`,
          name: dev.device_name,
          ip: dev.ip_address,
          type: 'esp',
          xRel: coords.xRel,
          yRel: coords.yRel,
          status: isDeviceTrulyOnline ? 'online' : 'offline',
          isOnline: isDeviceTrulyOnline,
          sensorType: dev.device_type,
          lastSeen: dev.last_seen,
          activityLabel: isDeviceTrulyOnline ? '● Terhubung (MQTT 1883)' : '○ Belum Terhubung (Offline)'
        };
      });

      const allNodes = [routerNode, edgeNode, ...espNodes, attackerNode];
      const getNodePos = (n: TopologyNode) => ({ x: n.xRel * width, y: n.yRel * height });

      const routerPos = getNodePos(routerNode);
      const edgePos = getNodePos(edgeNode);
      const attackerPos = getNodePos(attackerNode);

      // ─── SPAWN PACKETS (ONLY FOR TRULY ONLINE NODES!) ────────────────────────
      // Limit total particles to 20 for maximum responsiveness
      if (particles.length < 20) {
        if (Math.random() < 0.08) {
          particles.push({
            fromX: routerPos.x, fromY: routerPos.y, toX: edgePos.x, toY: edgePos.y,
            progress: 0, speed: 0.015 + Math.random() * 0.008, color: '#22c55e', size: 3
          });
        }

        espNodes.forEach(esp => {
          if (esp.isOnline && Math.random() < 0.05) {
            const espPos = getNodePos(esp);
            particles.push({
              fromX: espPos.x, fromY: espPos.y, toX: routerPos.x, toY: routerPos.y,
              progress: 0, speed: 0.012 + Math.random() * 0.006, color: '#38bdf8', size: 2.5
            });
          }
        });

        if (currentAttackActive && Math.random() < 0.15) {
          particles.push({
            fromX: attackerPos.x, fromY: attackerPos.y, toX: routerPos.x, toY: routerPos.y,
            progress: 0, speed: 0.025 + Math.random() * 0.01, color: '#ef4444', size: 3.5
          });
        }
      }

      // ─── DRAW WIRES ──────────────────────────────────────────────────────────
      // Edge PC to Router
      ctx.beginPath();
      ctx.moveTo(routerPos.x, routerPos.y);
      ctx.lineTo(edgePos.x, edgePos.y);
      ctx.strokeStyle = 'rgba(34, 197, 94, 0.6)';
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // ESP32 wires to Router
      espNodes.forEach(esp => {
        const espPos = getNodePos(esp);
        ctx.beginPath();
        ctx.moveTo(espPos.x, espPos.y);
        ctx.lineTo(routerPos.x, routerPos.y);

        if (esp.isOnline) {
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 4]);
        } else {
          ctx.strokeStyle = 'rgba(100, 116, 139, 0.18)';
          ctx.lineWidth = 1;
          ctx.setLineDash([5, 5]);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Attacker wire
      ctx.beginPath();
      ctx.moveTo(attackerPos.x, attackerPos.y);
      ctx.lineTo(routerPos.x, routerPos.y);
      if (currentAttackActive) {
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.7)';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 3]);
      } else {
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.18)';
        ctx.lineWidth = 1;
        ctx.setLineDash([6, 6]);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // ─── DRAW TRAVELING PACKETS ──────────────────────────────────────────────
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.progress += p.speed;

        if (p.progress >= 1) {
          particles.splice(i, 1);
          continue;
        }

        const currX = p.fromX + (p.toX - p.fromX) * p.progress;
        const currY = p.fromY + (p.toY - p.fromY) * p.progress;

        // Clean, hardware-accelerated drawing without shadowBlur
        ctx.beginPath();
        ctx.arc(currX, currY, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
      }

      // ─── DRAW NODE GLYPHS ────────────────────────────────────────────────────
      for (const n of allNodes) {
        const pos = getNodePos(n);

        let strokeColor = '#475569';
        let coreColor = '#475569';
        let statusTextColor = '#64748b';
        let glowAlpha = 'rgba(71, 85, 105, 0.15)';

        if (n.type === 'router') {
          strokeColor = '#06b6d4';
          coreColor = '#06b6d4';
          statusTextColor = '#06b6d4';
          glowAlpha = 'rgba(6, 182, 212, 0.2)';
        } else if (n.type === 'edge') {
          strokeColor = '#22c55e';
          coreColor = '#22c55e';
          statusTextColor = '#22c55e';
          glowAlpha = 'rgba(34, 197, 94, 0.2)';
        } else if (n.type === 'esp') {
          if (n.isOnline) {
            strokeColor = '#38bdf8';
            coreColor = '#38bdf8';
            statusTextColor = '#22c55e';
            glowAlpha = 'rgba(56, 189, 248, 0.25)';
          } else {
            strokeColor = '#334155';
            coreColor = '#475569';
            statusTextColor = '#64748b';
            glowAlpha = 'transparent';
          }
        } else if (n.type === 'attacker') {
          if (currentAttackActive) {
            strokeColor = '#ef4444';
            coreColor = '#ef4444';
            statusTextColor = '#ef4444';
            glowAlpha = 'rgba(239, 68, 68, 0.25)';
          } else {
            strokeColor = '#334155';
            coreColor = '#475569';
            statusTextColor = '#64748b';
            glowAlpha = 'transparent';
          }
        }

        // Pulse ring for online nodes only
        if (n.isOnline) {
          const pulseR = 8 + (Math.sin(time / 250) + 1) * 3;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, pulseR + 4, 0, Math.PI * 2);
          ctx.fillStyle = n.type === 'attacker' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(56, 189, 248, 0.12)';
          ctx.fill();

          // Outer Glow Circle (crisp & zero CPU cost vs shadowBlur)
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, 14, 0, Math.PI * 2);
          ctx.fillStyle = glowAlpha;
          ctx.fill();
        }

        // Outer Ring
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 9, 0, Math.PI * 2);
        ctx.fillStyle = '#0b0f19';
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();

        // Inner Core Dot
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = coreColor;
        ctx.fill();

        // Node Title (Above)
        ctx.font = 'bold 8.5px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = n.isOnline ? '#f1f5f9' : '#94a3b8';
        ctx.fillText(n.name, pos.x, pos.y - 14);

        // IP Address (Below line 1)
        ctx.font = '8px monospace';
        ctx.fillStyle = '#64748b';
        ctx.fillText(n.ip, pos.x, pos.y + 14);

        // Honest Real Status Indicator (Below line 2)
        ctx.font = '7.5px -apple-system, sans-serif';
        ctx.fillStyle = statusTextColor;
        ctx.fillText(
          n.isOnline 
            ? (n.type === 'esp' ? '● ONLINE' : n.type === 'router' ? '● UP' : '● AKTIF')
            : (n.type === 'attacker' ? '○ STANDBY' : '○ OFFLINE'),
          pos.x, pos.y + 23
        );
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <div className="relative w-full h-full bg-[#090d16]/70 rounded-lg border border-white/5 overflow-hidden flex flex-col">
      {/* Live Header Status bar */}
      <div className="flex justify-between items-center px-3 py-1.5 border-b border-white/5 bg-[#0b0e17]/80 text-[10px] font-mono z-10">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 relative">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${onlineDevicesCount > 0 ? 'bg-green-400' : 'bg-amber-400'} opacity-75`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${onlineDevicesCount > 0 ? 'bg-green-500' : 'bg-amber-500'}`}></span>
          </span>
          <span className="text-slate-300 font-semibold">Live IoT Node Detection</span>
        </div>

        <div className="flex items-center gap-3 text-[9px]">
          <span className={onlineDevicesCount > 0 ? 'text-green-400 font-bold' : 'text-slate-400'}>
            ● {onlineDevicesCount}/{totalDevicesCount} ESP32 Terhubung
          </span>
          <span className="text-cyan-400">
            ● Edge PC Online
          </span>
          <span className={hasActiveAttack ? 'text-red-400 font-bold' : 'text-slate-500'}>
            {hasActiveAttack ? '⚠️ Serangan Aktif' : '🛡 0 Penyusup'}
          </span>
        </div>
      </div>

      {/* Canvas with real-time state */}
      <div className="relative flex-1 w-full">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full"></canvas>
      </div>

      {/* Honest Bottom Notice */}
      <div className="px-3 py-1 bg-[#0b0e17]/90 border-t border-white/5 flex justify-between text-[8.5px] font-mono text-slate-400 z-10">
        <span>Subnet: <b className="text-cyan-300">{network?.subnet || '—'}</b></span>
        <span>
          Status: {onlineDevicesCount > 0 
            ? <b className="text-green-400">{onlineDevicesCount} Node Aktif</b> 
            : <b className="text-amber-400">Menunggu Koneksi ESP32 (Hardware Offline)</b>
          }
        </span>
        <span>Sniffer: <b className="text-green-400">{network?.interface || '—'} Active</b></span>
      </div>
    </div>
  );
}
