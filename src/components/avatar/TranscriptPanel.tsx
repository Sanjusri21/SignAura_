import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  Copy,
  Check,
  FileEdit,
  Download,
  Sparkles,
  FileText,
  Code2,
  ArrowRight,
  Layers,
  Play,
  Pause,
  RotateCcw
} from 'lucide-react';
import { GlossToken, VideoProject } from '../../types';
import { GlassButton } from '../ui/GlassButton';
import { translateEnglishToISLGloss } from '../../lib/islGrammar';
import { hasSignMotion } from './SignAvatar3D';

interface TranscriptPanelProps {
  project: VideoProject;
  activeTokenId?: string;
  isPlaying?: boolean;
  onTogglePlay?: () => void;
  onReplay?: () => void;
  onSelectToken?: (token: GlossToken) => void;
}

// Comparable forms of a transcript word: "Don't," -> ["dont", "don"]
const wordForms = (word: string): string[] => {
  const clean = word.toLowerCase().replace(/[^a-z0-9']/g, '');
  if (!clean.replace(/'/g, '')) return [];
  return [clean.replace(/'/g, ''), clean.split("'")[0]];
};

/**
 * Maps each gloss token to the transcript word it came from. Tokens arrive in ISL order
 * and as stems ("striv", "jame"), so each takes the first unused exact match, falling back
 * to a prefix match for stems long enough to be unambiguous.
 */
const mapTokensToWords = (parts: string[], tokens: GlossToken[]): Map<string, number> => {
  const forms = parts.map(wordForms);
  const used = new Set<number>();
  const mapping = new Map<string, number>();
  const findUnused = (matches: (form: string) => boolean) =>
    forms.findIndex((f, i) => !used.has(i) && f.some(matches));

  for (const token of tokens) {
    const target = (token.word || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (!target) continue;
    let index = findUnused((f) => f === target);
    if (index < 0 && target.length >= 3) {
      index = findUnused((f) => f.startsWith(target));
    }
    if (index >= 0) {
      used.add(index);
      mapping.set(token.id, index);
    }
  }
  return mapping;
};

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  project,
  activeTokenId,
  isPlaying = false,
  onTogglePlay,
  onReplay,
  onSelectToken
}) => {
  const [activeTab, setActiveTab] = useState<'transcript' | 'gloss' | 'syntax'>('transcript');
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editableTranscript, setEditableTranscript] = useState(project.transcript);
  const transcriptScrollRef = useRef<HTMLDivElement>(null);
  const activeWordRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    setEditableTranscript(project.transcript);
    setIsEditing(false);
  }, [project.transcript]);

  // Compute live real ISL grammar gloss and tagged tokens
  const islResult = useMemo(() => {
    return translateEnglishToISLGloss(editableTranscript);
  }, [editableTranscript]);

  // Word-level sync between the transcript and the gloss token the avatar is signing
  const transcriptParts = useMemo(() => editableTranscript.split(/(\s+)/), [editableTranscript]);
  const tokenWordIndex = useMemo(
    () => mapTokensToWords(transcriptParts, project.glossTokens),
    [transcriptParts, project.glossTokens]
  );
  const wordTokens = useMemo(() => {
    const byWord = new Map<number, GlossToken>();
    project.glossTokens.forEach((t) => {
      const index = tokenWordIndex.get(t.id);
      if (index !== undefined) byWord.set(index, t);
    });
    return byWord;
  }, [tokenWordIndex, project.glossTokens]);

  const activeTokenIndex = project.glossTokens.findIndex((t) => t.id === activeTokenId);
  const activeToken = activeTokenIndex >= 0 ? project.glossTokens[activeTokenIndex] : undefined;
  const activeWordIndex = activeTokenId ? tokenWordIndex.get(activeTokenId) : undefined;
  const activeHasMotion = activeToken ? hasSignMotion(activeToken.gloss) : false;
  const signedWordIndexes = useMemo(() => {
    const signed = new Set<number>();
    project.glossTokens.slice(0, Math.max(0, activeTokenIndex)).forEach((t) => {
      const index = tokenWordIndex.get(t.id);
      if (index !== undefined) signed.add(index);
    });
    return signed;
  }, [project.glossTokens, activeTokenIndex, tokenWordIndex]);

  // Keep the glowing word visible inside the transcript box without scrolling the page
  useEffect(() => {
    const container = transcriptScrollRef.current;
    const word = activeWordRef.current;
    if (!container || !word) return;
    // The container is position: relative, so offsetTop is measured from its top edge
    const top = word.offsetTop;
    if (top < container.scrollTop || top + word.offsetHeight > container.scrollTop + container.clientHeight) {
      container.scrollTo({ top: top - container.clientHeight / 2, behavior: 'smooth' });
    }
  }, [activeWordIndex]);

  const handleCopy = () => {
    let textToCopy = '';
    if (activeTab === 'transcript') {
      textToCopy = `English: ${editableTranscript}\nISL Gloss: ${islResult.islGloss}`;
    } else {
      textToCopy = project.glossTokens.map(t => t.gloss).join(' -> ');
    }
    
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = (format: 'srt' | 'vtt' | 'json') => {
    let content = '';
    const filename = `signaura_export_${project.id}.${format}`;

    if (format === 'json') {
      content = JSON.stringify({
        project: project.title,
        accuracy: project.accuracy,
        transcript: editableTranscript,
        islGloss: islResult.islGloss,
        islGlossTokens: project.glossTokens,
        grammarTokens: islResult.tokens
      }, null, 2);
    } else if (format === 'srt') {
      content = project.glossTokens.map((t, idx) => {
        const start = `00:00:${t.startTime.toFixed(0).padStart(2, '0')},000`;
        const end = `00:00:${t.endTime.toFixed(0).padStart(2, '0')},000`;
        return `${idx + 1}\n${start} --> ${end}\n${t.word} [ISL: ${t.gloss}]\n`;
      }).join('\n');
    } else {
      content = `WEBVTT\n\n` + project.glossTokens.map((t) => {
        const start = `00:00:${t.startTime.toFixed(0).padStart(2, '0')}.000`;
        const end = `00:00:${t.endTime.toFixed(0).padStart(2, '0')}.000`;
        return `${start} --> ${end}\n${t.word} [ISL: ${t.gloss}]`;
      }).join('\n\n');
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Header & Tabs */}
      <div className="flex items-center justify-between border-b border-[#273154] pb-3">
        <div className="flex items-center gap-1.5 bg-[#101735] p-1 rounded-xl border border-[#273154]">
          <button
            onClick={() => setActiveTab('transcript')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              activeTab === 'transcript'
                ? 'bg-[#151D40] text-white border border-[#273154]'
                : 'text-[#A8B2D1] hover:text-white'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Dual Transcript & Gloss</span>
          </button>

          <button
            onClick={() => setActiveTab('gloss')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              activeTab === 'gloss'
                ? 'bg-[#151D40] text-white border border-[#273154]'
                : 'text-[#A8B2D1] hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>ISL Gestures</span>
          </button>
        </div>

        <button
          onClick={handleCopy}
          className="text-xs text-[#A8B2D1] hover:text-white flex items-center gap-1 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Content Body */}
      {activeTab === 'transcript' ? (
        <div className="space-y-3.5">
          {/* 1. English Source */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-bold text-[#A8B2D1] uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3 h-3 text-[#22D3EE]" />
                English Speech Input
              </span>
              <div className="flex items-center gap-3">
                {onTogglePlay && project.glossTokens.length > 0 && (
                  <button
                    onClick={onTogglePlay}
                    className="text-[#22D3EE] hover:underline flex items-center gap-1 font-medium text-[11px]"
                  >
                    {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                    <span>{isPlaying ? 'Pause' : 'Play with avatar'}</span>
                  </button>
                )}
                {onReplay && project.glossTokens.length > 0 && (
                  <button
                    onClick={onReplay}
                    className="text-[#A8B2D1] hover:text-white flex items-center gap-1 font-medium text-[11px]"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Replay</span>
                  </button>
                )}
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="text-[#22D3EE] hover:underline flex items-center gap-1 font-medium text-[11px]"
                >
                  <FileEdit className="w-3 h-3" />
                  <span>{isEditing ? 'Save edits' : 'Edit text'}</span>
                </button>
              </div>
            </div>

            {isEditing ? (
              <textarea
                value={editableTranscript}
                onChange={(e) => setEditableTranscript(e.target.value)}
                className="w-full bg-[#101735] text-xs p-3 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white outline-none resize-none leading-relaxed"
                rows={3}
              />
            ) : (
              <div
                ref={transcriptScrollRef}
                className="relative max-h-44 overflow-y-auto text-xs text-white bg-[#101735] p-3 rounded-xl border border-[#273154] leading-relaxed"
              >
                {transcriptParts.map((part, index) => {
                  const token = wordTokens.get(index);
                  if (!token) {
                    return (
                      <span key={index} className={isPlaying && part.trim() ? 'text-[#6B7A99]' : undefined}>
                        {part}
                      </span>
                    );
                  }

                  const isActive = index === activeWordIndex;
                  const isSigned = signedWordIndexes.has(index);
                  return (
                    <span
                      key={index}
                      ref={isActive ? activeWordRef : undefined}
                      onClick={() => onSelectToken?.(token)}
                      title={hasSignMotion(token.gloss) ? `ISL: ${token.gloss}` : `ISL: ${token.gloss} (no sign motion yet)`}
                      className={`cursor-pointer rounded px-0.5 -mx-0.5 transition-all duration-200 ${
                        isActive
                          ? activeHasMotion
                            ? 'bg-[#22D3EE]/25 text-[#22D3EE] font-bold shadow-[0_0_12px_rgba(34,211,238,0.55)]'
                            : 'bg-amber-400/20 text-amber-300 font-bold shadow-[0_0_10px_rgba(251,191,36,0.4)]'
                          : isPlaying && !isSigned
                          ? 'text-[#A8B2D1] hover:text-white'
                          : 'text-white hover:text-[#22D3EE]'
                      }`}
                    >
                      {part}
                    </span>
                  );
                })}
              </div>
            )}

            {activeToken && activeWordIndex !== undefined && !isEditing && (
              <div className="flex items-center gap-2 text-[10px] font-mono">
                <span className="text-[#6B7A99]">Signing:</span>
                <span className={activeHasMotion ? 'text-[#22D3EE] font-bold' : 'text-amber-300 font-bold'}>
                  {activeToken.gloss}
                </span>
                {!activeHasMotion && <span className="text-[#6B7A99]">no sign motion available, skipped</span>}
              </div>
            )}
          </div>

          {/* 2. ISL Syntactic Gloss Display (SOV Reordering) */}
          <div className="space-y-1.5 bg-[#101735]/80 p-3 rounded-xl border border-[#22D3EE]/30">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-bold text-[#22D3EE] uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3 h-3 text-[#22D3EE]" />
                ISL Gloss (SOV Syntax Reordering)
              </span>
              <span className="text-[10px] text-[#A8B2D1] bg-[#151D40] px-2 py-0.5 rounded border border-[#273154]">
                Time → SOV → Negation → WH-End
              </span>
            </div>

            <p className="text-sm font-mono font-bold text-[#22D3EE] tracking-wide pt-1">
              {islResult.islGloss || project.glossTokens.map(t => t.gloss).join(' ')}
            </p>

            {/* Grammar Tag Breakdown Chips */}
            {islResult.tokens.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[#273154]/60">
                {islResult.tokens.map((t) => (
                  <span
                    key={t.id}
                    className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[#151D40] border border-[#273154] text-white font-mono"
                  >
                    <span className="text-[#A8B2D1] text-[8px] uppercase">{t.tag}:</span>
                    <strong className="text-[#22D3EE]">{t.gloss}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between text-xs pt-1 border-t border-[#273154]">
            <span className="text-[11px] text-[#A8B2D1]">
              Grammar module: <strong className="text-[#22D3EE]">NLP Dependency & SOV Lemmatizer</strong>
            </span>

            <div className="flex items-center gap-1 text-[11px] text-[#A8B2D1]">
              <span>Export:</span>
              <button onClick={() => handleExport('srt')} className="text-white hover:text-[#22D3EE]">SRT</button>
              <span>•</span>
              <button onClick={() => handleExport('vtt')} className="text-white hover:text-[#22D3EE]">VTT</button>
              <span>•</span>
              <button onClick={() => handleExport('json')} className="text-white hover:text-[#22D3EE]">JSON</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          {project.glossTokens.map((t) => (
            <div
              key={t.id}
              onClick={() => onSelectToken?.(t)}
              className={`p-2.5 rounded-xl border transition-colors flex items-center justify-between cursor-pointer ${
                t.id === activeTokenId
                  ? 'bg-[#101735] border-[#22D3EE]'
                  : 'bg-[#101735] border-[#273154] hover:border-[#3B4975]'
              }`}
            >
              <div>
                <span className="text-xs font-mono font-bold text-white">{t.gloss}</span>
                <span className="text-[10px] text-[#A8B2D1] ml-2">"{t.word}"</span>
              </div>
              <span className="text-[10px] font-mono text-[#6B7A99]">
                {t.startTime}s - {t.endTime}s
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
