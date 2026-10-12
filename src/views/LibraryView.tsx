import React, { useState } from 'react';
import { 
  Film, 
  Search, 
  Play, 
  Clock, 
  Sparkles, 
  X,
  UserSquare2,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';
import { VideoProject, NavigationTab } from '../types';
import { GlassButton } from '../components/ui/GlassButton';
import { StatusBadge } from '../components/ui/StatusBadge';
import { formatDuration, formatSeconds } from '../utils/formatters';
import { resolveGlossTokensWithFallback } from '../lib/islFingerspelling';


interface LibraryViewProps {
  projects: VideoProject[];
  onSelectProject: (project: VideoProject) => void;
  onNavigate: (tab: NavigationTab) => void;
}

export const LibraryView: React.FC<LibraryViewProps> = ({
  projects,
  onSelectProject,
  onNavigate
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDialect, setFilterDialect] = useState<string>('all');
  const [selectedProjectPreview, setSelectedProjectPreview] = useState<VideoProject | null>(null);

  const filteredProjects = projects.filter((p) => {
    const matchesSearch = p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.transcript.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDialect = filterDialect === 'all' || p.dialect === filterDialect;
    return matchesSearch && matchesDialect;
  });

  return (
    <div className="space-y-6 pb-20 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Translation History & Archive</h1>
            <span className="text-xs font-semibold text-[#A8B2D1] bg-[#151D40] px-2.5 py-0.5 rounded-md border border-[#273154]">
              {projects.length} Saved
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#A8B2D1] mt-0.5">
            Previous media conversions with transcribed audio, syntactic tokens, and synchronized 3D sign sequences.
          </p>
        </div>

        <GlassButton
          variant="primary"
          size="sm"
          onClick={() => onNavigate('convert')}
          icon={<Sparkles className="w-3.5 h-3.5 text-[#080D24]" />}
        >
          New Conversion
        </GlassButton>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-[#151D40] p-3 rounded-2xl border border-[#273154] flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-[#6B7A99] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search archive by title, keywords, or transcript content..."
            className="w-full text-xs pl-10 pr-4 py-2.5 rounded-xl border border-[#273154] bg-[#101735] text-white placeholder-[#6B7A99] outline-none focus:border-[#22D3EE]"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={filterDialect}
            onChange={(e) => setFilterDialect(e.target.value)}
            className="text-xs py-2.5 px-3 rounded-xl bg-[#101735] text-white w-full sm:w-auto border border-[#273154] outline-none"
          >
            <option value="all">All Dialects</option>
            <option value="standard">ISL Standard</option>
            <option value="north">ISL Northern</option>
            <option value="south">ISL Southern</option>
          </select>
        </div>
      </div>

      {/* Video Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredProjects.map((proj) => (
          <div
            key={proj.id}
            className="bg-[#151D40] p-5 rounded-2xl border border-[#273154] flex flex-col justify-between group hover:border-[#3B4975] transition-colors shadow-md"
          >
            {/* Header / Info */}
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-bold text-white group-hover:text-[#22D3EE] transition-colors line-clamp-1">
                  {proj.title}
                </h3>
                <StatusBadge status={proj.status} />
              </div>

              <p className="text-xs text-[#A8B2D1] line-clamp-2 leading-relaxed">
                "{proj.transcript}"
              </p>

              {/* Tokens Preview / Unsupported Language Warning */}
              {proj.languageSupported === false ? (
                <div className="pt-1">
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    Language not supported yet ({proj.language?.toUpperCase() || 'OTHER'})
                  </span>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {proj.glossTokens.slice(0, 4).map((t) => (
                    <span
                      key={t.id}
                      className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#101735] text-[#A8B2D1] border border-[#273154]"
                    >
                      {t.gloss}
                    </span>
                  ))}
                  {proj.glossTokens.length > 4 && (
                    <span className="text-[10px] text-[#6B7A99] font-mono">
                      +{proj.glossTokens.length - 4} signs
                    </span>
                  )}
                </div>
              )}

              {/* Coverage Report Badge */}
              {proj.languageSupported !== false && (
                <div className="flex items-center justify-between text-[10px] pt-2 border-t border-[#273154]/50">
                  <span className="text-[#A8B2D1]">Coverage:</span>
                  <span className="font-semibold text-[#22D3EE] bg-[#101735] px-2 py-0.5 rounded border border-[#273154]">
                    {proj.coverage !== undefined ? proj.coverage : resolveGlossTokensWithFallback(proj.glossTokens).coverage}% Signs
                    {(proj.coverage !== undefined ? proj.coverage : resolveGlossTokensWithFallback(proj.glossTokens).coverage) < 100 && (
                      <span className="text-[#A8B2D1] ml-1">
                        ({100 - (proj.coverage !== undefined ? proj.coverage : resolveGlossTokensWithFallback(proj.glossTokens).coverage)}% Fingerspelled)
                      </span>
                    )}
                  </span>
                </div>
              )}
            </div>

            {/* Footer Actions */}
            <div className="pt-4 mt-4 border-t border-[#273154] flex items-center justify-between text-xs text-[#A8B2D1]">
              <div className="flex items-center gap-2 text-[11px]">
                <Clock className="w-3.5 h-3.5" />
                <span>{formatDuration(proj.duration)}</span>
                <span>•</span>
                <span className="capitalize">{proj.dialect} ISL</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedProjectPreview(proj)}
                  className="p-1.5 rounded-lg bg-[#101735] hover:bg-[#1A244D] text-[#A8B2D1] hover:text-white border border-[#273154] transition-colors"
                  title="Inspect details"
                >
                  <Layers className="w-3.5 h-3.5" />
                </button>

                <button
                  onClick={() => {
                    onSelectProject(proj);
                    onNavigate('avatar');
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-[#101735] hover:bg-[#1A244D] text-[#22D3EE] font-semibold border border-[#273154] hover:border-[#22D3EE]/40 flex items-center gap-1 transition-colors"
                >
                  <Play className="w-3 h-3" />
                  <span>Open 3D</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Detail Preview */}
      {selectedProjectPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setSelectedProjectPreview(null)}
            className="fixed inset-0 bg-black/75"
          />

          <div className="relative w-full max-w-2xl bg-[#151D40] rounded-2xl p-6 border border-[#273154] shadow-2xl space-y-5 z-10">
            <div className="flex items-center justify-between pb-3 border-b border-[#273154]">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedProjectPreview.title}</h3>
                <p className="text-xs text-[#A8B2D1]">
                  Duration: {formatDuration(selectedProjectPreview.duration)} • Dialect: {selectedProjectPreview.dialect.toUpperCase()} ISL
                </p>
              </div>
              <button
                onClick={() => setSelectedProjectPreview(null)}
                className="p-1.5 rounded-lg text-[#A8B2D1] hover:text-white bg-[#101735] border border-[#273154]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold text-white mb-1">Full Transcript:</p>
                <p className="text-xs text-[#A8B2D1] p-3 rounded-xl bg-[#101735] border border-[#273154] leading-relaxed">
                  "{selectedProjectPreview.transcript}"
                </p>
              </div>

              {selectedProjectPreview.languageSupported === false && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200">
                  {selectedProjectPreview.message || `Language not supported yet (${selectedProjectPreview.language}). Only English and Hindi are supported for Indian Sign Language translation.`}
                </div>
              )}

              <div>
                {(() => {
                  const { resolvedTokens, coverage, authenticCount, fingerspelledCount } = resolveGlossTokensWithFallback(selectedProjectPreview.glossTokens);
                  return (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-white">
                          ISL Gloss Sequence ({resolvedTokens.length} Tokens):
                        </span>
                        <span className="text-[10px] font-semibold text-[#22D3EE] bg-[#101735] px-2 py-0.5 rounded border border-[#273154]">
                          Coverage: {selectedProjectPreview.coverage !== undefined ? selectedProjectPreview.coverage : coverage}% ({authenticCount} Signs, {fingerspelledCount} Fingerspelled)
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto p-2.5 rounded-xl bg-[#101735] border border-[#273154]">
                        {resolvedTokens.map((t) => (
                          <div 
                            key={t.id} 
                            className={`p-2 rounded border text-center ${
                              t.isFingerspelled 
                                ? 'bg-purple-950/40 border-purple-500/40 text-purple-200' 
                                : 'bg-[#151D40] border-[#273154] text-white'
                            }`}
                          >
                            <p className="text-xs font-mono font-bold flex items-center justify-center gap-1">
                              <span className={t.isFingerspelled ? 'text-purple-300' : 'text-[#22D3EE]'}>{t.gloss}</span>
                              {t.isFingerspelled && (
                                <span className="text-[8px] bg-purple-500/30 text-purple-200 px-1 rounded font-sans font-bold">FS</span>
                              )}
                            </p>
                            <p className="text-[9px] text-[#A8B2D1] mt-0.5">
                              {t.isFingerspelled && t.fingerspelledChars ? t.fingerspelledChars.join('-') : `${formatSeconds(t.startTime)} - ${formatSeconds(t.endTime)}`}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <GlassButton
                variant="secondary"
                size="sm"
                onClick={() => setSelectedProjectPreview(null)}
              >
                Close
              </GlassButton>
              <GlassButton
                variant="primary"
                size="sm"
                onClick={() => {
                  onSelectProject(selectedProjectPreview);
                  setSelectedProjectPreview(null);
                  onNavigate('avatar');
                }}
                icon={<Play className="w-3.5 h-3.5 text-[#080D24]" />}
              >
                Launch in 3D Avatar
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
