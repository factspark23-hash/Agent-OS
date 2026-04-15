import type { TabId } from '../types';

const API_BASE = '/api';

async function request(endpoint: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// Server
export const checkHealth = () => request('/health');

// Browser
export const navigateTo = (url: string) =>
  request('/command', {
    method: 'POST',
    body: JSON.stringify({ command: 'navigate', url }),
  });

export const getScreenshot = () => request('/screenshot');

// Commands
export const sendCommand = (command: string, params?: Record<string, unknown>) =>
  request('/command', {
    method: 'POST',
    body: JSON.stringify({ command, ...params }),
  });

// Swarm
export const swarmSearch = (query: string, options?: Record<string, unknown>) =>
  request('/swarm/search', {
    method: 'POST',
    body: JSON.stringify({ query, ...options }),
  });

export const swarmRoute = (query: string) =>
  request('/swarm/route', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });

export const swarmHealth = () => request('/swarm/health');
export const swarmAgents = () => request('/swarm/agents');
export const swarmConfig = () => request('/swarm/config');

// Handoff
export const startHandoff = (url: string) =>
  request('/handoff/start', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });

export const getHandoffStatus = (id: string) => request(`/handoff/${id}`);

export const completeHandoff = (id: string) =>
  request(`/handoff/${id}/complete`, { method: 'POST' });

export const cancelHandoff = (id: string) =>
  request(`/handoff/${id}/cancel`, { method: 'POST' });

export const detectHandoff = (url: string) =>
  request('/handoff/detect', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });

export const getHandoffHistory = () => request('/handoff/history');
export const getHandoffStats = () => request('/handoff/stats');

// Sessions
export const getStatus = () => request('/status');

// WebSocket for real-time updates
export function createWebSocket(onMessage: (data: unknown) => void): WebSocket | null {
  try {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch { /* ignore non-JSON messages */ }
    };
    ws.onerror = () => { /* silent */ };
    return ws;
  } catch {
    return null;
  }
}
