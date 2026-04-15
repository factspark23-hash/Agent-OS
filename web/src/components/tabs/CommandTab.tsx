import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { PROVIDERS, detectProvider } from '../../config/providers';
import {
  Send, Brain, User, Bot, Sparkles, Loader2, AlertCircle, ChevronDown, ChevronUp,
} from 'lucide-react';

export function CommandTab() {
  const [input, setInput] = useState('');
  const [showReasoning, setShowReasoning] = useState<Record<string, boolean>>({});
  const chatMessages = useAppStore((s) => s.chatMessages);
  const addChatMessage = useAppStore((s) => s.addChatMessage);
  const isProcessing = useAppStore((s) => s.isProcessing);
  const setIsProcessing = useAppStore((s) => s.setIsProcessing);
  const apiKeys = useAppStore((s) => s.apiKeys);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const query = input.trim();
    setInput('');

    addChatMessage({ role: 'user', content: query });

    // Check for special commands
    if (query.toLowerCase().startsWith('login ') || query.toLowerCase().startsWith('signup ')) {
      const url = query.split(' ').slice(1).join(' ');
      addChatMessage({
        role: 'system',
        content: `Login handoff initiated for: ${url}. Switch to Handoff tab to complete login.`,
        reasoning: `Detected login/signup command. URL: ${url}. The AI will pause and let you take over the browser for secure credential entry.`,
      });
      return;
    }

    // Simulate AI reasoning (in production, this would call the actual API)
    setIsProcessing(true);
    const activeKey = apiKeys[0];
    const providerName = activeKey ? PROVIDERS.find(p => p.id === activeKey.provider)?.name : 'System';

    addChatMessage({
      role: 'assistant',
      content: `Processing your request: "${query}"`,
      reasoning: `Analyzing query type... ${providerName ? `Using ${providerName} (${activeKey?.model})` : 'No provider configured'}. Routing through 3-tier system: Rule-based → LLM fallback → Conservative.`,
      provider: activeKey?.provider,
      model: activeKey?.model,
    });

    // Simulate processing delay
    setTimeout(() => {
      setIsProcessing(false);
      addChatMessage({
        role: 'assistant',
        content: `Command executed. For real server integration, make sure Agent-OS server is running on localhost:8001 with --swarm flag enabled.`,
        reasoning: `Query classified. Swarm agents dispatched. Results aggregated and deduplicated. Quality scoring applied.`,
        provider: activeKey?.provider,
        model: activeKey?.model,
      });
    }, 2000);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)] max-w-4xl">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gradient">Command Center</h2>
        <p className="text-white/40 text-sm mt-1">Send commands, search queries, or control the browser with AI</p>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-auto space-y-4 pb-4">
        {chatMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-2xl bg-brand-500/10 flex items-center justify-center mb-4 glow-brand">
              <Sparkles size={36} className="text-brand-400" />
            </div>
            <h3 className="text-lg font-semibold text-white/60 mb-2">Ready for commands</h3>
            <p className="text-white/30 text-sm max-w-md">
              Type a command like <span className="text-brand-400 font-mono">"search latest AI news"</span>,
              <span className="text-brand-400 font-mono"> "login instagram.com"</span>, or any query.
            </p>
            <div className="flex gap-2 mt-6">
              {['search AI trends', 'login google.com', 'navigate github.com'].map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => setInput(cmd)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-white/50 hover:text-white/80 hover:border-brand-500/30 transition-all"
                >
                  {cmd}
                </button>
              ))}
            </div>
          </div>
        )}

        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 animate-in ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.role !== 'user' && (
              <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                {msg.role === 'system' ? <AlertCircle size={16} className="text-yellow-400" /> : <Bot size={16} className="text-brand-400" />}
              </div>
            )}
            <div className={`max-w-[70%] ${msg.role === 'user' ? 'order-first' : ''}`}>
              <div className={`rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-brand-600/20 border border-brand-500/20'
                  : msg.role === 'system'
                  ? 'bg-yellow-500/10 border border-yellow-500/20'
                  : 'glass'
              }`}>
                <p className="text-sm text-white/90 whitespace-pre-wrap">{msg.content}</p>

                {/* Reasoning Toggle */}
                {msg.reasoning && (
                  <div className="mt-2 pt-2 border-t border-white/5">
                    <button
                      onClick={() => setShowReasoning((p) => ({ ...p, [msg.id]: !p[msg.id] }))}
                      className="flex items-center gap-1 text-xs text-brand-400/70 hover:text-brand-400 transition-colors"
                    >
                      <Brain size={12} />
                      <span>AI Reasoning</span>
                      {showReasoning[msg.id] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                    {showReasoning[msg.id] && (
                      <div className="mt-2 p-3 rounded-lg bg-white/5 text-xs text-white/50 leading-relaxed animate-in">
                        {msg.reasoning}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1 px-1">
                <span className="text-[10px] text-white/20">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                {msg.provider && <span className="text-[10px] text-brand-400/40">{msg.provider}</span>}
              </div>
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0 mt-1">
                <User size={16} className="text-white/50" />
              </div>
            )}
          </div>
        ))}

        {isProcessing && (
          <div className="flex gap-3 animate-in">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center">
              <Loader2 size={16} className="text-brand-400 animate-spin" />
            </div>
            <div className="glass rounded-2xl px-4 py-3">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 rounded-full bg-brand-400 typing-dot" />
                <div className="w-2 h-2 rounded-full bg-brand-400 typing-dot" />
                <div className="w-2 h-2 rounded-full bg-brand-400 typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-3 pt-4 border-t border-white/10">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a command or search query..."
            className="input-field pr-12"
            disabled={isProcessing}
          />
          {apiKeys.length > 0 && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <span className="text-[10px] text-brand-400/50 font-mono">{apiKeys[0].provider}</span>
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={!input.trim() || isProcessing}
          className="btn-primary flex items-center gap-2"
        >
          <Send size={16} />
          Send
        </button>
      </form>
    </div>
  );
}
