'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import dynamic from 'next/dynamic';
import type { ChatMessage, RecommendationItem, SSEPhase, GraphData, UserProfile } from '@/types';
import { streamRecommendationSSE, fetchGraphData, fetchProfile, addToWatchlist as apiAddToWatchlist, removeFromWatchlist as apiRemoveFromWatchlist, exportConversation } from '@/lib/api';
import MovieCard from '@/components/MovieCard';
import PhaseIndicator from '@/components/PhaseIndicator';
import ProfileSidebar from '@/components/ProfileSidebar';

const ForceGraph = dynamic(() => import('@/components/ForceGraph'), { ssr: false });

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<SSEPhase | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [showGraph, setShowGraph] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const [allRecommendations, setAllRecommendations] = useState<RecommendationItem[]>([]);
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [totalMovies, setTotalMovies] = useState(0);

  // New states: watchlist, export, filters
  const [watchlist, setWatchlist] = useState<RecommendationItem[]>([]);
  const [showWatchlist, setShowWatchlist] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check API health on mount
  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((data) => setIsConnected(data.status === 'ok' || data.status === 'degraded'))
      .catch(() => setIsConnected(false));
  }, []);

  // Load graph data when session changes
  const loadGraph = useCallback(async (sid: string, recs: RecommendationItem[]) => {
    try {
      const graph = await fetchGraphData(sid, recs);
      setGraphData(graph);
    } catch (err) {
      console.error('Failed to load graph:', err);
    }
  }, []);

  // Load profile
  const loadProfile = useCallback(async (sid: string) => {
    try {
      const data = await fetchProfile(sid);
      if (data.profile) setProfile(data.profile);
    } catch (err) {
      console.error('Failed to load profile:', err);
    }
  }, []);

  // Watchlist handlers
  const handleToggleWatchlist = useCallback(async (movie: RecommendationItem) => {
    const inList = watchlist.some((m) => m.tmdb_id === movie.tmdb_id);
    if (inList) {
      setWatchlist((prev) => prev.filter((m) => m.tmdb_id !== movie.tmdb_id));
      if (sessionId) {
        try { await apiRemoveFromWatchlist(sessionId, movie.tmdb_id); } catch {}
      }
    } else {
      setWatchlist((prev) => [...prev, movie]);
      if (sessionId) {
        try { await apiAddToWatchlist(sessionId, movie); } catch {}
      }
    }
  }, [watchlist, sessionId]);

  // Export handler
  const handleExport = useCallback(async (format: 'json' | 'markdown') => {
    if (!sessionId) return;
    setExportLoading(true);
    try {
      const data = await exportConversation(sessionId, format);
      const blob = new Blob(
        [format === 'json' ? JSON.stringify(data, null, 2) : (data.content || JSON.stringify(data))],
        { type: format === 'json' ? 'application/json' : 'text/markdown' }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cinematch-${sessionId.slice(0, 8)}.${format === 'json' ? 'json' : 'md'}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExportLoading(false);
    }
  }, [sessionId]);

  // Send message
  const handleSend = async () => {
    const query = input.trim();
    if (!query || isLoading) return;

    setInput('');
    setIsLoading(true);
    setCurrentPhase(null);

    // Add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Add placeholder assistant message
    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      recommendations: [],
      timestamp: new Date(),
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);

    let streamedRecs: RecommendationItem[] = [];

    await streamRecommendationSSE(query, sessionId, {
      onStatus: (phase) => setCurrentPhase(phase),
      onRecommendations: (recs) => {
        streamedRecs = recs;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, recommendations: recs } : m))
        );
      },
      onToken: (token) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + token } : m))
        );
      },
      onNarrativeReplace: (text) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: text } : m))
        );
      },
      onDone: (sid) => {
        setSessionId(sid);
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m))
        );
        setCurrentPhase(null);
        setIsLoading(false);
        setAllRecommendations((prev) => [...prev, ...streamedRecs]);
        setTotalMovies((prev) => prev + streamedRecs.length);
        if (sid) {
          loadGraph(sid, [...allRecommendations, ...streamedRecs]);
          loadProfile(sid);
        }
      },
      onError: (error) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `❌ Error: ${error}`, isStreaming: false }
              : m
          )
        );
        setCurrentPhase(null);
        setIsLoading(false);
      },
    });
  };

  // Handle Enter key
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-cinema-bg">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="relative z-20 flex items-center justify-between px-6 py-3 glass-panel border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="relative">
            <span className="text-2xl">🎬</span>
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-cinema-accent animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-cinema-accent to-amber-300 bg-clip-text text-transparent">
              CineMatch AI
            </h1>
            <p className="text-[10px] text-cinema-textMuted -mt-0.5 hidden sm:block">Motor de Recomendación Inteligente</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Stats pill */}
          {totalMovies > 0 && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-cinema-accent/10 border border-cinema-accent/20 text-xs text-cinema-accent">
              <span>🎬</span> {totalMovies} películas recomendadas
            </div>
          )}

          {/* Watchlist toggle */}
          <button
            onClick={() => setShowWatchlist(!showWatchlist)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all duration-300 ${
              showWatchlist
                ? 'bg-gradient-to-r from-green-500 to-emerald-400 text-cinema-bg shadow-lg shadow-green-500/20'
                : 'glass-card text-cinema-textMuted hover:text-white hover:border-green-400/30'
            }`}
          >
            <span className="text-sm">🔖</span>
            {watchlist.length > 0 && (
              <span className="text-xs">{watchlist.length}</span>
            )}
            <span className="hidden sm:inline">Watchlist</span>
          </button>

          {/* Export dropdown */}
          {sessionId && (
            <div className="relative group/export">
              <button
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium glass-card text-cinema-textMuted hover:text-white transition-all duration-300"
                disabled={exportLoading}
              >
                {exportLoading ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <span className="text-sm">📥</span>
                )}
                <span className="hidden sm:inline">Exportar</span>
              </button>
              <div className="absolute right-0 top-full mt-1 hidden group-hover/export:flex flex-col bg-cinema-card border border-white/10 rounded-xl shadow-xl overflow-hidden z-30 min-w-[140px]">
                <button onClick={() => handleExport('markdown')} className="px-4 py-2 text-xs text-cinema-textMuted hover:text-white hover:bg-white/5 text-left transition-colors">
                  📝 Markdown
                </button>
                <button onClick={() => handleExport('json')} className="px-4 py-2 text-xs text-cinema-textMuted hover:text-white hover:bg-white/5 text-left transition-colors">
                  📋 JSON
                </button>
              </div>
            </div>
          )}

          {/* Graph toggle */}
          <button
            onClick={() => setShowGraph(!showGraph)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all duration-300 ${
              showGraph
                ? 'bg-gradient-to-r from-cinema-accent to-amber-400 text-cinema-bg shadow-lg shadow-amber-500/20'
                : 'glass-card text-cinema-textMuted hover:text-white hover:border-cinema-accent/30'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span className="hidden sm:inline">Mapa</span>
          </button>

          {/* Profile toggle */}
          <button
            onClick={() => setShowProfile(!showProfile)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all duration-300 ${
              showProfile
                ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/20'
                : 'glass-card text-cinema-textMuted hover:text-white hover:border-purple-400/30'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span className="hidden sm:inline">Perfil</span>
          </button>

          {/* Connection status */}
          <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg" title={isConnected ? 'Conectado' : 'Desconectado'}>
            <div className={`w-2 h-2 rounded-full transition-colors ${
              isConnected === null ? 'bg-cinema-textMuted/50' : isConnected ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-red-400 shadow-sm shadow-red-400/50'
            }`} />
          </div>
        </div>
      </header>

      {/* ── Main Content ────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className={`flex flex-col flex-1 transition-all duration-500 ${showGraph ? 'lg:w-1/2' : 'w-full'}`}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scrollbar-thin">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center px-4 animate-fade-in">
                {/* Hero animation */}
                <div className="relative mb-8">
                  <div className="text-7xl animate-float">🎬</div>
                  <div className="absolute -inset-8 bg-gradient-to-r from-cinema-accent/20 via-purple-500/10 to-pink-500/20 rounded-full blur-3xl animate-pulse-slow" />
                </div>

                <h2 className="text-3xl font-bold mb-3">
                  <span className="bg-gradient-to-r from-white via-cinema-text to-cinema-textMuted bg-clip-text text-transparent">
                    ¿Qué película buscas?
                  </span>
                </h2>
                <p className="text-cinema-textMuted max-w-md mb-10 leading-relaxed text-sm">
                  Cuéntame lo que te apetece ver. Puedo encontrar joyas basándome en géneros,
                  emociones, épocas, directores o simplemente una vibra.
                </p>

                {/* Suggestion chips */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-2xl w-full">
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={s.text}
                      onClick={() => { setInput(s.text); inputRef.current?.focus(); }}
                      className="group text-left px-4 py-3.5 rounded-2xl glass-card
                                 text-cinema-textMuted text-sm hover:text-white
                                 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg
                                 animate-slide-up"
                      style={{ animationDelay: `${i * 80}ms` }}
                    >
                      <span className="text-lg mr-2">{s.icon}</span>
                      <span className="group-hover:text-white transition-colors">{s.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
              >
                {msg.role === 'user' ? (
                  <div className="max-w-[80%] lg:max-w-[60%]">
                    <div className="bg-gradient-to-br from-cinema-accent/20 to-amber-500/10 border border-cinema-accent/20 rounded-2xl rounded-br-md px-5 py-3 backdrop-blur-sm">
                      <p className="text-white leading-relaxed">{msg.content}</p>
                    </div>
                    <p className="text-[10px] text-cinema-textMuted/40 text-right mt-1 pr-2">
                      {msg.timestamp.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                ) : (
                  <div className="max-w-[90%] lg:max-w-[80%] w-full">
                    {/* Movie cards */}
                    {msg.recommendations && msg.recommendations.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
                        {msg.recommendations.map((movie, idx) => (
                          <MovieCard
                            key={movie.tmdb_id}
                            movie={movie}
                            index={idx}
                            onAddToWatchlist={handleToggleWatchlist}
                            isInWatchlist={watchlist.some((m) => m.tmdb_id === movie.tmdb_id)}
                          />
                        ))}
                      </div>
                    )}

                    {/* Narrative */}
                    {msg.content && (
                      <div className="glass-panel rounded-2xl px-6 py-5">
                        <div className={`narrative-text text-cinema-text leading-relaxed ${msg.isStreaming ? 'typing-cursor' : ''}`}>
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Phase indicator */}
            {isLoading && currentPhase && (
              <div className="flex justify-start animate-fade-in">
                <PhaseIndicator phase={currentPhase} />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ── Input Area ──────────────────────────────── */}
          <div className="relative z-10 border-t border-white/5 glass-panel p-4">
            <div className="max-w-4xl mx-auto">
              <div className="flex gap-3 items-end">
                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Describe la película que buscas..."
                    rows={1}
                    className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-3.5 pr-12
                               text-white placeholder:text-cinema-textMuted/40 resize-none
                               focus:outline-none focus:border-cinema-accent/40 focus:ring-2 focus:ring-cinema-accent/10
                               transition-all duration-300 text-sm leading-relaxed"
                    disabled={isLoading}
                    style={{ minHeight: '48px', maxHeight: '120px' }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      target.style.height = '48px';
                      target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                    }}
                  />
                </div>
                <button
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                  className="flex-shrink-0 w-12 h-12 flex items-center justify-center
                             bg-gradient-to-r from-cinema-accent to-amber-400 text-cinema-bg
                             font-bold rounded-2xl shadow-lg shadow-amber-500/20
                             hover:shadow-amber-500/40 hover:scale-105
                             transition-all duration-300 disabled:opacity-30
                             disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100
                             active:scale-95"
                >
                  {isLoading ? (
                    <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="text-[10px] text-cinema-textMuted/30 text-center mt-2">
                Pulsa Enter para enviar · Shift+Enter para nueva línea
              </p>
            </div>
          </div>
        </div>

        {/* ── Graph Panel ───────────────────────────────── */}
        {showGraph && (
          <div className="hidden lg:flex flex-col w-1/2 border-l border-white/5 bg-cinema-bg/50 animate-fade-in">
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 glass-panel">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cinema-accent/20 to-amber-400/10 flex items-center justify-center">
                  <svg className="w-4 h-4 text-cinema-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                </div>
                <div>
                  <h2 className="font-semibold text-white text-sm">Mapa Conceptual</h2>
                  {graphData && (
                    <p className="text-[10px] text-cinema-textMuted">
                      {graphData.stats.total_nodes} nodos · {graphData.stats.total_links} conexiones
                    </p>
                  )}
                </div>
              </div>
              <button onClick={() => setShowGraph(false)} className="text-cinema-textMuted hover:text-white transition-colors p-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 p-4 overflow-hidden">
              {graphData && graphData.nodes.length > 0 ? (
                <ForceGraph
                  data={graphData}
                  width={600}
                  height={500}
                  onNodeClick={(node) => {
                    if (node.type === 'genre' || node.type === 'keyword' || node.type === 'mood') {
                      setInput(`Quiero algo de ${node.label}`);
                      inputRef.current?.focus();
                    }
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-cinema-textMuted">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] flex items-center justify-center mb-4 border border-white/5">
                    <svg className="w-8 h-8 text-cinema-textMuted/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium">El mapa se construirá con tus búsquedas</p>
                  <p className="text-xs mt-1 text-cinema-textMuted/50">Haz tu primera consulta para empezar</p>
                </div>
              )}
            </div>
            {profile && profile.archetype_tags.length > 0 && (
              <div className="px-5 py-3 border-t border-white/5 glass-panel">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-cinema-textMuted text-xs">Tu perfil:</span>
                  {profile.archetype_tags.map((tag) => (
                    <span key={tag} className="text-xs px-2.5 py-0.5 rounded-full bg-gradient-to-r from-cinema-accent/15 to-amber-400/10 text-cinema-accent border border-cinema-accent/20">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Watchlist Drawer ────────────────────────────── */}
      {showWatchlist && (
        <div className="fixed inset-0 z-40 flex justify-end animate-fade-in" onClick={() => setShowWatchlist(false)}>
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-sm bg-cinema-bg border-l border-white/10 h-full overflow-y-auto shadow-2xl animate-slide-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 z-10 glass-panel border-b border-white/5 px-5 py-4 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-white text-lg">🔖 Mi Watchlist</h2>
                <p className="text-xs text-cinema-textMuted">{watchlist.length} película{watchlist.length !== 1 ? 's' : ''}</p>
              </div>
              <button onClick={() => setShowWatchlist(false)} className="text-cinema-textMuted hover:text-white transition-colors p-1">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {watchlist.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[60vh] text-cinema-textMuted px-8 text-center">
                <span className="text-5xl mb-4 opacity-30">🔖</span>
                <p className="text-sm font-medium mb-1">Tu watchlist está vacía</p>
                <p className="text-xs text-cinema-textMuted/60">Guarda películas con el botón &quot;Guardar&quot; en cada tarjeta</p>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {watchlist.map((movie) => (
                  <div key={movie.tmdb_id} className="flex gap-3 items-start p-3 rounded-xl bg-white/5 border border-white/5 group/item">
                    {movie.poster_url ? (
                      <img src={movie.poster_url} alt={movie.title} className="w-12 h-18 rounded-lg object-cover flex-shrink-0" />
                    ) : (
                      <div className="w-12 h-18 rounded-lg bg-cinema-card flex items-center justify-center flex-shrink-0">
                        <span className="text-lg opacity-30">🎬</span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-white truncate">{movie.title}</h4>
                      <p className="text-xs text-cinema-textMuted">{movie.year} · ⭐ {movie.score.toFixed(1)}</p>
                      {movie.genres && (
                        <p className="text-[10px] text-cinema-textMuted/60 truncate mt-0.5">{movie.genres.slice(0, 3).join(', ')}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleToggleWatchlist(movie)}
                      className="text-cinema-textMuted/40 hover:text-red-400 transition-colors opacity-0 group-hover/item:opacity-100 p-1"
                      title="Quitar"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Profile sidebar */}
      <ProfileSidebar profile={profile} isOpen={showProfile} onClose={() => setShowProfile(false)} />
    </div>
  );
}

const SUGGESTIONS = [
  { icon: '🧠', text: 'Una peli de ciencia ficción que haga pensar' },
  { icon: '😂', text: 'Comedia española para ver con amigos' },
  { icon: '🌑', text: 'Un thriller oscuro y perturbador' },
  { icon: '❤️', text: 'Película romántica pero no cursi' },
  { icon: '🎨', text: 'Cine de autor europeo de los 90' },
  { icon: '👻', text: 'Terror japonés realmente aterrador' },
];
