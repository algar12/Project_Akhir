'use client';

import { useDashboard } from '@/contexts/DashboardContext';
import Header from '@/components/Header';
import MainGaugeCard from '@/components/MainGaugeCard';
import TopSmallLineChart from '@/components/TopSmallLineChart';
import StatCards from '@/components/StatCards';
import ThreatsPanel from '@/components/ThreatsPanel';
import MultiLineChart from '@/components/MultiLineChart';
import RiskLevelPanel from '@/components/RiskLevelPanel';
import BottomHealthPanels from '@/components/BottomHealthPanels';

// Sub-views
import NetworkView from '@/components/views/NetworkView';
import ThreatsView from '@/components/views/ThreatsView';
import IncidentsView from '@/components/views/IncidentsView';
import EndpointsView from '@/components/views/EndpointsView';
import ReportsView from '@/components/views/ReportsView';

export default function Dashboard() {
  const { activeTab } = useDashboard();

  return (
    <div className="p-2 md:p-3.5 flex flex-col min-h-screen bg-[#080a10] text-[#f1f5f9] select-none">
      {/* Top Navigation Bar with active functional controls */}
      <Header />

      {/* Dynamic View Rendering based on active navbar item */}
      {activeTab === 'Dashboard' && (
        <div className="flex-1 grid grid-cols-1 xl:grid-cols-12 gap-3">
          {/* LEFT COLUMN */}
          <div className="col-span-1 xl:col-span-7 flex flex-col gap-3">
            {/* Top Row: Main Gauge (3 cols) + Small Mountain Telemetry Chart (2 cols) */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 shrink-0">
              <MainGaugeCard />
              <TopSmallLineChart />
            </div>

            {/* Middle Row: 3 Stat Cards + vertical toolbar */}
            <StatCards />

            {/* Bottom Row: Threats by Type (3D Bar Chart + Dotted Cyber Map + Footer Pills) */}
            <ThreatsPanel />
          </div>

          {/* RIGHT COLUMN */}
          <div className="col-span-1 xl:col-span-5 flex flex-col gap-3">
            {/* Top: Luminous Multi-line Wave Chart */}
            <MultiLineChart />

            {/* Middle: Risk Level Progress Bars + Circular 98% Gauge */}
            <RiskLevelPanel />

            {/* Bottom: 2x2 Grid (Contagious Alerts, System Health Table & Bars, Risk Streams) */}
            <BottomHealthPanels />
          </div>
        </div>
      )}

      {activeTab === 'Network' && <NetworkView />}
      {activeTab === 'Threats' && <ThreatsView />}
      {activeTab === 'Incidents' && <IncidentsView />}
      {activeTab === 'Endpoints' && <EndpointsView />}
      {activeTab === 'Reports' && <ReportsView />}
    </div>
  );
}
