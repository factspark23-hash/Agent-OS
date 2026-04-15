import React, { useEffect, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { checkHealth } from '../../services/api';
import {
  Activity, Globe, Key, Zap, UserCheck, TrendingUp, Clock, Server,
} from 'lucide-react';

export function DashboardTab() {
  const serverStatus = useAppStore((s) => s.serverStatus);
  const setServerStatus = useAppStore((s) => s.setServerStatus);
  const apiKeys = useAppStore((s) => s.apiKeys);
  const handoffSessions = useAppStore((s) => s.handoffSessions);
  const swarmAgents = useAppStore((s) => s.swarmAgents);
  const chatMessages = useAppStore((s) => s.chatMessages);

  const [checking, setChecking] = useState(false);

  useEffect(() => {
    pingServer();
  }, []);

  const pingServer = async () => {
    setChecking(true);
    try {
      const res = await checkHealth();
      setServerStatus({
        online: true,
        version: res.version || '1.0.0',
        swarmEnabled: res.swarm_enabled,
        activeSessions: res.active_sessions,
      });
    } catch {
      setServerStatus({ online: false, url: serverStatus.url });
    }
    setChecking(false);
  };

  const stats = [
    {
      label: 'Server Status',
      value: serverStatus.online ? 'Online' : 'Offline',
      icon: <Server size={20} />,
      color: serverStatus.online ? 'text-green-400' : 'text-red-400',
      bg: serverStatus.online ? 'bg-green-500/10' : 'bg-red-500/10',
    },
    {
      label: 'API Keys',
      value: apiKeys.length.toString(),
      icon: <Key size={20} />,
      color: 'text-brand-400',
      bg: 'bg-brand-500/10',
    },
    {
      label: 'Swarm Agents',
      value: swarmAgents.length.toString(),
      icon: <Zap size={20} />,
      color: 'text-yellow-400',
      bg: 'bg-yellow-500/10',
    },
    {
      label: 'Handoffs',
      value: handoffSessions.length.toString(),
      icon: <UserCheck size={20} />,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
  ];

  const recentActivity = chatMessages.slice(-5).reverse().map((msg) => ({
    icon: msg.role === 'user' ? <Globe size={14} /> : <Activity size={14} />,
    text: msg.role === 'user' ? `Command: ${msg.content.slice(0, 60)}` : `AI: ${msg.content.slice(0, 60)}`,
    time: new Date(msg.timestamp).toLocaleTimeString(),
  }));

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gradient">Dashboard</h2>
          <p className="text-white/40 text-sm mt-1">Agent-OS system overview and health</p>
        </div>
        <button onClick={pingServer} disabled={checking} className="btn-secondary text-sm flex items-center gap-2">
          <TrendingUp size={14} className={checking ? 'animate-spin' : ''} />
          {checking ? 'Checking...' : 'Refresh'}
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="card">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/40 text-xs uppercase tracking-wider">{stat.label}</span>
              <div className={`w-8 h-8 rounded-lg ${stat.bg} flex items-center justify-center ${stat.color}`}>
                {stat.icon}
              </div>
            </div>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Active Provider & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Connected Providers */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Connected Providers</h3>
          {apiKeys.length === 0 ? (
            <div className="text-center py-6">
              <Key size={32} className="text-white/20 mx-auto mb-2" />
              <p className="text-white/30 text-sm">No API keys configured</p>
              <p className="text-white/20 text-xs mt-1">Go to API Keys tab to add one</p>
            </div>
          ) : (
            <div className="space-y-2">
              {apiKeys.map((key) => (
                <div key={key.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-white/5">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-sm text-white/80">{key.provider}</span>
                  </div>
                  <span className="text-xs text-white/30 font-mono">{key.keyPreview}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Recent Activity</h3>
          {recentActivity.length === 0 ? (
            <div className="text-center py-6">
              <Clock size={32} className="text-white/20 mx-auto mb-2" />
              <p className="text-white/30 text-sm">No recent activity</p>
              <p className="text-white/20 text-xs mt-1">Start by sending a command</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentActivity.map((act, i) => (
                <div key={i} className="flex items-center gap-3 py-2 px-3 rounded-lg bg-white/5">
                  <div className="text-white/30">{act.icon}</div>
                  <span className="text-sm text-white/60 flex-1 truncate">{act.text}</span>
                  <span className="text-xs text-white/20">{act.time}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Swarm Agent Status */}
      {serverStatus.swarmEnabled && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Swarm Agents</h3>
          <div className="grid grid-cols-5 gap-3">
            {swarmAgents.map((agent) => (
              <div key={agent.key} className="text-center p-3 rounded-xl bg-white/5">
                <div className={`w-3 h-3 rounded-full mx-auto mb-2 ${
                  agent.status === 'idle' ? 'bg-green-500' : agent.status === 'searching' ? 'bg-yellow-500 animate-pulse' : 'bg-white/20'
                }`} />
                <p className="text-xs text-white/70 font-medium">{agent.name}</p>
                <p className="text-[10px] text-white/30 mt-1">{agent.expertise}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
