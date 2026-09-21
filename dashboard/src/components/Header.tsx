'use client';
import { useState, useEffect } from 'react';
import { useDashboard } from '@/contexts/DashboardContext';
import { 
  Search, Settings, User, Bell, Clock, ShieldCheck, 
  X, Check, Radio, Database, Cpu, Wifi, Key
} from 'lucide-react';

const NAV_ITEMS = ['Dashboard', 'Network', 'Threats', 'Incidents', 'Endpoints', 'Reports'];

export default function Header() {
  const { 
    activeTab, setActiveTab, 
    searchQuery, setSearchQuery, 
    liveAlerts, clearLiveAlerts, system, isConnected, 
    timeRangeHours, setTimeRangeHours,
    apiKey, setApiKey, devices, network 
  } = useDashboard();

  // Modals / Dropdowns state
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showTimeRange, setShowTimeRange] = useState(false);
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [tempApiKey, setTempApiKey] = useState(apiKey);

  // Global ⌘K / Ctrl+K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      } else if (e.key === 'Escape') {
        setShowCommandPalette(false);
        setShowNotifications(false);
        setShowTimeRange(false);
        setShowUserProfile(false);
        setShowSettings(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <nav className="flex items-center justify-between panel px-5 py-2.5 mb-3 shrink-0 flex-wrap gap-4 border border-white/10 rounded-xl relative z-30">
        {/* Left: Logo and Navigation Tabs */}
        <div className="flex items-center space-x-7">
          <div 
            onClick={() => setActiveTab('Dashboard')}
            className="flex items-center space-x-2.5 cursor-pointer group"
          >
            <div className="w-6 h-6 bg-cyan-500 rounded flex items-center justify-center shadow-[0_0_12px_rgba(6,182,212,0.6)] group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-4 h-4 text-black stroke-[2.5]" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-xs tracking-wider text-slate-100 uppercase whitespace-nowrap">
                Unified Network Guard
              </span>
              <span className="text-[8px] font-mono text-cyan-400 tracking-tight">
                Edge Computing IoT Platform
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="hidden lg:flex space-x-6 text-xs text-slate-400">
            {NAV_ITEMS.map(item => (
              <button 
                key={item}
                onClick={() => setActiveTab(item)}
                className={`transition-all font-medium py-1 ${
                  activeTab === item 
                    ? 'text-white font-semibold drop-shadow-[0_0_10px_rgba(255,255,255,0.6)] border-b-2 border-cyan-400' 
                    : 'hover:text-slate-200'
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Search, Notification, Time Range, User, Settings */}
        <div className="flex items-center space-x-3 ml-auto">
          {/* Search Trigger */}
          <div 
            onClick={() => setShowCommandPalette(true)}
            className="bg-[#0b0e17] border border-white/10 rounded-lg px-3 py-1.5 flex items-center text-xs text-slate-400 hover:border-cyan-500/50 transition-all shadow-inner cursor-pointer"
          >
            <Search className="w-3.5 h-3.5 mr-2 text-slate-500" />
            <span className="w-24 md:w-36 text-slate-500 text-xs truncate">
              {searchQuery ? searchQuery : 'Quick search...'}
            </span>
            {searchQuery ? (
              <button 
                onClick={(e) => { e.stopPropagation(); setSearchQuery(''); }} 
                className="text-slate-400 hover:text-white mr-1 text-xs"
              >
                ×
              </button>
            ) : null}
            <span className="text-slate-500 border border-white/10 px-1 rounded text-[9px] font-mono">⌘K</span>
          </div>

          {/* Bell Notifications */}
          <div className="relative">
            <button 
              onClick={() => {
                setShowNotifications(prev => !prev);
                setShowTimeRange(false);
                setShowUserProfile(false);
                setShowSettings(false);
              }}
              className={`p-1.5 rounded-md transition-colors relative ${showNotifications ? 'bg-white/15 text-white' : 'hover:bg-white/5 text-slate-400 hover:text-white'}`}
            >
              <Bell className="w-4 h-4" />
              {liveAlerts.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full shadow-[0_0_6px_#ef4444]"></span>
              )}
            </button>

            {/* Notifications Dropdown */}
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 panel p-3 border border-white/15 shadow-2xl z-50 rounded-xl animate-in fade-in zoom-in-95">
                <div className="flex justify-between items-center pb-2 border-b border-white/10 text-xs font-bold text-white">
                  <span>Security Notifications</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-cyan-400 font-normal">{liveAlerts.length} live alerts</span>
                    {liveAlerts.length > 0 && (
                      <button 
                        onClick={clearLiveAlerts}
                        className="text-[9px] text-slate-400 hover:text-red-400 underline transition-colors"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <div className="max-h-60 overflow-auto divide-y divide-white/5 my-2 text-xs">
                  {liveAlerts.length === 0 ? (
                    <div className="py-6 text-center text-slate-500 text-xs">
                      No new live alert packets received.
                    </div>
                  ) : (
                    liveAlerts.slice(0, 5).map((a, i) => (
                      <div key={i} className="py-2 flex flex-col gap-0.5">
                        <div className="flex justify-between font-bold text-[11px]">
                          <span className="text-red-400">{a.attack_type || 'Security Alert'}</span>
                          <span className="text-slate-500 text-[10px] font-mono">{a.source_ip}</span>
                        </div>
                        <p className="text-[11px] text-slate-400 truncate">{a.description || 'Suricata signature trigger'}</p>
                      </div>
                    ))
                  )}
                </div>
                <div className="pt-2 border-t border-white/10 text-center">
                  <button 
                    onClick={() => { setActiveTab('Threats'); setShowNotifications(false); }}
                    className="text-[11px] text-cyan-400 hover:underline font-medium"
                  >
                    View all threats feed →
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Clock: Time Filter */}
          <div className="relative">
            <button 
              onClick={() => {
                setShowTimeRange(prev => !prev);
                setShowNotifications(false);
                setShowUserProfile(false);
                setShowSettings(false);
              }}
              className={`p-1.5 rounded-md transition-colors ${showTimeRange ? 'bg-white/15 text-white' : 'hover:bg-white/5 text-slate-400 hover:text-white'}`}
            >
              <Clock className="w-4 h-4" />
            </button>

            {showTimeRange && (
              <div className="absolute right-0 mt-2 w-48 panel p-2 border border-white/15 shadow-2xl z-50 rounded-xl">
                <div className="text-[10px] uppercase tracking-wider font-mono text-slate-500 px-2 py-1">Time Range Window</div>
                <div className="space-y-1 text-xs">
                  {[
                    { label: 'Last 1 Hour', hours: 1 },
                    { label: 'Last 6 Hours', hours: 6 },
                    { label: 'Last 24 Hours', hours: 24 },
                    { label: 'Last 7 Days', hours: 168 },
                  ].map(t => (
                    <button
                      key={t.hours}
                      onClick={() => {
                        setTimeRangeHours(t.hours);
                        setShowTimeRange(false);
                      }}
                      className={`w-full text-left px-2.5 py-1.5 rounded flex justify-between items-center transition-colors ${
                        timeRangeHours === t.hours ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'hover:bg-white/5 text-slate-300'
                      }`}
                    >
                      <span>{t.label}</span>
                      {timeRangeHours === t.hours && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* User Profile */}
          <div className="relative">
            <button 
              onClick={() => {
                setShowUserProfile(prev => !prev);
                setShowNotifications(false);
                setShowTimeRange(false);
                setShowSettings(false);
              }}
              className={`p-1.5 rounded-md transition-colors ${showUserProfile ? 'bg-white/15 text-white' : 'hover:bg-white/5 text-slate-400 hover:text-white'}`}
            >
              <User className="w-4 h-4" />
            </button>

            {showUserProfile && (
              <div className="absolute right-0 mt-2 w-64 panel p-4 border border-white/15 shadow-2xl z-50 rounded-xl text-xs">
                <div className="flex items-center gap-3 pb-3 border-b border-white/10">
                  <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs border border-cyan-500/40">
                    AD
                  </div>
                  <div>
                    <h4 className="font-bold text-white">Security Admin</h4>
                    <span className="text-[10px] text-slate-500">Root Operator</span>
                  </div>
                </div>
                <div className="space-y-2 mt-3 text-[11px] text-slate-400">
                  <div className="flex justify-between">
                    <span>API Server:</span>
                    <span className="text-green-400 font-mono font-bold">Port 8000</span>
                  </div>
                  <div className="flex justify-between">
                    <span>WebSocket:</span>
                    <span className={isConnected ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                      {isConnected ? "Connected" : "Disconnected"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Database:</span>
                    <span className="text-slate-200 capitalize">{system?.database || 'Connected'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Settings */}
          <div className="relative">
            <button 
              onClick={() => {
                setShowSettings(prev => !prev);
                setShowNotifications(false);
                setShowTimeRange(false);
                setShowUserProfile(false);
              }}
              className={`p-1.5 rounded-md transition-colors ${showSettings ? 'bg-white/15 text-white' : 'hover:bg-white/5 text-slate-400 hover:text-white'}`}
            >
              <Settings className="w-4 h-4" />
            </button>

            {showSettings && (
              <div className="absolute right-0 mt-2 w-72 panel p-4 border border-white/15 shadow-2xl z-50 rounded-xl text-xs">
                <h4 className="font-bold text-white mb-2 flex items-center gap-2">
                  <Settings className="w-4 h-4 text-cyan-400" />
                  <span>Platform Settings</span>
                </h4>
                <div className="space-y-3 mt-3">
                  <div>
                    <label className="text-[10px] text-slate-400 font-medium block mb-1">API Key Header</label>
                    <div className="flex gap-2">
                      <input 
                        type="text"
                        value={tempApiKey}
                        onChange={(e) => setTempApiKey(e.target.value)}
                        className="bg-[#0b0e17] border border-white/10 rounded px-2 py-1 text-xs text-white font-mono flex-1 outline-none focus:border-cyan-500"
                      />
                      <button 
                        onClick={() => {
                          setApiKey(tempApiKey);
                          setShowSettings(false);
                        }}
                        className="px-2 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-bold"
                      >
                        Save
                      </button>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/10 space-y-1.5 text-[11px] text-slate-400">
                    <div className="flex justify-between items-center">
                      <span>Sniffer Interface</span>
                      <span className="font-mono text-cyan-400 font-bold">{network?.interface || '—'}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span>Subnet Mask</span>
                      <span className="font-mono text-slate-300">{network?.subnet || '—'}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Global Command Palette Modal (⌘K) */}
      {showCommandPalette && (
        <div 
          onClick={() => setShowCommandPalette(false)}
          className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-start justify-center pt-24 animate-in fade-in"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg panel p-4 border border-white/20 shadow-2xl rounded-2xl flex flex-col gap-3"
          >
            {/* Input */}
            <div className="flex items-center gap-2 border-b border-white/10 pb-3">
              <Search className="w-4 h-4 text-cyan-400" />
              <input
                type="text"
                autoFocus
                placeholder="Type a command, IP address, device, or view..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-sm text-white outline-none flex-1 placeholder-slate-500 font-medium"
              />
              <button 
                onClick={() => setShowCommandPalette(false)}
                className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Navigation Items */}
            <div className="space-y-1 text-xs">
              <div className="text-[10px] uppercase font-mono text-slate-500 px-2 py-1">Quick Jump to Views</div>
              {NAV_ITEMS.map(tab => (
                <button
                  key={tab}
                  onClick={() => {
                    setActiveTab(tab);
                    setShowCommandPalette(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/10 flex justify-between items-center text-slate-200 transition-colors"
                >
                  <span className="font-semibold">{tab} View</span>
                  <span className="text-[10px] text-slate-500 font-mono">Navigate →</span>
                </button>
              ))}
            </div>

            {/* Connected Devices in Search */}
            {devices.length > 0 && (
              <div className="space-y-1 text-xs border-t border-white/10 pt-2">
                <div className="text-[10px] uppercase font-mono text-slate-500 px-2 py-1">Managed Endpoints</div>
                {devices.slice(0, 3).map(d => (
                  <button
                    key={d.id}
                    onClick={() => {
                      setActiveTab('Endpoints');
                      setSearchQuery(d.ip_address);
                      setShowCommandPalette(false);
                    }}
                    className="w-full text-left px-3 py-1.5 rounded-lg hover:bg-white/10 flex justify-between items-center text-slate-300 font-mono text-[11px]"
                  >
                    <span>{d.device_name} ({d.ip_address})</span>
                    <span className="text-cyan-400">{d.device_type}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
