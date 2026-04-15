import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import {
  Settings as SettingsIcon, Server, Palette, Globe, Shield, Database, Wifi,
  Save, RotateCw, Monitor,
} from 'lucide-react';

export function SettingsTab() {
  const serverUrl = useAppStore((s) => s.serverUrl);
  const setServerUrl = useAppStore((s) => s.setServerUrl);
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const serverStatus = useAppStore((s) => s.serverStatus);
  const setServerStatus = useAppStore((s) => s.setServerStatus);

  const [tempUrl, setTempUrl] = useState(serverUrl);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setServerUrl(tempUrl);
    setServerStatus({ url: tempUrl });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-2xl font-bold text-gradient">Settings</h2>
        <p className="text-white/40 text-sm mt-1">Configure Agent-OS connection and preferences</p>
      </div>

      {/* Server Connection */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Server size={14} /> Server Connection
        </h3>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-white/40 mb-1.5 block">Agent-OS Server URL</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={tempUrl}
                onChange={(e) => setTempUrl(e.target.value)}
                placeholder="http://localhost:8001"
                className="input-field flex-1"
              />
              <button onClick={handleSave} className="btn-primary flex items-center gap-2">
                <Save size={14} />
                {saved ? 'Saved!' : 'Save'}
              </button>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-white/5">
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-2.5 h-2.5 rounded-full ${serverStatus.online ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-white/60">{serverStatus.online ? 'Connected' : 'Disconnected'}</span>
            </div>
            <p className="text-xs text-white/30">
              Make sure Agent-OS is running: <span className="font-mono text-brand-400/60">python main.py --swarm</span>
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-white/5">
              <p className="text-[10px] text-white/30 uppercase tracking-wider">Main Server</p>
              <p className="text-sm font-mono text-white/60 mt-1">:8001</p>
            </div>
            <div className="p-3 rounded-xl bg-white/5">
              <p className="text-[10px] text-white/30 uppercase tracking-wider">Debug Dashboard</p>
              <p className="text-sm font-mono text-white/60 mt-1">:8002</p>
            </div>
          </div>
        </div>
      </div>

      {/* Appearance */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Palette size={14} /> Appearance
        </h3>
        <div className="flex gap-3">
          {(['dark', 'light'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`flex-1 p-4 rounded-xl border transition-all ${
                theme === t
                  ? 'border-brand-500/50 bg-brand-500/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20'
              }`}
            >
              <Monitor size={20} className={theme === t ? 'text-brand-400' : 'text-white/30'} />
              <p className={`text-sm mt-2 ${theme === t ? 'text-brand-400' : 'text-white/40'}`}>
                {t.charAt(0).toUpperCase() + t.slice(1)} Mode
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Swarm Config */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Shield size={14} /> Swarm Configuration
        </h3>
        <div className="space-y-3">
          {[
            { key: 'SWARM_ENABLED', value: 'true', desc: 'Enable/disable swarm search module' },
            { key: 'SWARM_MAX_WORKERS', value: '50', desc: 'Max parallel agents (1-50)' },
            { key: 'SWARM_ROUTER_THRESHOLD', value: '0.7', desc: 'Confidence threshold for router' },
            { key: 'SWARM_LLM_ENABLED', value: 'true', desc: 'Enable LLM fallback in router' },
            { key: 'SWARM_USE_BROWSER', value: 'false', desc: 'Use browser backend for search' },
            { key: 'SWARM_MAX_RESULTS', value: '10', desc: 'Max results per search' },
          ].map((env) => (
            <div key={env.key} className="flex items-center justify-between p-2.5 rounded-lg bg-white/5">
              <div>
                <p className="text-xs font-mono text-brand-400/60">{env.key}</p>
                <p className="text-[10px] text-white/20">{env.desc}</p>
              </div>
              <span className="text-xs text-white/30 font-mono">{env.value}</span>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-white/20 mt-3">
          Set these as environment variables when starting Agent-OS server
        </p>
      </div>

      {/* About */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Database size={14} /> About Agent-OS
        </h3>
        <div className="space-y-2 text-xs text-white/30">
          <p><span className="text-white/50 font-medium">Version:</span> 1.0.0</p>
          <p><span className="text-white/50 font-medium">Engine:</span> Patchright (stealth Chromium)</p>
          <p><span className="text-white/50 font-medium">Server:</span> aiohttp + Python 3.12</p>
          <p><span className="text-white/50 font-medium">Search:</span> curl_cffi + Bing/DDG/Google/SearXNG</p>
          <p><span className="text-white/50 font-medium">Swarm:</span> Up to 50 parallel agents</p>
          <p><span className="text-white/50 font-medium">Handoff:</span> Login/Signup detection + user takeover</p>
        </div>
      </div>
    </div>
  );
}
