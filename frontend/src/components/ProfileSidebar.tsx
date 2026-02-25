'use client';

import type { UserProfile } from '@/types';

interface Props {
  profile: UserProfile | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ProfileSidebar({ profile, isOpen, onClose }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-md" onClick={onClose} />

      {/* Sidebar */}
      <div className="relative w-[420px] max-w-[92vw] glass-panel border-l border-white/[0.06]
                      overflow-y-auto animate-slide-in-right"
           style={{ background: 'linear-gradient(180deg, rgba(13,17,23,0.95), rgba(6,8,15,0.98))' }}>
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                <svg className="w-5 h-5 text-cinema-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Perfil Cinéfilo
              </h2>
              <p className="text-cinema-textMuted text-xs mt-1 ml-7.5">Tu huella cinematográfica</p>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center
                         text-cinema-textMuted hover:text-white hover:bg-white/[0.08] transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {!profile ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-cinema-accent/20 to-purple-500/20
                            border border-cinema-accent/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-cinema-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                </svg>
              </div>
              <p className="text-cinema-text font-medium mb-1.5">Sin datos aún</p>
              <p className="text-cinema-textMuted text-sm leading-relaxed max-w-[240px] mx-auto">
                Tu perfil se construirá automáticamente conforme explores películas
              </p>
            </div>
          ) : (
            <div className="space-y-7">
              {/* Archetype Tags */}
              {profile.archetype_tags.length > 0 && (
                <section>
                  <SectionTitle>Arquetipo</SectionTitle>
                  <div className="flex flex-wrap gap-2">
                    {profile.archetype_tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500/10 to-orange-500/10
                                   text-cinema-accent border border-amber-500/20 text-sm font-medium
                                   shadow-[0_0_12px_rgba(245,158,11,0.08)]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Stats Grid */}
              <section className="grid grid-cols-2 gap-2.5">
                <StatCard label="Interacciones" value={profile.interaction_count.toString()} gradient="from-blue-500/15 to-cyan-500/15" accent="text-blue-400" />
                <StatCard label="Rating medio" value={`${profile.avg_preferred_rating.toFixed(1)}`} gradient="from-amber-500/15 to-yellow-500/15" accent="text-amber-400" />
                <StatCard label="Películas vistas" value={profile.liked_movies.length.toString()} gradient="from-emerald-500/15 to-green-500/15" accent="text-emerald-400" />
                <StatCard label="Géneros" value={Object.keys(profile.genre_affinity).length.toString()} gradient="from-purple-500/15 to-pink-500/15" accent="text-purple-400" />
              </section>

              {/* Genre Affinity */}
              {Object.keys(profile.genre_affinity).length > 0 && (
                <section>
                  <SectionTitle>Géneros Favoritos</SectionTitle>
                  <div className="space-y-2.5">
                    {Object.entries(profile.genre_affinity)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 6)
                      .map(([genre, score]) => (
                        <AffinityBar key={genre} label={genre} value={score} colorFrom="#10b981" colorTo="#34d399" />
                      ))}
                  </div>
                </section>
              )}

              {/* Mood Affinity */}
              {Object.keys(profile.mood_affinity).length > 0 && (
                <section>
                  <SectionTitle>Estados de Ánimo</SectionTitle>
                  <div className="space-y-2.5">
                    {Object.entries(profile.mood_affinity)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 5)
                      .map(([mood, score]) => (
                        <AffinityBar key={mood} label={mood} value={score} colorFrom="#ec4899" colorTo="#f472b6" />
                      ))}
                  </div>
                </section>
              )}

              {/* Keywords */}
              {Object.keys(profile.keyword_affinity).length > 0 && (
                <section>
                  <SectionTitle>Temas de Interés</SectionTitle>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(profile.keyword_affinity)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 12)
                      .map(([kw, score]) => (
                        <span
                          key={kw}
                          className="text-xs px-2.5 py-1 rounded-md bg-purple-500/[0.08]
                                     text-purple-300/90 border border-purple-500/[0.12] transition-colors
                                     hover:bg-purple-500/[0.15] hover:border-purple-500/20"
                          style={{ opacity: 0.5 + Math.min(score / 8, 0.5) }}
                        >
                          {kw}
                        </span>
                      ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[11px] font-semibold text-cinema-textMuted/70 uppercase tracking-[0.15em] mb-3 flex items-center gap-2">
      <span className="w-4 h-px bg-cinema-textMuted/20" />
      {children}
    </h3>
  );
}

function StatCard({ label, value, gradient, accent }: {
  label: string; value: string; gradient: string; accent: string;
}) {
  return (
    <div className={`glass-card rounded-xl p-3.5 bg-gradient-to-br ${gradient}`}>
      <p className="text-cinema-textMuted text-[10px] uppercase tracking-wider mb-1">{label}</p>
      <p className={`${accent} font-bold text-xl tabular-nums`}>{value}</p>
    </div>
  );
}

function AffinityBar({ label, value, colorFrom, colorTo }: {
  label: string; value: number; colorFrom: string; colorTo: string;
}) {
  const pct = Math.min((value / 10) * 100, 100);

  return (
    <div className="group flex items-center gap-3">
      <span className="text-cinema-text text-sm w-24 truncate capitalize group-hover:text-white transition-colors">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${colorFrom}, ${colorTo})`,
            boxShadow: `0 0 8px ${colorFrom}40`,
          }}
        />
      </div>
      <span className="text-cinema-textMuted text-[10px] w-5 text-right tabular-nums">
        {value.toFixed(0)}
      </span>
    </div>
  );
}
