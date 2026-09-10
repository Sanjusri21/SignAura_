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
  isPlaying?: boolean;
  onTogglePlay?: () => void;
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
    <div className="w-full bg-[#151D40] p-4 rounded-2xl border border-[#273154] shadow-md relative select-none">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#22D3EE] animate-pulse" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#22D3EE]" />
            ISL Gloss Sequence Timeline
          </h3>
        </div>
        
        <div className="flex items-center gap-2 text-xs font-mono text-[#A8B2D1]">
          <Clock className="w-3.5 h-3.5 text-[#6B7A99]" />
          <span>
            {currentTime.toFixed(1)}s / {totalDuration.toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Progress Track */}
      <div 
        className="w-full h-2 rounded-full bg-[#101735] relative mb-4 cursor-pointer overflow-hidden group border border-[#273154]"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const clickX = e.clientX - rect.left;
          const percentage = clickX / rect.width;
          onSeekTime?.(percentage * totalDuration);
        }}
      >
        <div 
          className="h-full rounded-full bg-[#22D3EE] transition-all duration-150"
          style={{ width: `${Math.min(100, (currentTime / (totalDuration || 1)) * 100)}%` }}
        />
      </div>

      {/* Gloss Token Chips Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1">
        {tokens.map((token) => {
          const isActive = token.id === activeTokenId;
          return (
            <button
              key={token.id}
              onClick={() => onSelectToken(token)}
              className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-semibold tracking-wide transition-colors relative flex flex-col items-center gap-0.5 border ${
                isActive
                  ? 'bg-[#101735] text-white border-[#22D3EE] shadow-sm'
                  : 'bg-[#101735] text-[#A8B2D1] hover:text-white hover:bg-[#1A244D] border-[#273154]'
              }`}
            >
              {/* Gloss Sign Name */}
              <span className={`font-mono text-xs font-bold ${isActive ? 'text-[#22D3EE]' : 'text-white'}`}>
                {token.gloss}
              </span>

              {/* Original Spoken Word */}
              <span className="text-[10px] text-[#A8B2D1] font-normal">
                "{token.word}"
              </span>

              {/* Grammar Tag Pill */}
              {token.grammarTag && (
                <span className="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-[#151D40] text-[#A8B2D1] border border-[#273154] mt-0.5">
                  {token.grammarTag}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
