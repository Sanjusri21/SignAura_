import React, { useState, useMemo } from 'react';
import { 
  Copy, 
  Check, 
  FileEdit, 
  Download, 
  Sparkles, 
  FileText, 
  Code2,
  ArrowRight,
  Layers
} from 'lucide-react';
import { GlossToken, VideoProject } from '../../types';
import { GlassButton } from '../ui/GlassButton';
import { translateEnglishToISLGloss } from '../../lib/islGrammar';

interface TranscriptPanelProps {
  project: VideoProject;
  activeTokenId?: string;
  onReplay?: () => void;
  onSelectToken?: (token: GlossToken) => void;
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  project,
  activeTokenId,
  onReplay,
  onSelectToken
}) => {
  const [activeTab, setActiveTab] = useState<'transcript' | 'gloss' | 'syntax'>('transcript');
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editableTranscript, setEditableTranscript] = useState(project.transcript);

  // Compute live real ISL grammar gloss and tagged tokens
  const islResult = useMemo(() => {
    return translateEnglishToISLGloss(editableTranscript);
  }, [editableTranscript]);

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
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="text-[#22D3EE] hover:underline flex items-center gap-1 font-medium text-[11px]"
              >
                <FileEdit className="w-3 h-3" />
                <span>{isEditing ? 'Save edits' : 'Edit text'}</span>
              </button>
            </div>

            {isEditing ? (
              <textarea
                value={editableTranscript}
                onChange={(e) => setEditableTranscript(e.target.value)}
                className="w-full bg-[#101735] text-xs p-3 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white outline-none resize-none leading-relaxed"
                rows={3}
              />
            ) : (
              <div className="text-xs text-white bg-[#101735] p-3 rounded-xl border border-[#273154] leading-relaxed">
                "{editableTranscript}"
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
