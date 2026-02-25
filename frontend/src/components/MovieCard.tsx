'use client';

import type { RecommendationItem } from '@/types';

interface Props {
  movie: RecommendationItem;
  index: number;
}

export default function MovieCard({ movie, index }: Props) {
  const scoreColor =
    movie.score >= 8 ? 'from-emerald-400 to-green-500' :
    movie.score >= 6 ? 'from-cinema-accent to-amber-400' :
    'from-orange-400 to-red-400';

  return (
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

        {/* Bottom gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-cinema-card via-cinema-card/60 via-40% to-transparent" />
      </div>

      {/* Content */}
      <div className="relative px-4 pb-4 -mt-12">
        <h3 className="font-bold text-white text-sm leading-tight mb-1 line-clamp-2 group-hover:text-cinema-accent transition-colors">
          {movie.title}
        </h3>
        <p className="text-cinema-accent/80 text-xs font-medium mb-2.5">{movie.year}</p>

        {/* Genres */}
        {movie.genres && movie.genres.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
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
        <p className="text-cinema-textMuted text-xs leading-relaxed line-clamp-3">
          {movie.reason}
        </p>
      </div>
    </div>
  );
}
