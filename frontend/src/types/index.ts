// ── API Types ────────────────────────────────────────────

export interface RecommendationItem {
  tmdb_id: number;
  title: string;
  year: number;
  score: number;
  poster_url: string | null;
  reason: string;
  genres: string[];
  keywords: string[];
  // Extended enrichment
  trailer_url?: string | null;
  trailer_embed_url?: string | null;
  trailer_thumbnail?: string | null;
  imdb_rating?: number | null;
  rotten_tomatoes?: number | null;
  metacritic?: number | null;
  awards?: string | null;
  director?: string | null;
  actors?: string | null;
  trivia?: string[];
  wikipedia_url?: string | null;
}

export interface RecommendResponse {
  session_id: string;
  narrative: string;
  recommendations: RecommendationItem[];
  processing_time_ms: number;
}

export interface RecommendRequest {
  query: string;
  session_id?: string;
  max_results?: number;
  language?: string;
  filters?: {
    min_year?: number;
    min_rating?: number;
  };
}

// ── Profile Types ────────────────────────────────────────

export interface UserProfile {
  genre_affinity: Record<string, number>;
  keyword_affinity: Record<string, number>;
  mood_affinity: Record<string, number>;
  era_preference: Record<string, number>;
  director_affinity: Record<string, number>;
  country_preference: Record<string, number>;
  liked_movies: number[];
  disliked_movies: number[];
  interaction_count: number;
  avg_preferred_rating: number;
  archetype_tags: string[];
}

export interface ProfileResponse {
  session_id: string;
  profile: UserProfile | null;
}

// ── Graph Types ──────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: 'user' | 'movie' | 'genre' | 'keyword' | 'mood' | 'archetype';
  index?: number;
  tags?: string[];
  score?: number;
  year?: number;
  poster_url?: string;
  reason?: string;
  // D3 simulation properties
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  relation: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  profile: UserProfile | null;
  stats: {
    total_nodes: number;
    total_links: number;
    movie_count: number;
    genre_count: number;
    keyword_count: number;
  };
}

// ── Chat Types ───────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  recommendations?: RecommendationItem[];
  timestamp: Date;
  isStreaming?: boolean;
}

// ── SSE Event Types ──────────────────────────────────────

export type SSEPhase = 'extracting' | 'searching' | 'enriching' | 'ranking' | 'narrating';

export interface SSEStatusEvent {
  phase: SSEPhase;
}

// ── Watchlist Types ──────────────────────────────────────

export interface WatchlistResponse {
  session_id: string;
  movies: RecommendationItem[];
}

// ── Export Types ──────────────────────────────────────────

export interface ExportResponse {
  format: 'json' | 'markdown';
  content?: string;
  session_id?: string;
  turns?: { role: string; content: string }[];
  recommendations?: RecommendationItem[];
}
