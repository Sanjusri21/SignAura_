import React from 'react';
import { GlossToken } from '../../types';
import { Sparkles, Clock } from 'lucide-react';

interface GlossTimelineProps {
  tokens: GlossToken[];
  activeTokenId: string;
  onSelectToken: (token: GlossToken) => void;
  currentTime?: number;
  totalDuration?: number;
  onSeekTime?: (time: number) => void;
}

export const GlossTimeline: React.FC<GlossTimelineProps> = ({
  tokens,
  activeTokenId,
  onSelectToken,
  currentTime = 0,
  totalDuration = 25,
  onSeekTime
}) => {
  return (
    <div className="w-full glass-card p-4 rounded-3xl border border-white/12 shadow-xl relative select-none">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-slate-300" />
            ISL Gloss Sequence Timeline
          </h3>
        </div>
        
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>
            {currentTime.toFixed(1)}s / {totalDuration.toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Progress Track */}
      <div 
        className="w-full h-2 rounded-full bg-white/8 relative mb-4 cursor-pointer overflow-hidden group border border-white/8"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const clickX = e.clientX - rect.left;
          const percentage = clickX / rect.width;
          onSeekTime?.(percentage * totalDuration);
        }}
      >
        <div 
          className="h-full rounded-full bg-gradient-to-r from-white/90 via-cyan-300 to-indigo-300 shadow-[0_0_12px_rgba(255,255,255,0.4)] transition-all duration-150"
          style={{ width: `${Math.min(100, (currentTime / (totalDuration || 1)) * 100)}%` }}
        />
      </div>

      {/* Gloss Token Chips Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1 scrollbar-thin">
        {tokens.map((token) => {
          const isActive = token.id === activeTokenId;
          return (
            <button
              key={token.id}
              onClick={() => onSelectToken(token)}
              className={`flex-shrink-0 px-3.5 py-2 rounded-2xl text-xs font-semibold tracking-wide transition-all duration-200 relative group flex flex-col items-center gap-0.5 ${
                isActive
                  ? 'bg-white/18 text-white border border-white/35 shadow-[0_0_20px_rgba(255,255,255,0.2)] scale-105'
                  : 'glass-subtle text-slate-300 hover:text-white hover:bg-white/8 border border-white/10 hover:border-white/20'
              }`}
            >
              {/* Gloss Sign Name */}
              <span className="font-mono text-[13px] font-bold text-white">
                {token.gloss}
              </span>

              {/* Original Spoken Word */}
              <span className="text-[10px] text-slate-400 font-normal group-hover:text-slate-200">
                "{token.word}"
              </span>

              {/* Grammar Tag Pill */}
              {token.grammarTag && (
                <span className="text-[8px] font-mono uppercase px-1.5 py-0.2 rounded-full bg-white/8 text-slate-300 border border-white/10 mt-0.5">
                  {token.grammarTag}
                </span>
              )}

              {/* Active Underline Glow */}
              {isActive && (
                <span className="absolute -bottom-1 left-2 right-2 h-0.5 bg-white rounded-full shadow-[0_0_8px_#ffffff]" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
