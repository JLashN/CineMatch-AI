/**
 * CineMatch AI — API Client Layer
 *
 * Clean SSE streaming client with proper token handling.
 * Uses the Strategy pattern for event dispatching.
 *
 * CRITICAL: SSE tokens from the backend carry intentional leading spaces
 *           (e.g. " bien", " que"). We must NOT .trim() them.
 */

import type {
  GraphData,
  ProfileResponse,
  RecommendationItem,
  SSEPhase,
} from '@/types';

// ── Configuration ────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// ── SSE Stream Callbacks (Observer pattern) ──────────────

export interface StreamCallbacks {
  onStatus: (phase: SSEPhase) => void;
  onRecommendations: (recs: RecommendationItem[]) => void;
  onToken: (token: string) => void;
  onNarrativeReplace: (text: string) => void;
  onDone: (sessionId: string) => void;
  onError: (error: string) => void;
}

// ── SSE Event Handlers (Strategy pattern) ────────────────

type SSEEventHandler = (rawData: string, callbacks: StreamCallbacks, context: SSEContext) => void;

interface SSEContext {
  sessionId: string | null;
}

const EVENT_HANDLERS: Record<string, SSEEventHandler> = {
  status: (rawData, callbacks) => {
    try {
      const status = JSON.parse(rawData.trim());
      callbacks.onStatus(status.phase);
    } catch { /* malformed status event */ }
  },

  recommendations: (rawData, callbacks) => {
    try {
      const recs = JSON.parse(rawData.trim());
      callbacks.onRecommendations(recs);
    } catch { /* malformed recs event */ }
  },

  token: (rawData, callbacks) => {
    // CRITICAL: Do NOT trim rawData here!
    // The backend sends tokens like " bien" with an intentional leading space.
    // Trimming would strip the space → words concatenate without spaces.
    callbacks.onToken(rawData);
  },

  narrative_replace: (rawData, callbacks) => {
    callbacks.onNarrativeReplace(rawData.trim());
  },

  done: (rawData, callbacks, context) => {
    try {
      const doneData = JSON.parse(rawData.trim());
      callbacks.onDone(doneData.session_id || context.sessionId || '');
    } catch {
      callbacks.onDone(context.sessionId || '');
    }
  },
};

// ── SSE Parser ───────────────────────────────────────────

class SSEParser {
  private buffer = '';
  private currentEvent = '';
  private readonly callbacks: StreamCallbacks;
  private readonly context: SSEContext;

  constructor(callbacks: StreamCallbacks, context: SSEContext) {
    this.callbacks = callbacks;
    this.context = context;
  }

  /**
   * Feed raw bytes from the ReadableStream into the parser.
   * Handles SSE line protocol: `event: <type>\ndata: <payload>\n\n`
   */
  feed(chunk: string): void {
    this.buffer += chunk;
    // SSE uses \r\n line endings (HTTP). Normalize to \n then split.
    const normalized = this.buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const parts = normalized.split('\n');
    // Last element might be incomplete — keep it in the buffer
    this.buffer = parts.pop() || '';

    for (const rawLine of parts) {
      // SSE spec: lines starting with "event:" set the event type
      if (rawLine.startsWith('event:')) {
        // Strip "event:" + one optional leading space, then trim any extra whitespace
        let ev = rawLine.slice(6);
        if (ev.startsWith(' ')) ev = ev.slice(1);
        this.currentEvent = ev.trim();
        continue;
      }

      // SSE spec: lines starting with "data:" carry the payload
      if (rawLine.startsWith('data:')) {
        // SSE spec §9.2.4: remove "data:" prefix, then strip exactly ONE
        // optional leading U+0020 SPACE.  Any further spaces are real payload.
        //   "data: hello"   → "hello"
        //   "data:  hello"  → " hello"   (one leading space is real token data)
        //   "data:hello"    → "hello"    (no leading space to strip)
        let rawData = rawLine.slice(5);            // strip "data:"
        if (rawData.startsWith(' ')) {
          rawData = rawData.slice(1);              // strip ONE protocol space
        }
        this.dispatch(this.currentEvent, rawData);
        this.currentEvent = '';
        continue;
      }

      // Empty lines and comments (`:`) are ignored per SSE spec
    }
  }

