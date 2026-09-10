import React, { useState } from 'react';
import { 
  Sparkles, 
  ArrowRight, 
  Video, 
  Globe2, 
  Cpu, 
  Layers, 
  BotMessageSquare,
  Mic,
  UserSquare2,
  CheckCircle2
} from 'lucide-react';
import { Navbar } from '../components/layout/Navbar';
import { SignAvatar3D } from '../components/avatar/SignAvatar3D';
import { NavigationTab } from '../types';
import { GlassButton } from '../components/ui/GlassButton';

interface LandingViewProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const LandingView: React.FC<LandingViewProps> = ({ onNavigate }) => {
  const [demoSign, setDemoSign] = useState<string>('WELCOME');
  const [isDemoPlaying, setIsDemoPlaying] = useState<boolean>(true);

  const quickSigns = [
    { label: 'Welcome', sign: 'WELCOME' },
    { label: 'Hello', sign: 'HELLO' },
    { label: 'Thank You', sign: 'THANK_YOU' },
    { label: 'Help', sign: 'HELP' },
    { label: 'India', sign: 'INDIA' },
  ];

  const features = [
    {
      icon: Video,
      title: 'Video → ISL',
      description: 'Convert spoken video content into Indian Sign Language.',
      actionTab: 'convert' as NavigationTab
    },
    {
      icon: Cpu,
      title: 'AI Translation',
      description: 'Transform speech and text into meaningful ISL sign sequences.',
      actionTab: 'translator' as NavigationTab
    },
    {
      icon: UserSquare2,
      title: '3D Sign Avatar',
      description: 'Visualize sign language through an interactive 3D humanoid avatar.',
      actionTab: 'avatar' as NavigationTab
    },
    {
      icon: Globe2,
      title: 'Universal Accessibility',
      description: 'Designed to make digital media accessible for Deaf and hard-of-hearing users.',
      actionTab: 'settings' as NavigationTab
    },
    {
      icon: BotMessageSquare,
      title: 'AI Chat Assistant',
      description: 'Interact with SignAura AI for real-time sign language queries.',
      actionTab: 'assistant' as NavigationTab
    },
    {
      icon: Mic,
      title: 'Speech Recognition',
      description: 'Transcribe spoken audio directly into Indian Sign Language glosses.',
      actionTab: 'convert' as NavigationTab
    }
  ];

  const workflowSteps = [
    {
      step: '01',
      title: 'Video Input',
      description: 'Upload video media or provide a web stream URL.',
      icon: Video
    },
    {
      step: '02',
      title: 'Speech Recognition',
      description: 'Extract and transcribe spoken audio with Whisper ASR.',
      icon: Mic
    },
    {
      step: '03',
      title: 'ISL Translation',
      description: 'Translate grammar into Subject-Object-Verb (SOV) sign gloss.',
      icon: Cpu
    },
    {
      step: '04',
      title: '3D Sign Motion',
      description: 'Render articulated 3D humanoid avatar keyframes in real time.',
      icon: UserSquare2
    }
  ];

  const metrics = [
    { value: '98.7%', label: 'Translation Accuracy' },
    { value: '15,000+', label: 'ISL Vocabulary Signs' },
    { value: '< 450ms', label: 'Synthesis Latency' },
    { value: '60 FPS', label: '3D Avatar Motion' }
  ];

