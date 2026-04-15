import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import {
  UserCheck, Shield, Play, CheckCircle, XCircle, Clock, Globe, AlertTriangle,
  Pause, PlayCircle, Search, LogIn, UserPlus,
} from 'lucide-react';

export function HandoffTab() {
  const [urlInput, setUrlInput] = useState('');
  const handoffSessions = useAppStore((s) => s.handoffSessions);
  const addHandoffSession = useAppStore((s) => s.addHandoffSession);
  const updateHandoffSession = useAppStore((s) => s.updateHandoffSession);
  const activeHandoffId = useAppStore((s) => s.activeHandoffId);
  const setActiveHandoffId = useAppStore((s) => s.setActiveHandoffId);

  const handleStartHandoff = () => {
    if (!urlInput.trim()) return;
    let url = urlInput.trim();
    if (!url.startsWith('http')) url = 'https://' + url;

    const domain = new URL(url).hostname;
    const id = crypto.randomUUID();

    addHandoffSession({
      id,
      url,
      domain,
      status: 'active',
      startedAt: new Date().toISOString(),
      loginType: 'unknown',
    });
    setActiveHandoffId(id);
    setUrlInput('');
  };

  const handleComplete = (id: string) => {
    updateHandoffSession(id, { status: 'completed', completedAt: new Date().toISOString() });
    if (activeHandoffId === id) setActiveHandoffId(null);
  };

  const handleCancel = (id: string) => {
    updateHandoffSession(id, { status: 'cancelled', completedAt: new Date().toISOString() });
    if (activeHandoffId === id) setActiveHandoffId(null);
  };

  const activeSession = handoffSessions.find((s) => s.id === activeHandoffId);
  const completedSessions = handoffSessions.filter((s) => s.status !== 'active');
  const activeSessions = handoffSessions.filter((s) => s.status === 'active');

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold text-gradient">Login/Signup Handoff</h2>
        <p className="text-white/40 text-sm mt-1">
          AI detects login pages → pauses → you login securely → AI resumes
        </p>
      </div>

      {/* How it works */}
      <div className="card glow-brand">
        <h3 className="text-sm font-semibold text-brand-400 mb-3 flex items-center gap-2">
          <Shield size={14} /> How Handoff Works
        </h3>
        <div className="grid grid-cols-4 gap-4">
          {[
            { step: '1', icon: <Globe size={20} />, title: 'Navigate', desc: 'AI navigates to a website' },
            { step: '2', icon: <Pause size={20} />, title: 'Detect', desc: 'AI detects login/signup page' },
            { step: '3', icon: <UserCheck size={20} />, title: 'Handoff', desc: 'You take over & login' },
            { step: '4', icon: <PlayCircle size={20} />, title: 'Resume', desc: 'AI continues after login' },
          ].map((s) => (
            <div key={s.step} className="text-center">
              <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-2 text-brand-400">
                {s.icon}
              </div>
              <p className="text-xs font-semibold text-white/70">{s.title}</p>
              <p className="text-[10px] text-white/30 mt-0.5">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Start Handoff */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Start New Handoff</h3>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Globe size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleStartHandoff()}
              placeholder="Enter URL for login/signup (e.g., instagram.com, twitter.com)"
              className="input-field pl-9"
            />
          </div>
          <button onClick={handleStartHandoff} className="btn-primary flex items-center gap-2">
            <LogIn size={16} />
            Start Handoff
          </button>
        </div>
      </div>

      {/* Active Handoff */}
      {activeSession && (
        <div className="card border-yellow-500/30 glow-warning">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-yellow-500/10 flex items-center justify-center">
                <AlertTriangle size={20} className="text-yellow-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-yellow-400">Handoff Active — Your Turn!</p>
                <p className="text-xs text-white/40">{activeSession.domain}</p>
              </div>
            </div>
            <span className="badge-warning">Waiting for you</span>
          </div>

          <div className="p-4 rounded-xl bg-white/5 mb-4">
            <p className="text-sm text-white/60 mb-2">
              The AI has paused. Please complete the login on <span className="text-brand-400">{activeSession.domain}</span>.
            </p>
            <p className="text-xs text-white/30">
              URL: <span className="font-mono">{activeSession.url}</span>
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => handleComplete(activeSession.id)}
              className="btn-primary flex items-center gap-2 flex-1 justify-center"
            >
              <CheckCircle size={16} />
              I've Logged In — Resume AI
            </button>
            <button
              onClick={() => handleCancel(activeSession.id)}
              className="btn-danger flex items-center gap-2"
            >
              <XCircle size={16} />
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Quick Login Shortcuts */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Quick Login</h3>
        <div className="grid grid-cols-4 gap-3">
          {[
            { name: 'Google', url: 'https://accounts.google.com', icon: '🔵' },
            { name: 'GitHub', url: 'https://github.com/login', icon: '⚫' },
            { name: 'Instagram', url: 'https://instagram.com/accounts/login', icon: '📸' },
            { name: 'Twitter/X', url: 'https://x.com/i/flow/login', icon: '🐦' },
          ].map((site) => (
            <button
              key={site.name}
              onClick={() => setUrlInput(site.url)}
              className="p-3 rounded-xl bg-white/5 border border-white/5 hover:border-brand-500/30 transition-all text-center group"
            >
              <span className="text-2xl block mb-1">{site.icon}</span>
              <span className="text-xs text-white/50 group-hover:text-white/80 transition-colors">{site.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Session History */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">
          Session History ({handoffSessions.length})
        </h3>
        {handoffSessions.length === 0 ? (
          <div className="text-center py-8">
            <UserCheck size={40} className="text-white/10 mx-auto mb-3" />
            <p className="text-white/30 text-sm">No handoff sessions yet</p>
            <p className="text-white/20 text-xs mt-1">Start by entering a URL above</p>
          </div>
        ) : (
          <div className="space-y-2">
            {handoffSessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5">
                <div className="flex items-center gap-3">
                  {session.status === 'active' ? (
                    <AlertTriangle size={16} className="text-yellow-400" />
                  ) : session.status === 'completed' ? (
                    <CheckCircle size={16} className="text-green-400" />
                  ) : (
                    <XCircle size={16} className="text-red-400" />
                  )}
                  <div>
                    <p className="text-sm text-white/70">{session.domain}</p>
                    <p className="text-[10px] text-white/20 font-mono">{session.url}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={session.status === 'completed' ? 'badge-success' : session.status === 'active' ? 'badge-warning' : 'badge-error'}>
                    {session.status}
                  </span>
                  <span className="text-[10px] text-white/20">
                    {new Date(session.startedAt).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
