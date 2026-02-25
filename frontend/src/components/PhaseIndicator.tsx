'use client';

import type { SSEPhase } from '@/types';

interface Props {
  phase: SSEPhase | null;
}

const PHASES: { key: SSEPhase; label: string; icon: string }[] = [
  { key: 'extracting', label: 'Analizando', icon: '🧠' },
  { key: 'searching', label: 'Buscando', icon: '🔍' },
  { key: 'enriching', label: 'Enriqueciendo', icon: '📊' },
  { key: 'ranking', label: 'Puntuando', icon: '🏆' },
  { key: 'narrating', label: 'Escribiendo', icon: '✍️' },
];

export default function PhaseIndicator({ phase }: Props) {
  if (!phase) return null;

  const currentIdx = PHASES.findIndex((p) => p.key === phase);

  return (
    <div className="glass-card px-5 py-3.5 animate-fade-in">
      <div className="flex items-center gap-1">
        {PHASES.map((p, idx) => {
          const isActive = idx === currentIdx;
          const isDone = idx < currentIdx;

          return (
            <div key={p.key} className="flex items-center">
              <div className="flex items-center gap-1.5">
                <span className={`text-sm transition-transform duration-300 ${isActive ? 'scale-110' : ''}`}>{p.icon}</span>
                <span
                  className={`text-xs transition-all duration-300 ${
                    isActive
                      ? 'text-cinema-accent font-semibold'
                      : isDone
                      ? 'text-cinema-green'
                      : 'text-cinema-textMuted/30'
                  }`}
                >
                  {p.label}
                </span>
                {isActive && <div className="phase-dot bg-cinema-accent" />}
                {isDone && <span className="text-cinema-green text-[10px]">✓</span>}
              </div>
              {idx < PHASES.length - 1 && (
                <div className={`w-6 h-px mx-2 transition-colors duration-300 ${
                  isDone ? 'bg-cinema-green/50' : 'bg-white/[0.06]'
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
