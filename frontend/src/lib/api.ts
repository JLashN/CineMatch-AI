import type {
  GraphData,
  ProfileResponse,
  RecommendationItem,
  SSEPhase,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// ── Stream recommendation (SSE) ──────────────────────────

export interface StreamCallbacks {
  onStatus: (phase: SSEPhase) => void;
  onRecommendations: (recs: RecommendationItem[]) => void;
  onToken: (token: string) => void;
  onNarrativeReplace: (text: string) => void;
  onDone: (sessionId: string) => void;
  onError: (error: string) => void;
}

export async function streamRecommendation(
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
      callbacks.onError('No se pudo leer la respuesta');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7).trim();
          continue;
        }
        if (!line.startsWith('data: ')) continue;

        const data = line.slice(6);

        // We need to figure out the event type from context
        // SSE format: event: xxx\ndata: yyy\n\n
        // Let's re-parse properly
      }
    }
  } catch (err) {
    callbacks.onError(`Error de conexión: ${err}`);
  }
}

// Better SSE parser
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
      callbacks.onError('No readable stream');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const line = part.trim();

        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
          continue;
        }

        if (line.startsWith('data:')) {
          const data = line.slice(5).trim();

          switch (currentEvent) {
            case 'status':
              try {
                const status = JSON.parse(data);
                callbacks.onStatus(status.phase);
              } catch {}
              break;

            case 'recommendations':
              try {
                const recs = JSON.parse(data);
                callbacks.onRecommendations(recs);
              } catch {}
              break;

            case 'token':
              callbacks.onToken(data);
              break;

            case 'narrative_replace':
              callbacks.onNarrativeReplace(data);
              break;

            case 'done':
              try {
                const doneData = JSON.parse(data);
                callbacks.onDone(doneData.session_id || sessionId || '');
              } catch {
                callbacks.onDone(sessionId || '');
              }
              break;
          }

          currentEvent = '';
        }
      }
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
