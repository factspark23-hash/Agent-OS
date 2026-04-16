import type { TabId } from '../types';
import { useAppStore } from '../store/useAppStore';

// Backend runs on port 8001 by default. In development, the Vite dev server
// proxies /api to http://localhost:8001. In production, nginx handles it.
const API_BASE = '/api';

function getAuthHeaders(): Record<string, string> {
  const store = useAppStore.getState();
  const headers: Record<string, string> = {};
  
  const apiKey = store.settings?.apiKey;
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  
  const token = store.settings?.authToken;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

/** Get the token string to embed in command body for legacy auth. */
function getCommandToken(): string {
  const store = useAppStore.getState();
  // Prefer API key for command body, then JWT token
  return store.settings?.apiKey || store.settings?.authToken || '';
}

async function request(endpoint: string, options?: RequestInit) {
  const authHeaders = getAuthHeaders();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 
      'Content-Type': 'application/json', 
      ...authHeaders,
      ...options?.headers 
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Send a command with auth token embedded in the body for legacy auth support. */
async function sendAuthenticatedCommand(command: string, params?: Record<string, unknown>) {
  const token = getCommandToken();
  return request('/command', {
    method: 'POST',
    body: JSON.stringify({ command, token, ...params }),
  });
}

// Server
export const checkHealth = () => request('/health');

// Browser
export const navigateTo = (url: string) =>
  sendAuthenticatedCommand('navigate', { url });

export const getScreenshot = () => request('/screenshot');

// Commands — uses authenticated command helper
export const sendCommand = (command: string, params?: Record<string, unknown>) =>
  sendAuthenticatedCommand(command, params);

// Auth
export const register = (email: string, username: string, password: string) =>
  request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, username, password }),
  });

export const login = (username: string, password: string) =>
  request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });

export const refreshToken = (refresh_token: string) =>
  request('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  });

export const createApiKey = (name: string, scopes?: string[]) =>
  request('/auth/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name, scopes }),
  });

export const listApiKeys = () => request('/auth/api-keys');

export const revokeApiKey = (keyPrefix: string) =>
  request(`/auth/api-keys/${keyPrefix}`, { method: 'DELETE' });

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
    
    // Send auth token as first message after connection
    ws.onopen = () => {
      const store = useAppStore.getState();
      const token = store.settings?.apiKey || store.settings?.authToken || '';
      
      ws.send(JSON.stringify({
        token: token,
      }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch { /* ignore non-JSON messages */ }
    };
    
    // Add auto-reconnect with exponential backoff
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    ws.onclose = () => {
      if (reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        reconnectAttempts++;
        setTimeout(() => {
          createWebSocket(onMessage);
        }, delay);
      }
    };
    
    ws.onerror = () => { /* silent */ };
    return ws;
  } catch {
    return null;
  }
}
