import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { PROVIDERS, detectProvider, validateKeyFormat } from '../../config/providers';
import { Key, Plus, Trash2, CheckCircle, XCircle, Eye, EyeOff, Zap } from 'lucide-react';

export function ApiKeysTab() {
  const [newKey, setNewKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState('');

  const apiKeys = useAppStore((s) => s.apiKeys);
  const addApiKey = useAppStore((s) => s.addApiKey);
  const removeApiKey = useAppStore((s) => s.removeApiKey);

  const detectedProvider = detectProvider(newKey);
  const validation = newKey ? (detectedProvider ? validateKeyFormat(newKey, detectedProvider) : { valid: false, message: 'Unknown provider key format' }) : null;

  const handleAdd = () => {
    if (!detectedProvider) {
      setError('Could not detect provider. Check your key format.');
      return;
    }
    if (validation && !validation.valid) {
      setError(validation.message);
      return;
    }
    addApiKey(newKey, selectedModel || detectedProvider.models[0]);
    setNewKey('');
    setSelectedModel('');
    setError('');
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold text-gradient">API Keys</h2>
        <p className="text-white/40 text-sm mt-1">Add any provider's API key — auto-detect & ready to use</p>
      </div>

      {/* Add Key Card */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Add New Key</h3>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-white/40 mb-1.5 block">API Key or Ollama URL</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={newKey}
                onChange={(e) => { setNewKey(e.target.value); setError(''); }}
                placeholder="sk-... / sk-ant-... / AIza... / xai-... / http://localhost:11434"
                className="input-field pr-20"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <button onClick={() => setShowKey(!showKey)} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                  {showKey ? <EyeOff size={14} className="text-white/40" /> : <Eye size={14} className="text-white/40" />}
                </button>
              </div>
            </div>
          </div>

          {/* Auto-detected Provider */}
          {detectedProvider && (
            <div className="flex items-center gap-3 p-3 rounded-xl bg-brand-500/10 border border-brand-500/20 animate-in">
              <div className="text-2xl">{detectedProvider.icon}</div>
              <div>
                <p className="text-sm font-semibold text-brand-400">{detectedProvider.name} Detected</p>
                <p className="text-xs text-white/40">Base: {detectedProvider.baseUrl}</p>
              </div>
              {validation?.valid && <CheckCircle size={18} className="text-green-400 ml-auto" />}
            </div>
          )}

          {!detectedProvider && newKey.length > 5 && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
              <XCircle size={16} className="text-red-400" />
              <p className="text-xs text-red-400">Unknown key format. Supported: OpenAI, Anthropic, Google, xAI, Mistral, DeepSeek, Ollama</p>
            </div>
          )}

          {/* Model Selection */}
          {detectedProvider && (
            <div>
              <label className="text-xs text-white/40 mb-1.5 block">Model</label>
              <select
                value={selectedModel || detectedProvider.models[0]}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="input-field appearance-none cursor-pointer"
              >
                {detectedProvider.models.map((m) => (
                  <option key={m} value={m} className="bg-surface-900">{m}</option>
                ))}
              </select>
            </div>
          )}

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button onClick={handleAdd} disabled={!detectedProvider || !validation?.valid} className="btn-primary flex items-center gap-2">
            <Plus size={16} />
            Add Key
          </button>
        </div>
      </div>

      {/* Supported Providers */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Supported Providers</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {PROVIDERS.map((p) => (
            <div key={p.id} className="p-3 rounded-xl bg-white/5 border border-white/5 hover:border-brand-500/20 transition-all">
              <div className="text-2xl mb-2">{p.icon}</div>
              <p className="text-sm font-medium text-white/80">{p.name}</p>
              <p className="text-[10px] text-white/30 font-mono mt-1">{p.keyPrefix}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Active Keys */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Active Keys ({apiKeys.length})</h3>
        {apiKeys.length === 0 ? (
          <div className="text-center py-8">
            <Key size={40} className="text-white/10 mx-auto mb-3" />
            <p className="text-white/30 text-sm">No API keys added yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {apiKeys.map((key) => {
              const provider = PROVIDERS.find((p) => p.id === key.provider);
              return (
                <div key={key.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/8 transition-all group">
                  <div className="flex items-center gap-3">
                    <div className="text-xl">{provider?.icon}</div>
                    <div>
                      <p className="text-sm font-medium text-white/80">{provider?.name}</p>
                      <p className="text-xs text-white/30 font-mono">{key.keyPreview}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-white/20">{key.model}</span>
                    <span className="badge-success">Active</span>
                    <button
                      onClick={() => removeApiKey(key.id)}
                      className="p-1.5 rounded-lg hover:bg-red-500/20 text-white/30 hover:text-red-400 transition-all opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
