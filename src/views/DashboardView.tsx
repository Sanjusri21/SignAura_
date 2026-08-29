import React from 'react';
import { 
  Sparkles, 
  Upload, 
  Link2, 
  TrendingUp, 
  Video, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  Play, 
  Activity, 
  BotMessageSquare,
  Layers,
  UserSquare2,
  FileText
} from 'lucide-react';
import { VideoProject, NavigationTab } from '../types';
import { SignAvatar3D } from '../components/avatar/SignAvatar3D';
import { GlassButton } from '../components/ui/GlassButton';
import { GlassCard } from '../components/ui/GlassCard';

interface DashboardViewProps {
  projects: VideoProject[];
  onNavigate: (tab: NavigationTab) => void;
  onSelectProject: (project: VideoProject) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  projects,
  onNavigate,
  onSelectProject
}) => {
  return (
    <div className="space-y-8 pb-16">
      {/* 1. GREETING HEADER */}
      <section className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">👋</span>
            <p className="text-xs uppercase tracking-wider font-semibold text-slate-400">Welcome Back</p>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            Good afternoon, Dr. Sanju
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Indian Sign Language neural models are operating at full 60 FPS accuracy.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <GlassButton
            variant="primary"
            size="md"
            onClick={() => onNavigate('convert')}
            icon={<Upload className="w-4 h-4 text-slate-900" />}
          >
            Upload Media
          </GlassButton>

          <GlassButton
            variant="secondary"
            size="md"
            onClick={() => onNavigate('avatar')}
            icon={<UserSquare2 className="w-4 h-4 text-slate-300" />}
          >
            Open 3D Studio
          </GlassButton>
        </div>
      </section>

      {/* 2. ASYMMETRIC HERO SPLIT: START CONVERSION + LIVE SIGNAVATAR */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT (7 COLS): START CONVERSION PORTAL */}
        <div className="lg:col-span-7 flex flex-col justify-between glass-card p-6 sm:p-8 rounded-[32px] border border-white/16 shadow-2xl relative overflow-hidden">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="glass-badge text-xs">Fast Ingestion</span>
              <span className="text-xs font-mono text-slate-400">ISL SOV Ready</span>
            </div>

            <div className="space-y-2 max-w-lg">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Start Neural Conversion
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Drop your video lecture, speech audio, or past recordings to extract semantic tokens and generate synchronized 3D sign keyframes.
              </p>
            </div>
          </div>

          {/* Direct Input Triggers */}
          <div className="pt-6 space-y-3">
            <div 
              onClick={() => onNavigate('convert')}
              className="p-4 rounded-2xl glass-subtle hover:bg-white/10 border border-white/12 hover:border-white/25 transition-all cursor-pointer flex items-center justify-between group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-white group-hover:scale-105 transition-transform">
                  <Upload className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Upload Video or Audio File</h3>
                  <p className="text-xs text-slate-400">Supports MP4, MOV, WEBM, WAV</p>
                </div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
            </div>

            <div 
              onClick={() => onNavigate('convert')}
              className="p-4 rounded-2xl glass-subtle hover:bg-white/10 border border-white/12 hover:border-white/25 transition-all cursor-pointer flex items-center justify-between group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-white group-hover:scale-105 transition-transform">
                  <Link2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Paste Video Link (YouTube, Loom)</h3>
                  <p className="text-xs text-slate-400">Direct neural stream ingestion</p>
                </div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
            </div>
          </div>
        </div>

        {/* RIGHT (5 COLS): SIGNAVATAR LIVE PREVIEW STAGE */}
        <div className="lg:col-span-5 flex flex-col glass-card p-4 rounded-[32px] border border-white/16 shadow-2xl relative">
          <div className="flex items-center justify-between px-2 py-1 mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-white" />
              <h3 className="text-sm font-bold text-white">SignAvatar 3D Preview</h3>
            </div>
            <button
              onClick={() => onNavigate('avatar')}
              className="text-xs text-slate-300 hover:text-white flex items-center gap-1 font-semibold"
            >
              <span>Full Studio</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 rounded-[24px] overflow-hidden min-h-[300px]">
            <SignAvatar3D
              currentSign="WELCOME"
              isPlaying={true}
              height="320px"
            />
          </div>
        </div>

      </section>

      {/* 3. ASYMMETRIC METRICS & RECENT ACTIVITY GRID */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* RECENT VIDEO CONVERSIONS QUEUE (8 COLS) */}
        <div className="lg:col-span-8 glass-card p-6 sm:p-7 rounded-[32px] border border-white/14 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Video className="w-4 h-4 text-slate-300" />
                Recent Video Conversions
              </h2>
              <p className="text-xs text-slate-400">Processed videos with generated ISL sign sequences</p>
            </div>

            <button
              onClick={() => onNavigate('library')}
              className="text-xs text-slate-300 hover:text-white font-semibold flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Project List */}
          <div className="space-y-2.5">
            {projects.slice(0, 3).map((proj) => (
              <div
                key={proj.id}
                onClick={() => {
                  onSelectProject(proj);
                  onNavigate('avatar');
                }}
                className="p-3.5 rounded-2xl glass-subtle hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center text-white flex-shrink-0 group-hover:scale-105 transition-transform">
                    <Play className="w-4 h-4 ml-0.5" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-white group-hover:text-slate-100 transition-colors truncate">
                      {proj.title}
                    </h3>
                    <p className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                      <span>{proj.createdAt}</span>
                      <span>•</span>
                      <span>{proj.duration}s</span>
                      <span>•</span>
                      <span>{proj.glossTokens.length} ISL signs</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 self-end sm:self-center">
                  <span className="glass-badge text-[10px]">
                    {proj.accuracy}% Accuracy
                  </span>
                  <GlassButton variant="cyan" size="sm">
                    Launch
                  </GlassButton>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ASYMMETRIC STATS & COPILOT CARD (4 COLS) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Quick Metrics Capsule */}
          <div className="grid grid-cols-2 gap-3">
            <GlassCard className="p-4 rounded-2xl text-center">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1">
                Conversions
              </span>
              <span className="text-2xl font-extrabold text-white">124</span>
              <span className="text-[10px] text-emerald-400 block mt-0.5">+14% this month</span>
            </GlassCard>

            <GlassCard className="p-4 rounded-2xl text-center">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-1">
                Time Saved
              </span>
              <span className="text-2xl font-extrabold text-white">18.4h</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Automated ISL</span>
            </GlassCard>
          </div>

          {/* AI Copilot Quick Launcher */}
          <div className="glass-card p-5 rounded-[28px] border border-white/14 space-y-3">
            <div className="flex items-center gap-2">
              <BotMessageSquare className="w-4 h-4 text-white" />
              <h3 className="text-sm font-bold text-white">SignAura AI Copilot</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Have questions about Indian Sign Language grammar rules or syntax? Ask our real-time copilot.
            </p>
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={() => onNavigate('assistant')}
              className="w-full justify-center"
            >
              Ask ISL Question
            </GlassButton>
          </div>
        </div>

      </section>
    </div>
  );
};