  private dispatch(eventType: string, rawData: string): void {
    const handler = EVENT_HANDLERS[eventType];
    if (handler) {
      handler(rawData, this.callbacks, this.context);
    }
  }
}

// ── Main Streaming Function ──────────────────────────────

export async function streamRecommendationSSE(
  query: string,
  sessionId: string | null,
  callbacks: StreamCallbacks,
  maxResults: number = 3,
): Promise<void> {
  const body = {
    query,
    session_id: sessionId,
    max_results: maxResults,
    language: 'es',
    filters: {},
  };

  try {
    const response = await fetch(`${API_BASE}/api/recommend/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const err = await response.text();
      callbacks.onError(`Error ${response.status}: ${err}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError('No readable stream available');
      return;
    }

    const decoder = new TextDecoder();
    const parser = new SSEParser(callbacks, { sessionId });

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));
    }
  } catch (err) {
    callbacks.onError(`Error de conexión: ${err}`);
  }
}

// ── Non-streaming recommendation ─────────────────────────

export async function fetchRecommendation(
  query: string,
  sessionId: string | null,
  maxResults: number = 3,
) {
  const body = {
    query,
    session_id: sessionId,
    max_results: maxResults,
    language: 'es',
    filters: {},
  };

  const response = await fetch(`${API_BASE}/api/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Error ${response.status}: ${await response.text()}`);
  }

  return response.json();
}

// ── Graph data ───────────────────────────────────────────

export async function fetchGraphData(
  sessionId: string,
  movies?: RecommendationItem[],
): Promise<GraphData> {
  if (movies && movies.length > 0) {
    const response = await fetch(`${API_BASE}/api/graph/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        movies: movies.map((m) => ({
          tmdb_id: m.tmdb_id,
          title: m.title,
          year: m.year,
          score: m.score,
          poster_url: m.poster_url,
          reason: m.reason,
          genres: m.genres || [],
          keywords: m.keywords || [],
        })),
      }),
    });
    if (!response.ok) throw new Error('Failed to fetch graph');
    return response.json();
  }

  const response = await fetch(`${API_BASE}/api/graph/${sessionId}`);
  if (!response.ok) throw new Error('Failed to fetch graph');
  return response.json();
}

// ── User profile ─────────────────────────────────────────

export async function fetchProfile(
  sessionId: string,
): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE}/api/profile/${sessionId}`);
  if (!response.ok) throw new Error('Failed to fetch profile');
  return response.json();
}

// ── Health check ─────────────────────────────────────────

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/api/health`);
  return response.json();
}

// ── Watchlist ────────────────────────────────────────────

export async function getWatchlist(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/watchlist/${sessionId}`);
  if (!response.ok) throw new Error('Failed to fetch watchlist');
  return response.json();
}

export async function addToWatchlist(sessionId: string, movie: any) {
  const response = await fetch(`${API_BASE}/api/watchlist/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ movie }),
  });
  if (!response.ok) throw new Error('Failed to add to watchlist');
  return response.json();
}

export async function removeFromWatchlist(sessionId: string, tmdbId: number) {
  const response = await fetch(`${API_BASE}/api/watchlist/${sessionId}/${tmdbId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to remove from watchlist');
  return response.json();
}

// ── Trailer ──────────────────────────────────────────────

export async function getTrailer(tmdbId: number) {
  const response = await fetch(`${API_BASE}/api/trailer/${tmdbId}`);
  if (!response.ok) throw new Error('Failed to fetch trailer');
  return response.json();
}

// ── Export conversation ──────────────────────────────────

export async function exportConversation(sessionId: string, format: 'json' | 'markdown' = 'markdown') {
  const response = await fetch(`${API_BASE}/api/export/${sessionId}?format=${format}`);
  if (!response.ok) throw new Error('Failed to export conversation');
  return response.json();
}