  return (
    <div className="space-y-20 pb-20">
      {/* Clean Solid Navbar */}
      <Navbar onNavigate={onNavigate} />

      {/* 1. HERO SECTION */}
      <section id="hero" className="max-w-7xl mx-auto pt-4 md:pt-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          {/* Left Hero Content */}
          <div className="lg:col-span-6 space-y-6 text-left">
            {/* Pill Tag */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#101735] border border-[#273154]">
              <Sparkles className="w-3.5 h-3.5 text-[#22D3EE]" />
              <span className="text-xs font-semibold text-white tracking-wide">
                AI-Powered Indian Sign Language Accessibility
              </span>
            </div>

            {/* Main Hero Headline */}
            <div className="space-y-2">
              <span className="text-xs font-bold tracking-widest uppercase text-[#22D3EE]">
                SIGN AURA
              </span>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.12]">
                Breaking communication barriers with <span className="text-[#22D3EE]">AI & 3D Avatars.</span>
              </h1>
            </div>

            {/* Supporting Copy */}
            <p className="text-base sm:text-lg text-[#A8B2D1] leading-relaxed max-w-xl">
              Breaking communication barriers with AI-powered Indian Sign Language translation and interactive 3D avatars.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center gap-3.5 pt-2">
              <GlassButton
                variant="primary"
                size="lg"
                onClick={() => onNavigate('signup')}
                icon={<ArrowRight className="w-4 h-4 text-[#080D24]" />}
                iconPosition="right"
              >
                Get Started
              </GlassButton>

              <GlassButton
                variant="secondary"
                size="lg"
                onClick={() => {
                  const el = document.getElementById('avatar-interactive-section');
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                Explore SignAura
              </GlassButton>
            </div>

            {/* Trust Indicators */}
            <div className="flex items-center gap-4 pt-4 border-t border-[#273154] text-xs text-[#A8B2D1]">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#22D3EE]" />
                <span>ISL SOV Syntax</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#22D3EE]" />
                <span>SMPL-X Kinematics</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#22D3EE]" />
                <span>Web-Standard</span>
              </div>
            </div>
          </div>

          {/* Right Hero Stage: Live 3D Avatar Container */}
          <div className="lg:col-span-6" id="avatar-interactive-section">
            <div className="bg-[#151D40] rounded-2xl border border-[#273154] p-4 shadow-xl">
              <div className="flex items-center justify-between pb-3 mb-2 border-b border-[#273154] px-1">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#22D3EE] animate-pulse" />
                  <span className="text-xs font-bold text-white tracking-wide">3D Sign Avatar Preview</span>
                </div>
                <span className="text-[11px] font-mono font-bold text-[#22D3EE] bg-[#101735] px-2.5 py-0.5 rounded-md border border-[#273154]">
                  Sign: {demoSign}
                </span>
              </div>

              {/* Working 3D Avatar (Unchanged component, cleanly housed) */}
              <SignAvatar3D
                currentSign={demoSign}
                isPlaying={isDemoPlaying}
                onTogglePlay={() => setIsDemoPlaying(!isDemoPlaying)}
                height="420px"
              />

              {/* Quick Interactive Gesture Buttons */}
              <div className="mt-3 pt-3 border-t border-[#273154] flex flex-wrap items-center justify-center gap-1.5 select-none">
                <span className="text-xs font-semibold text-[#A8B2D1] mr-1">Try Sign:</span>
                {quickSigns.map((item) => (
                  <button
                    key={item.sign}
                    onClick={() => {
                      setDemoSign(item.sign);
                      setIsDemoPlaying(true);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      demoSign === item.sign
                        ? 'bg-[#22D3EE] text-[#080D24] shadow-sm'
                        : 'bg-[#101735] text-[#A8B2D1] hover:text-white hover:bg-[#1A244D] border border-[#273154]'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* 2. METRICS ROW */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-6xl mx-auto">
        {metrics.map((m, i) => (
          <div key={i} className="bg-[#151D40] border border-[#273154] rounded-2xl p-5 text-center shadow-md">
            <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-1">
              {m.value}
            </div>
            <div className="text-xs text-[#A8B2D1] font-medium">
              {m.label}
            </div>
          </div>
        ))}
      </section>

      {/* 3. FEATURE CARDS (Solid #151D40 Background, Subtle #273154 Border, Hover Lift) */}
      <section id="features" className="space-y-8 max-w-6xl mx-auto pt-4">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-[#22D3EE]">
            Platform Features
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Universal AI Accessibility Suite
          </h2>
          <p className="text-sm text-[#A8B2D1]">
            Transform multimedia content into accurate, natural Indian Sign Language representations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <div 
                key={idx}
                onClick={() => onNavigate(feat.actionTab)}
                className="bg-[#151D40] border border-[#273154] rounded-2xl p-6 flex flex-col justify-between hover:border-[#3B4975] hover:-translate-y-1 transition-all duration-200 cursor-pointer group shadow-md"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[#22D3EE] font-bold text-sm">✦</span>
                    <div className="w-10 h-10 rounded-xl bg-[#101735] border border-[#273154] flex items-center justify-center text-[#22D3EE] group-hover:scale-105 transition-transform">
                      <Icon className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-base font-bold text-white group-hover:text-[#22D3EE] transition-colors">
                      {feat.title}
                    </h3>
                    <p className="text-sm text-[#A8B2D1] leading-relaxed">
                      {feat.description}
                    </p>
                  </div>
                </div>

                <div className="pt-4 mt-4 border-t border-[#273154] flex items-center text-xs font-semibold text-[#22D3EE] group-hover:translate-x-0.5 transition-transform">
                  <span>Learn more</span>
                  <span className="ml-1">→</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. HOW IT WORKS 4-STEP PIPELINE */}
      <section id="how-it-works" className="space-y-8 max-w-6xl mx-auto pt-4">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-[#6366F1]">
            Workflow Architecture
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            How SignAura Works
          </h2>
          <p className="text-sm text-[#A8B2D1]">
            From raw media to 60 FPS articulated sign language keyframes in four synchronized steps.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {workflowSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div key={idx} className="bg-[#151D40] border border-[#273154] rounded-2xl p-5 flex flex-col justify-between hover:border-[#3B4975] transition-colors shadow-md">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-extrabold font-mono text-[#22D3EE]">
                      {step.step}
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-[#101735] border border-[#273154] flex items-center justify-center text-white">
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>

                  <h3 className="text-sm font-bold text-white pt-1">
                    {step.title}
                  </h3>
                  <p className="text-xs text-[#A8B2D1] leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 5. ABOUT SECTION */}
      <section id="about" className="max-w-6xl mx-auto pt-4">
        <div className="bg-[#151D40] rounded-2xl p-8 sm:p-10 border border-[#273154] shadow-lg">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-8 space-y-4">
              <span className="text-xs font-bold uppercase tracking-wider text-[#22D3EE]">
                Accessibility Mission
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Empowering India's Deaf & Hard-of-Hearing Community
              </h2>
              <p className="text-sm text-[#A8B2D1] leading-relaxed">
                SignAura bridges linguistic disparities across educational institutions, broadcast media, and digital services with standardized Indian Sign Language kinematics.
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <div className="bg-[#101735] px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs text-[#A8B2D1] border border-[#273154]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>Subject-Object-Verb (SOV) Grammar</span>
                </div>
                <div className="bg-[#101735] px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs text-[#A8B2D1] border border-[#273154]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#22D3EE]" />
                  <span>SMPL-X 3D Rig</span>
                </div>
                <div className="bg-[#101735] px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs text-[#A8B2D1] border border-[#273154]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#8B5CF6]" />
                  <span>Pan-Indian Lexicon</span>
                </div>
              </div>
            </div>

            <div className="lg:col-span-4 flex justify-center">
              <div className="w-full bg-[#101735] rounded-xl p-6 border border-[#273154] text-center space-y-3">
                <h4 className="text-sm font-bold text-white">Get Started with SignAura</h4>
                <p className="text-xs text-[#A8B2D1]">
                  Convert your first video or test sign language sentences in our 3D Studio.
                </p>
                <GlassButton
                  variant="primary"
                  size="sm"
                  onClick={() => onNavigate('signup')}
                  className="w-full justify-center"
                >
                  Create Free Account
                </GlassButton>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. BOTTOM CTA */}
      <section className="max-w-4xl mx-auto text-center">
        <div className="bg-[#151D40] rounded-2xl p-8 sm:p-10 border border-[#273154] shadow-xl space-y-5">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Ready to make digital content accessible?
          </h2>
          <p className="text-sm text-[#A8B2D1] max-w-xl mx-auto">
            Join educators, developers, and organizations utilizing SignAura for automated Indian Sign Language translation.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <GlassButton
              variant="primary"
              size="lg"
              onClick={() => onNavigate('signup')}
              icon={<ArrowRight className="w-4 h-4 text-[#080D24]" />}
              iconPosition="right"
            >
              Get Started Now
            </GlassButton>
            <GlassButton
              variant="secondary"
              size="lg"
              onClick={() => onNavigate('signin')}
            >
              Sign In
            </GlassButton>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="max-w-6xl mx-auto pt-8 border-t border-[#273154] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#A8B2D1]">
        <p>© {new Date().getFullYear()} SignAura. AI-Powered Indian Sign Language Accessibility.</p>
        <div className="flex items-center gap-4">
          <button onClick={() => onNavigate('settings')} className="hover:text-white transition-colors">Accessibility Standards</button>
          <button onClick={() => onNavigate('settings')} className="hover:text-white transition-colors">Lexicon</button>
          <button onClick={() => onNavigate('signin')} className="hover:text-white transition-colors">Sign In</button>
        </div>
      </footer>
    </div>
  );
};
