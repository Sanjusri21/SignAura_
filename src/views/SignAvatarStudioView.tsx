import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Layers, 
  Share2, 
  Sliders, 
  Maximize2, 
  RotateCcw,
  BookOpen
} from 'lucide-react';
import { SignAvatar3D } from '../components/avatar/SignAvatar3D';
import { GlossTimeline } from '../components/avatar/GlossTimeline';
import { TranscriptPanel } from '../components/avatar/TranscriptPanel';
import { VideoProject, GlossToken } from '../types';
import { GlassButton } from '../components/ui/GlassButton';

interface SignAvatarStudioViewProps {
  project: VideoProject;
  onOpenDictionary?: () => void;
}

export const SignAvatarStudioView: React.FC<SignAvatarStudioViewProps> = ({
  project,
  onOpenDictionary
}) => {
  const [activeToken, setActiveToken] = useState<GlossToken>(project.glossTokens[0] || {
    id: 'default',
    word: 'Hello',
    gloss: 'HELLO',
    startTime: 0,
    endTime: 2,
    confidence: 0.99
  });

  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [currentTime, setCurrentTime] = useState<number>(0);

  // Playback timer cycle through tokens
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTime((prev) => {
        const next = prev + 0.1 * playbackSpeed;
        if (next >= project.duration) {
          return 0;
        }

        const found = project.glossTokens.find(
          t => next >= t.startTime && next <= t.endTime
        );
        if (found && found.id !== activeToken.id) {
          setActiveToken(found);
        }

        return next;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, project, activeToken]);

  const handleSelectToken = (token: GlossToken) => {
    setActiveToken(token);
    setCurrentTime(token.startTime);
    setIsPlaying(true);
  };

  const handleSeekTime = (time: number) => {
    setCurrentTime(time);
    const found = project.glossTokens.find(
      t => time >= t.startTime && time <= t.endTime
    );
    if (found) {
      setActiveToken(found);
    }
  };

  const handleReplay = () => {
    setCurrentTime(0);
    if (project.glossTokens[0]) {
      setActiveToken(project.glossTokens[0]);
    }
    setIsPlaying(true);
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Studio Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-4 sm:p-5 rounded-[28px] border border-white/14">
        <div>
          <div className="flex items-center gap-2">
            <span className="glass-badge text-[10px]">3D Studio</span>
            <span className="text-xs text-slate-400 font-mono">Dialect: {project.dialect.toUpperCase()}</span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight mt-1">
            {project.title}
          </h1>
        </div>

        <div className="flex items-center gap-2.5">
          {onOpenDictionary && (
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={onOpenDictionary}
              icon={<BookOpen className="w-3.5 h-3.5 text-slate-300" />}
            >
              ISL Lexicon
            </GlassButton>
          )}
          <span className="glass-badge text-xs">
            {project.accuracy}% Precision
          </span>
        </div>
      </div>

      {/* CENTERPIECE: 3D SIGNAVATAR + TRANSCRIPT PANEL */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* 3D AVATAR WEBGL STAGE (7 COLS) */}
        <div className="lg:col-span-7 space-y-4">
          <SignAvatar3D
            currentSign={activeToken.gloss}
            isPlaying={isPlaying}
            playbackSpeed={playbackSpeed}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
            onSpeedChange={(s) => setPlaybackSpeed(s)}
            height="460px"
          />

          {/* GLOSS TIMELINE */}
          <GlossTimeline
            tokens={project.glossTokens}
            activeTokenId={activeToken.id}
            onSelectToken={handleSelectToken}
            currentTime={currentTime}
            totalDuration={project.duration}
            onSeekTime={handleSeekTime}
          />
        </div>

        {/* RIGHT COLUMN: TRANSCRIPT & ISL SYNTACTIC PANEL (5 COLS) */}
        <div className="lg:col-span-5 space-y-4">
          <TranscriptPanel
            project={project}
            activeTokenId={activeToken.id}
            onReplay={handleReplay}
            onSelectToken={handleSelectToken}
          />

          {/* Real-time Sign Metadata Inspector */}
          <div className="glass-card p-5 rounded-[28px] border border-white/14 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-white" />
              Active Sign Keyframe Inspector
            </h3>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-2xl glass-subtle border border-white/10">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Gloss Token</span>
                <span className="text-sm font-mono font-bold text-white">{activeToken.gloss}</span>
              </div>
              <div className="p-3 rounded-2xl glass-subtle border border-white/10">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Time Span</span>
                <span className="text-xs font-mono text-slate-200">{activeToken.startTime}s – {activeToken.endTime}s</span>
              </div>
              <div className="p-3 rounded-2xl glass-subtle border border-white/10">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Grammar Role</span>
                <span className="text-xs font-bold text-slate-200">{activeToken.grammarTag || 'LEXICAL_SIGN'}</span>
              </div>
              <div className="p-3 rounded-2xl glass-subtle border border-white/10">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Neural Confidence</span>
                <span className="text-xs font-bold text-white">{((activeToken.confidence || 0.98) * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
