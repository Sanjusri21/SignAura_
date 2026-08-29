import React, { useState } from 'react';
import { 
  Sparkles, 
  ArrowRight, 
  Play, 
  Video, 
  Globe2, 
  Cpu, 
  Layers, 
  Zap, 
  CheckCircle2
} from 'lucide-react';
import { SignAvatar3D } from '../components/avatar/SignAvatar3D';
import { NavigationTab } from '../types';
import { GlassButton } from '../components/ui/GlassButton';
import { GlassCard } from '../components/ui/GlassCard';

interface LandingViewProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const LandingView: React.FC<LandingViewProps> = ({ onNavigate }) => {
  const [demoSign, setDemoSign] = useState<string>('WELCOME');
  const [isDemoPlaying, setIsDemoPlaying] = useState<boolean>(true);

  const quickSigns = [
    { label: 'Hello', sign: 'HELLO' },
    { label: 'Welcome', sign: 'WELCOME' },
    { label: 'Thank You', sign: 'THANK_YOU' },
    { label: 'Accessible', sign: 'ACCESSIBLE' },
    { label: 'India', sign: 'INDIA' },
    { label: 'Help', sign: 'HELP' }
  ];

  const features = [
    {
      icon: Cpu,
      title: 'Neural ISL Grammar Engine',
      description: 'Converts English and Hindi syntax into natural Indian Sign Language Subject-Object-Verb (SOV) grammatical structure.'
    },
    {
      icon: Layers,
      title: 'Spatial 3D SignAvatar',
      description: 'Real-time WebGL humanoid with 5-finger articulated joint rigging, spatial lighting reflections, and expressive facial markers.'
    },
    {
      icon: Globe2,
      title: 'Pan-Indian Dialect Matrix',
      description: 'Certified support for Pan-Indian Standard ISL, Northern regional variations, and Southern lexicon adaptations.'
    },
    {
      icon: Zap,
      title: 'Sub-450ms Latency',
      description: 'Whisper AI audio extraction pipeline and parallel keyframe synthesis for broadcast-ready accessibility.'
    }
  ];

  const metrics = [
    { value: '98.7%', label: 'ISL BLEU Accuracy' },
    { value: '15,000+', label: 'Certified ISL Signs' },
    { value: '< 450ms', label: 'Processing Latency' },
    { value: '60 FPS', label: 'Spatial 3D Fidelity' }
  ];

  return (
    <div className="space-y-20 py-4 pb-24">
      {/* 1. HERO SECTION WITH SIGNAVATAR AS THE CENTERPIECE */}
      <section className="relative flex flex-col items-center text-center pt-6 md:pt-10">
        
        {/* Minimal Pill Badge */}
        <div className="glass-subtle px-4 py-1.5 rounded-full inline-flex items-center gap-2 border border-white/16 shadow-md mb-6 backdrop-blur-2xl">
          <Sparkles className="w-3.5 h-3.5 text-white" />
          <span className="text-xs font-semibold tracking-wider text-slate-200">
            Spatial AI Accessibility Technology
          </span>
          <span className="text-[10px] text-white bg-white/12 px-2 py-0.5 rounded-full font-mono font-bold">
            v4.2
          </span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight max-w-4xl text-gradient-spatial leading-[1.08] mb-6">
          Communication without barriers.
        </h1>

        {/* Subtitle */}
        <p className="text-base sm:text-lg md:text-xl text-slate-300 max-w-2xl font-normal leading-relaxed mb-8">
          Transform speech, video, and text into authentic <span className="text-white font-semibold">Indian Sign Language</span> using AI and our interactive 3D SignAvatar.
        </p>

        {/* Hero Actions */}
        <div className="flex flex-wrap items-center justify-center gap-3.5 mb-14">
          <GlassButton
            variant="primary"
            size="lg"
            onClick={() => onNavigate('convert')}
            icon={<ArrowRight className="w-4 h-4" />}
            iconPosition="right"
          >
            Start Converting
          </GlassButton>

          <GlassButton
            variant="secondary"
            size="lg"
            onClick={() => onNavigate('dashboard')}
          >
            Open Dashboard
          </GlassButton>
        </div>

        {/* 2. SPATIAL HOLOGRAPHIC DISPLAY STAGE CONTAINER */}
        <div className="w-full max-w-4xl relative">
          {/* Ambient soft glow beneath avatar stage */}
          <div className="absolute -inset-4 bg-gradient-to-r from-blue-600/20 via-cyan-500/15 to-purple-600/20 rounded-[40px] blur-3xl -z-10" />

          {/* 3D SignAvatar Presentation Stage */}
          <div className="glass-card rounded-[36px] p-4 sm:p-6 border border-white/20 shadow-2xl relative">
            <SignAvatar3D
              currentSign={demoSign}
              isPlaying={isDemoPlaying}
              onTogglePlay={() => setIsDemoPlaying(!isDemoPlaying)}
              height="500px"
            />

            {/* Quick Interactive Gesture Chips */}
            <div className="mt-5 pt-4 border-t border-white/10 flex flex-wrap items-center justify-center gap-2 select-none">
              <span className="text-xs font-semibold text-slate-400 mr-2">Test Live ISL Signs:</span>
              {quickSigns.map((item) => (
                <button
                  key={item.sign}
                  onClick={() => {
                    setDemoSign(item.sign);
                    setIsDemoPlaying(true);
                  }}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                    demoSign === item.sign
                      ? 'bg-white/22 text-white border border-white/35 shadow-[0_0_15px_rgba(255,255,255,0.25)] scale-105'
                      : 'glass-subtle text-slate-300 hover:text-white hover:bg-white/8 border border-white/10'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 3. METRICS ROW */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-5xl mx-auto">
        {metrics.map((m, i) => (
          <GlassCard key={i} className="p-6 text-center rounded-3xl">
            <div className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-1">
              {m.value}
            </div>
            <div className="text-xs sm:text-sm text-slate-400 font-medium">
              {m.label}
            </div>
          </GlassCard>
        ))}
      </section>

      {/* 4. SPATIAL CAPABILITIES GRID */}
      <section className="space-y-8 max-w-5xl mx-auto">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Engineered for Precision & Fluidity
          </h2>
          <p className="text-sm text-slate-400">
            A real-time multimodal AI pipeline bridging speech acoustics, ISL syntax, and spatial 3D kinematics.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {features.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <GlassCard 
                key={idx}
                className="p-6 rounded-3xl flex items-start gap-4 hover:border-white/24"
              >
                <div className="w-11 h-11 rounded-2xl bg-white/10 border border-white/14 flex items-center justify-center flex-shrink-0 shadow-sm">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-base font-bold text-white">
                    {feat.title}
                  </h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    {feat.description}
                  </p>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </section>

      {/* 5. BOTTOM CALL TO ACTION */}
      <section className="max-w-4xl mx-auto">
        <div className="glass-card rounded-[36px] p-8 sm:p-12 border border-white/20 text-center relative overflow-hidden shadow-2xl">
          <div className="max-w-2xl mx-auto space-y-5">
            <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              Make Every Video Accessible
            </h2>
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              Upload lectures, emergency instructions, or conversations to generate real-time Indian Sign Language in seconds.
            </p>
            <div className="pt-3">
              <GlassButton
                variant="primary"
                size="lg"
                onClick={() => onNavigate('convert')}
                icon={<Video className="w-4 h-4 text-slate-900" />}
              >
                Launch Conversion Studio
              </GlassButton>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
