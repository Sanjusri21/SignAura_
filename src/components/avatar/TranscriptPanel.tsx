import React, { useState } from 'react';
import { 
  Copy, 
  Check, 
  FileEdit, 
  Download, 
  RotateCcw, 
  Sparkles, 
  Layers, 
  FileText, 
  Code2
} from 'lucide-react';
import { GlossToken, VideoProject } from '../../types';
import { GlassButton } from '../ui/GlassButton';

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
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  const handleCopy = () => {
    const textToCopy = activeTab === 'transcript'
      ? editableTranscript
      : project.glossTokens.map(t => t.gloss).join(' -> ');
    
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
        islGlossTokens: project.glossTokens
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
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);

    setDownloadSuccess(format.toUpperCase());
    setTimeout(() => setDownloadSuccess(null), 2500);
  };

  return (
    <div className="glass-card rounded-[28px] p-5 flex flex-col justify-between border border-white/14 shadow-2xl relative backdrop-blur-2xl">
      {/* Header & Tabs */}
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
          {/* Left Tab Switcher */}
          <div className="flex items-center gap-1 glass-subtle p-1 rounded-2xl border border-white/10">
            <button
              onClick={() => setActiveTab('transcript')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'transcript'
                  ? 'bg-white/18 text-white border border-white/25 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Transcript</span>
            </button>

            <button
              onClick={() => setActiveTab('gloss')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'gloss'
                  ? 'bg-white/18 text-white border border-white/25 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>ISL Gloss</span>
            </button>

            <button
              onClick={() => setActiveTab('syntax')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'syntax'
                  ? 'bg-white/18 text-white border border-white/25 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>ISL Syntax</span>
            </button>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-1">
            <button
              onClick={handleCopy}
              className="glass-subtle hover:bg-white/10 p-2 rounded-xl text-slate-300 hover:text-white border border-white/10 transition-all text-xs"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={() => setIsEditing(!isEditing)}
              className={`glass-subtle hover:bg-white/10 p-2 rounded-xl border border-white/10 transition-all text-xs ${
                isEditing ? 'bg-white/20 text-white border-white/30' : 'text-slate-300 hover:text-white'
              }`}
              title="Edit Spoken Transcript"
            >
              <FileEdit className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Content Views */}
        <div className="min-h-[160px] py-1">
          {activeTab === 'transcript' && (
            <div>
              {isEditing ? (
                <textarea
                  value={editableTranscript}
                  onChange={(e) => setEditableTranscript(e.target.value)}
                  className="w-full h-36 glass-input text-sm p-3 rounded-2xl resize-none font-sans leading-relaxed"
                  placeholder="Edit spoken transcript..."
                />
              ) : (
                <div className="text-sm text-slate-200 leading-relaxed space-y-2.5">
                  <p className="flex flex-wrap gap-1.5 items-center">
                    {project.glossTokens.map((token) => {
                      const isActive = token.id === activeTokenId;
                      return (
                        <span
                          key={token.id}
                          onClick={() => onSelectToken?.(token)}
                          className={`cursor-pointer px-2 py-0.5 rounded-lg transition-all ${
                            isActive
                              ? 'bg-white/20 text-white font-semibold border border-white/35 shadow-[0_0_12px_rgba(255,255,255,0.3)]'
                              : 'hover:bg-white/8 text-slate-200'
                          }`}
                        >
                          {token.word}
                        </span>
                      );
                    })}
                  </p>
                  <div className="text-xs text-slate-400 pt-3 border-t border-white/8 flex items-center justify-between">
                    <span>Accuracy: <strong className="text-white font-semibold">{project.accuracy}%</strong></span>
                    <span>Language: <strong className="text-slate-300 font-semibold">{project.language}</strong></span>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'gloss' && (
            <div className="space-y-3">
              <div className="p-3.5 rounded-2xl bg-black/30 border border-white/10 font-mono text-xs text-white flex flex-wrap gap-2 items-center leading-loose">
                {project.glossTokens.map((token, i) => (
                  <span key={token.id} className="inline-flex items-center gap-1.5">
                    <span 
                      onClick={() => onSelectToken?.(token)}
                      className={`cursor-pointer px-2.5 py-1 rounded-xl border transition-all ${
                        token.id === activeTokenId
                          ? 'bg-white/22 text-white border-white/40 shadow-md scale-105'
                          : 'bg-white/6 text-slate-200 border-white/10 hover:border-white/25'
                      }`}
                    >
                      {token.gloss}
                    </span>
                    {i < project.glossTokens.length - 1 && (
                      <span className="text-slate-500 font-sans">→</span>
                    )}
                  </span>
                ))}
              </div>
              <p className="text-[11px] text-slate-400">
                Click any gloss node to seek 3D SignAvatar to that gesture keyframe.
              </p>
            </div>
          )}

          {activeTab === 'syntax' && (
            <div className="space-y-3">
              <div className="p-3 rounded-2xl bg-white/6 border border-white/12 text-xs">
                <p className="font-bold text-white mb-1 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-slate-300" /> ISL Syntactic Grammar Rule: S-O-V Structure
                </p>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Indian Sign Language follows Subject + Object + Verb syntactic ordering with non-manual facial expressions.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl glass-subtle border border-white/10">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Topic / Time First</span>
                  <span className="text-white font-mono text-xs">TODAY, WELCOME</span>
                </div>
                <div className="p-2.5 rounded-xl glass-subtle border border-white/10">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Verb Final Placement</span>
                  <span className="text-white font-mono text-xs">PROCESS, ASSIST</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Export & Actions Footer */}
      <div className="pt-3 border-t border-white/10 flex flex-wrap items-center justify-between gap-2 mt-3">
        <GlassButton
          variant="secondary"
          size="sm"
          onClick={onReplay}
          icon={<RotateCcw className="w-3.5 h-3.5 text-slate-300" />}
        >
          Replay
        </GlassButton>

        {/* Multi-Format Export Buttons */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-slate-400 mr-1 hidden sm:inline">Export:</span>
          {(['srt', 'vtt', 'json'] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => handleExport(fmt)}
              className="glass-subtle hover:bg-white/10 px-2.5 py-1.5 rounded-xl text-xs font-mono font-semibold uppercase text-slate-300 hover:text-white border border-white/10 transition-all"
            >
              {downloadSuccess === fmt.toUpperCase() ? (
                <Check className="w-3 h-3 text-emerald-400 inline" />
              ) : (
                fmt
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
