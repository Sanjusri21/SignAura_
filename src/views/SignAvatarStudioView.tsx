import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  BookOpen,
  Play,
  Pause,
  RotateCcw,
  Camera,
  Layers,
  Activity,
  UserSquare2
} from 'lucide-react';
import { SignAvatar3D, CameraPreset, LightingPreset } from '../components/avatar/SignAvatar3D';
import { GlossTimeline } from '../components/avatar/GlossTimeline';
import { TranscriptPanel } from '../components/avatar/TranscriptPanel';
import { VideoProject, GlossToken } from '../types';
import { GlassButton } from '../components/ui/GlassButton';
import { signAuraApi, SignAvatarResponse } from '../services/api';

const SIGNAVATAR_API_URL = 'http://127.0.0.1:8001';

interface SignAvatarStudioViewProps {
  project: VideoProject;
  onOpenDictionary?: () => void;
}

export const SignAvatarStudioView: React.FC<SignAvatarStudioViewProps> = ({
  project,
  onOpenDictionary
}) => {
  const [activeToken, setActiveToken] = useState<GlossToken>(
    project.glossTokens[0] || {
      id: 'default',
      word: 'Good',
      gloss: 'GOOD',
      startTime: 0,
      endTime: 2,
      confidence: 0.99
    }
  );

  const [currentSignName, setCurrentSignName] = useState<string>('GOOD');
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>('front');
  const [lightingPreset, setLightingPreset] = useState<LightingPreset>('studio');

  // SignAvatar AI generation state
  const [sentence, setSentence] = useState<string>('');
  const [generatedGifUrl, setGeneratedGifUrl] = useState<string>('');
  const [generatedMotionUrl, setGeneratedMotionUrl] = useState<string>(
    `${SIGNAVATAR_API_URL}/motion/good`
  );
  const [motionSegments, setMotionSegments] = useState<{ word: string; frames: number }[]>([]);
  const [motionFps, setMotionFps] = useState(30);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string>('');

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTime((prev) => {
        const next = prev + 0.1 * playbackSpeed;
        if (next >= project.duration) return 0;

        const found = project.glossTokens.find(
          (t) => next >= t.startTime && next <= t.endTime
        );
        if (found && found.id !== activeToken.id) {
          setActiveToken(found);
          setCurrentSignName(found.gloss || 'WELCOME');
        }
        return next;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, project.duration, project.glossTokens, activeToken.id]);

  const handleSelectToken = (token: GlossToken) => {
    setActiveToken(token);
    setCurrentSignName(token.gloss || 'WELCOME');
    setCurrentTime(token.startTime);
    setIsPlaying(true);
  };

  const handleGenerateSentence = async () => {
    if (!sentence.trim()) return;
    setIsGenerating(true);
    setGenerationError('');

    try {
      // Step 8: Call the real translation-to-signavatar sequence pipeline
      const res = await signAuraApi.translateToSignAvatar(sentence.trim());

      if (res.available && res.animation?.animation_url) {
        setGeneratedMotionUrl(res.animation.animation_url);
        setMotionFps(res.animation.fps || 30);
        setCurrentSignName(res.glosses?.join(' ') || sentence.trim());
        if (res.glosses) {
          setMotionSegments(res.glosses.map((g) => ({ word: g, frames: Math.round(res.animation!.frames / res.glosses.length) })));
        }
      } else if (!res.available) {
        setGeneratedMotionUrl('');
        setMotionSegments([]);
        const missingReasons = res.unavailable?.map((u) => `${u.gloss}: ${u.reason}`).join(', ') || res.error || 'Required ISL signs are unavailable';
        setGenerationError(`Sign animation unavailable for: ${missingReasons}`);
      }
    } catch (err: any) {
      setGeneratedMotionUrl('');
      setMotionSegments([]);
      setGenerationError(err?.response?.data?.detail || err?.message || 'Could not generate animation sequence.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6 pb-20 max-w-7xl mx-auto">
      {/* 1. STUDIO HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#151D40] p-5 rounded-2xl border border-[#273154] shadow-md">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#22D3EE] bg-[#101735] px-2.5 py-0.5 rounded border border-[#273154]">
              SMPL-X Rig v2.4
            </span>
            <span className="text-xs text-[#A8B2D1]">60 FPS WebGL Kinematics</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            3D Sign Avatar
          </h1>
        </div>

        {/* Stats Strip */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="bg-[#101735] px-3.5 py-1.5 rounded-xl border border-[#273154] text-left">
            <p className="text-[10px] text-[#A8B2D1] uppercase tracking-wider font-semibold">Current Sign</p>
            <p className="text-xs font-mono font-bold text-[#22D3EE]">{currentSignName || activeToken.gloss || 'WELCOME'}</p>
          </div>

          <div className="bg-[#101735] px-3.5 py-1.5 rounded-xl border border-[#273154] text-left">
            <p className="text-[10px] text-[#A8B2D1] uppercase tracking-wider font-semibold">Motion</p>
            <p className="text-xs font-mono font-bold text-white">183 Frames • 20 FPS</p>
          </div>

          {onOpenDictionary && (
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={onOpenDictionary}
              icon={<BookOpen className="w-4 h-4 text-[#A8B2D1]" />}
            >
              ISL Dictionary
            </GlassButton>
          )}
        </div>
      </div>

      {/* 2. MAIN 3D STAGE & SIDEBAR */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left / Center 3D Stage (8 cols on desktop) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="bg-[#151D40] rounded-2xl border border-[#273154] p-4 shadow-xl relative">
            {/* Embedded 3D Avatar (Untouched Component) */}
            <SignAvatar3D
              currentSign={currentSignName || activeToken.gloss || 'WELCOME'}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying(!isPlaying)}
              playbackSpeed={playbackSpeed}
              onSpeedChange={setPlaybackSpeed}
              motionUrl={generatedMotionUrl}
              motionSegments={motionSegments}
              motionFps={motionFps}
              generatedGifUrl={generatedGifUrl}
              height="500px"
              showISLControls={true}
              onSignChange={(sign) => {
                setCurrentSignName(sign);
                setActiveToken((prev) => ({ ...prev, gloss: sign, word: sign.toLowerCase() }));
              }}
            />
          </div>

          {/* Interactive Timeline */}
          {project.glossTokens && project.glossTokens.length > 0 && (
            <div className="bg-[#151D40] rounded-2xl border border-[#273154] p-4 shadow-md">
              <GlossTimeline
                tokens={project.glossTokens}
                activeTokenId={activeToken.id}
                currentTime={currentTime}
                totalDuration={project.duration}
                onSelectToken={handleSelectToken}
                isPlaying={isPlaying}
                onTogglePlay={() => setIsPlaying(!isPlaying)}
              />
            </div>
          )}
        </div>

        {/* Right Controls Panel (4 cols on desktop) */}
        <div className="lg:col-span-4 space-y-4">
          
          {/* Camera View Controls */}
          <div className="bg-[#151D40] rounded-2xl p-5 border border-[#273154] shadow-md space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
              <Camera className="w-4 h-4 text-[#22D3EE]" />
              <span>Camera Perspective</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {(['front', 'perspective', 'hands', 'top'] as CameraPreset[]).map((preset) => (
                <button
                  key={preset}
                  onClick={() => setCameraPreset(preset)}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold capitalize transition-colors border text-center ${
                    cameraPreset === preset
                      ? 'bg-[#101735] text-[#22D3EE] border-[#22D3EE]'
                      : 'bg-[#101735] text-[#A8B2D1] hover:text-white border-[#273154] hover:bg-[#1A244D]'
                  }`}
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          {/* Text-to-Sign Sentence Generator */}
          <div className="bg-[#151D40] rounded-2xl p-5 border border-[#273154] shadow-md space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-[#8B5CF6]" />
              <span>Text to Sign Sequence</span>
            </div>

            <div className="space-y-2">
              <input
                type="text"
                value={sentence}
                onChange={(e) => setSentence(e.target.value)}
                placeholder="Enter English, Tamil, or concept text..."
                className="w-full bg-[#101735] text-xs py-2.5 px-3 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white placeholder-[#6B7A99] outline-none"
              />

              {/* Verified Demo Presets */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                <span className="text-[10px] text-[#A8B2D1] self-center mr-1">Presets:</span>
                {[
                  { label: 'good drink', text: 'good drink' },
                  { label: 'help teacher', text: 'help teacher' },
                  { label: 'go drink help', text: 'go drink help' },
                  { label: 'hello (missing)', text: 'hello' }
                ].map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => {
                      setSentence(preset.text);
                    }}
                    className="px-2 py-0.5 rounded-lg bg-[#101735] text-[#22D3EE] text-[10px] font-mono border border-[#273154] hover:border-[#22D3EE] transition-colors"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              <GlassButton
                variant="primary"
                size="sm"
                onClick={handleGenerateSentence}
                disabled={isGenerating || !sentence.trim()}
                className="w-full justify-center text-xs font-bold mt-2"
              >
                {isGenerating ? 'Synthesizing BridgeConn Signs...' : 'Generate 3D Signs'}
              </GlassButton>
            </div>

            {generationError && (
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
                <p className="font-semibold">{generationError}</p>
                <p className="text-[10px] text-amber-400/80 mt-0.5">
                  SignAura strictly serves authentic BridgeConn 3D motion captures and never generates fake animations for missing signs.
                </p>
              </div>
            )}

            {motionSegments.length > 0 && (
              <div className="pt-2 border-t border-[#273154] space-y-1.5">
                <p className="text-[11px] font-semibold text-[#A8B2D1]">Generated Motion Tokens:</p>
                <div className="flex flex-wrap gap-1.5">
                  {motionSegments.map((s, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-[#101735] text-[#22D3EE] text-[10px] font-mono font-bold border border-[#273154]"
                    >
                      {s.word} ({s.frames}f)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Transcript Panel */}
          {project.transcript && (
            <div className="bg-[#151D40] rounded-2xl p-5 border border-[#273154] shadow-md">
              <TranscriptPanel
                project={project}
                activeTokenId={activeToken.id}
                onSelectToken={handleSelectToken}
              />
            </div>
          )}

        </div>

      </div>
    </div>
  );
};