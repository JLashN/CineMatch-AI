'use client';

import { useState } from 'react';
import type { RecommendationItem } from '@/types';

interface Props {
  movie: RecommendationItem;
  index: number;
  onAddToWatchlist?: (movie: RecommendationItem) => void;
  isInWatchlist?: boolean;
}

export default function MovieCard({ movie, index, onAddToWatchlist, isInWatchlist = false }: Props) {
  const [showTrailer, setShowTrailer] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [copied, setCopied] = useState(false);

  const scoreColor =
    movie.score >= 8 ? 'from-emerald-400 to-green-500' :
    movie.score >= 6 ? 'from-cinema-accent to-amber-400' :
    'from-orange-400 to-red-400';

  const handleShare = async () => {
    const text = `🎬 ${movie.title} (${movie.year}) — ${movie.score}/10\n${movie.reason}\n\nRecomendado por CineMatch AI`;
    if (navigator.share) {
      try {
        await navigator.share({ title: movie.title, text });
      } catch { /* user cancelled */ }
    } else {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <>
      <div
        className="group relative movie-card-shine rounded-2xl overflow-hidden
                   bg-cinema-card border border-white/[0.06]
                   hover:border-cinema-accent/30 transition-all duration-500
                   hover:shadow-2xl hover:shadow-amber-500/[0.08] hover:scale-[1.02]
                   animate-slide-up"
        style={{ animationDelay: `${index * 120}ms`, animationFillMode: 'both' }}
      >
        {/* Poster */}
        <div className="relative aspect-[2/3] overflow-hidden">
          {movie.poster_url ? (
            <img
              src={movie.poster_url}
              alt={movie.title}
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-cinema-surface to-cinema-card flex items-center justify-center">
              <span className="text-5xl opacity-30">🎬</span>
            </div>
          )}

          {/* Score badge */}
          <div className="absolute top-3 right-3">
            <div className={`bg-gradient-to-r ${scoreColor} px-2.5 py-1 rounded-xl shadow-lg`}>
              <span className="text-white text-xs font-bold">{movie.score.toFixed(1)}</span>
            </div>
          </div>

          {/* Trailer play button overlay */}
          {movie.trailer_url && (
            <button
              onClick={() => movie.trailer_embed_url ? setShowTrailer(true) : window.open(movie.trailer_url!, '_blank')}
              className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/40 transition-all duration-300 opacity-0 group-hover:opacity-100"
            >
              <div className="w-14 h-14 rounded-full bg-red-600/90 flex items-center justify-center shadow-xl transform scale-75 group-hover:scale-100 transition-transform duration-300">
                <svg className="w-6 h-6 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </button>
          )}

          {/* Bottom gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-cinema-card via-cinema-card/60 via-40% to-transparent pointer-events-none" />
        </div>

        {/* Content */}
        <div className="relative px-4 pb-4 -mt-12">
          <h3 className="font-bold text-white text-sm leading-tight mb-1 line-clamp-2 group-hover:text-cinema-accent transition-colors">
            {movie.title}
          </h3>

          <div className="flex items-center gap-2 mb-2">
            <span className="text-cinema-accent/80 text-xs font-medium">{movie.year}</span>
            {movie.director && (
              <span className="text-cinema-textMuted/60 text-[10px]">· {movie.director}</span>
            )}
          </div>

          {/* Multi-platform ratings */}
          {(movie.imdb_rating || movie.rotten_tomatoes != null || movie.metacritic != null) && (
            <div className="flex items-center gap-2 mb-2.5 flex-wrap">
              {movie.imdb_rating && (
                <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-yellow-500/10 border border-yellow-500/20">
                  <span className="text-[10px] font-bold text-yellow-400">IMDb</span>
                  <span className="text-[10px] text-yellow-300">{movie.imdb_rating}</span>
                </div>
              )}
              {movie.rotten_tomatoes != null && (
                <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-red-500/10 border border-red-500/20">
                  <span className="text-[10px]">{movie.rotten_tomatoes >= 60 ? '🍅' : '🤢'}</span>
                  <span className="text-[10px] text-red-300">{movie.rotten_tomatoes}%</span>
                </div>
              )}
              {movie.metacritic != null && (
                <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md border ${
                  movie.metacritic >= 60 ? 'bg-green-500/10 border-green-500/20' :
                  movie.metacritic >= 40 ? 'bg-yellow-500/10 border-yellow-500/20' :
                  'bg-red-500/10 border-red-500/20'
                }`}>
                  <span className="text-[10px] font-bold text-white/70">MC</span>
                  <span className={`text-[10px] ${
                    movie.metacritic >= 60 ? 'text-green-300' :
                    movie.metacritic >= 40 ? 'text-yellow-300' : 'text-red-300'
                  }`}>{movie.metacritic}</span>
                </div>
              )}
            </div>
          )}

          {/* Genres */}
          {movie.genres && movie.genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2.5">
              {movie.genres.slice(0, 3).map((genre) => (
                <span
                  key={genre}
                  className="text-[10px] px-2 py-0.5 rounded-full
                             bg-white/[0.06] text-cinema-textMuted border border-white/[0.06]"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {/* Reason */}
          <p className="text-cinema-textMuted text-xs leading-relaxed line-clamp-3 mb-3">
            {movie.reason}
          </p>

          {/* Awards */}
          {movie.awards && movie.awards !== 'N/A' && (
            <div className="flex items-center gap-1.5 mb-3 px-2 py-1.5 rounded-lg bg-amber-500/5 border border-amber-500/10">
              <span className="text-xs">🏆</span>
              <span className="text-[10px] text-amber-300/80 line-clamp-1">{movie.awards}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-1.5">
            {/* Detail / Trivia button */}
            {((movie.trivia && movie.trivia.length > 0) || movie.wikipedia_url) && (
              <button
                onClick={() => setShowDetail(true)}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium
                           bg-white/5 border border-white/10 text-cinema-textMuted hover:text-white hover:bg-white/10 transition-all"
                title="Datos curiosos"
              >
                <span>💡</span> Info
              </button>
            )}

            {/* Watchlist button */}
            {onAddToWatchlist && (
              <button
                onClick={() => onAddToWatchlist(movie)}
                className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                  isInWatchlist
                    ? 'bg-cinema-accent/20 border border-cinema-accent/30 text-cinema-accent'
                    : 'bg-white/5 border border-white/10 text-cinema-textMuted hover:text-cinema-accent hover:bg-cinema-accent/10'
                }`}
                title={isInWatchlist ? 'En tu watchlist' : 'Guardar'}
              >
                <span>{isInWatchlist ? '✓' : '+'}</span> {isInWatchlist ? 'Guardada' : 'Guardar'}
              </button>
            )}

            {/* Share button */}
            <button
              onClick={handleShare}
              className="flex items-center justify-center w-8 h-8 rounded-lg
                         bg-white/5 border border-white/10 text-cinema-textMuted hover:text-white hover:bg-white/10 transition-all"
              title={copied ? '¡Copiado!' : 'Compartir'}
            >
              <span className="text-xs">{copied ? '✓' : '↗'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Trailer Modal */}
      {showTrailer && movie.trailer_embed_url && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in" onClick={() => setShowTrailer(false)}>
          <div className="relative w-full max-w-4xl mx-4" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowTrailer(false)}
              className="absolute -top-10 right-0 text-white/70 hover:text-white text-lg transition-colors"
            >
              ✕ Cerrar
            </button>
            <div className="aspect-video rounded-2xl overflow-hidden shadow-2xl">
              <iframe
                src={`${movie.trailer_embed_url}?autoplay=1`}
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                title={`Trailer: ${movie.title}`}
              />
            </div>
            <p className="text-center text-white/60 text-sm mt-3">{movie.title} ({movie.year})</p>
          </div>
        </div>
      )}

      {/* Detail/Trivia Modal */}
      {showDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in" onClick={() => setShowDetail(false)}>
          <div className="relative w-full max-w-lg mx-4 glass-panel rounded-2xl p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowDetail(false)}
              className="absolute top-4 right-4 text-cinema-textMuted hover:text-white transition-colors"
            >
              ✕
            </button>

            <h3 className="text-lg font-bold text-white mb-1">{movie.title}</h3>
            <p className="text-cinema-accent text-sm mb-4">{movie.year} {movie.director ? `· Dir: ${movie.director}` : ''}</p>

            {movie.actors && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-cinema-textMuted uppercase mb-1.5">Reparto</h4>
                <p className="text-sm text-cinema-text">{movie.actors}</p>
              </div>
            )}

            {movie.trivia && movie.trivia.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-cinema-textMuted uppercase mb-2">💡 Datos curiosos</h4>
                <div className="space-y-2">
                  {movie.trivia.map((fact, i) => (
                    <div key={i} className="px-3 py-2 rounded-lg bg-white/5 border border-white/5">
                      <p className="text-xs text-cinema-text leading-relaxed">{fact}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {movie.awards && movie.awards !== 'N/A' && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-cinema-textMuted uppercase mb-1.5">🏆 Premios</h4>
                <p className="text-sm text-amber-300">{movie.awards}</p>
              </div>
            )}

            <div className="flex items-center gap-3 mt-4 pt-4 border-t border-white/10">
              {movie.wikipedia_url && (
                <a
                  href={movie.wikipedia_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-cinema-textMuted hover:text-white text-xs transition-all"
                >
                  📖 Wikipedia
                </a>
              )}
              {movie.trailer_url && (
                <a
                  href={movie.trailer_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 hover:text-red-200 text-xs transition-all"
                >
                  ▶ YouTube
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
