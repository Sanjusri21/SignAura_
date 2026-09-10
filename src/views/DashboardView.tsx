import React from 'react';
import { 
  Upload, 
  Languages, 
  UserSquare2, 
  BotMessageSquare, 
  Video, 
  TrendingUp, 
  Clock, 
  ArrowUpRight, 
  Play, 
  Layers,
  Activity
} from 'lucide-react';
import { VideoProject, NavigationTab } from '../types';
import { useAuth } from '../context/AuthContext';
import { GlassButton } from '../components/ui/GlassButton';
import { StatusBadge } from '../components/ui/StatusBadge';

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
  const { user } = useAuth();

  const stats = [
    {
      title: 'Videos Processed',
      value: `${projects.length}`,
      trend: '+12% this week',
      icon: Video,
      color: 'text-[#22D3EE]'
    },
    {
      title: 'Translations',
      value: '1,420+',
      trend: 'ISL SOV Certified',
      icon: Languages,
      color: 'text-[#8B5CF6]'
    },
    {
      title: 'Sign Sequences',
      value: '15,800',
      trend: '60 FPS 3D Keyframes',
      icon: Layers,
      color: 'text-[#10B981]'
    },
    {
      title: 'Recent Activity',
      value: 'Active',
      trend: 'Whisper ASR Live',
      icon: Activity,
      color: 'text-[#F59E0B]'
    }
  ];

  const actionCards = [
    {
      id: 'convert' as NavigationTab,
      title: 'Video to ISL',
      description: 'Upload video or paste URLs to synthesize synchronized Indian Sign Language 3D animations.',
      icon: Video,
      badge: 'Video Ingest',
    },
    {
      id: 'translator' as NavigationTab,
      title: 'ISL Translator',
      description: 'Convert English and Hindi text into syntactic Subject-Object-Verb (SOV) sign sequences.',
      icon: Languages,
      badge: 'NLP Engine',
    },
    {
      id: 'avatar' as NavigationTab,
      title: '3D Avatar Studio',
      description: 'Interact with articulated 3D humanoid avatar keyframes, camera angles, and motions.',
      icon: UserSquare2,
      badge: '3D Rig',
    },
    {
      id: 'assistant' as NavigationTab,
      title: 'AI Assistant',
      description: 'Consult the AI accessibility copilot for real-time sign language lookups and guidance.',
      icon: BotMessageSquare,
      badge: 'AI Copilot',
    }
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* 1. GREETING HEADER */}
      <section className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-semibold text-[#A8B2D1]">
              Welcome back
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            {user?.full_name ? `Welcome back, ${user.full_name}` : 'Welcome back'}
          </h1>
          <p className="text-[#A8B2D1] text-sm mt-1">
            Make digital content accessible with SignAura.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <GlassButton
            variant="primary"
            size="md"
            onClick={() => onNavigate('convert')}
            icon={<Upload className="w-4 h-4 text-[#080D24]" />}
          >
            Upload Video
          </GlassButton>

          <GlassButton
            variant="secondary"
            size="md"
            onClick={() => onNavigate('avatar')}
            icon={<UserSquare2 className="w-4 h-4 text-[#A8B2D1]" />}
          >
            3D Avatar
          </GlassButton>
        </div>
      </section>

      {/* 2. STATISTIC METRIC CARDS (Solid Dark Cards) */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-[#151D40] border border-[#273154] p-5 rounded-2xl flex flex-col justify-between shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#A8B2D1]">{stat.title}</span>
                <div className="w-8 h-8 rounded-lg bg-[#101735] border border-[#273154] flex items-center justify-center">
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </div>
              </div>

              <div className="mt-3">
                <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {stat.value}
                </div>
                <div className="text-[11px] text-[#A8B2D1] mt-0.5 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3 text-[#22D3EE]" />
                  <span>{stat.trend}</span>
                </div>
              </div>
            </div>
          );
        })}
      </section>

      {/* 3. MAIN ACTION HUBS */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white tracking-tight">
            Quick Actions
          </h2>
          <span className="text-xs text-[#A8B2D1]">Select an accessibility tool</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {actionCards.map((action) => {
            const Icon = action.icon;
            return (
              <div
                key={action.id}
                onClick={() => onNavigate(action.id)}
                className="bg-[#151D40] p-5 rounded-2xl border border-[#273154] hover:border-[#3B4975] hover:-translate-y-0.5 cursor-pointer group transition-all duration-200 flex flex-col justify-between shadow-md"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl bg-[#101735] border border-[#273154] flex items-center justify-center text-[#22D3EE] group-hover:scale-105 transition-transform">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-semibold text-[#A8B2D1] bg-[#101735] px-2 py-0.5 rounded-md border border-[#273154]">
                      {action.badge}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-white group-hover:text-[#22D3EE] transition-colors flex items-center justify-between">
                      <span>{action.title}</span>
                      <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-[#22D3EE]" />
                    </h3>
                    <p className="text-xs text-[#A8B2D1] leading-relaxed">
                      {action.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. RECENT ACTIVITY & MEDIA ARCHIVE PREVIEW */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-white tracking-tight">
              Recent Activity
            </h2>
            <span className="text-xs font-semibold text-[#A8B2D1] bg-[#101735] px-2.5 py-0.5 rounded-md border border-[#273154]">
              {projects.length} Saved
            </span>
          </div>

          <button
            onClick={() => onNavigate('library')}
            className="text-xs font-semibold text-[#22D3EE] hover:text-[#38BDF8] transition-colors flex items-center gap-1"
          >
            <span>View Full Archive</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.slice(0, 3).map((proj) => (
            <div
              key={proj.id}
              className="bg-[#151D40] p-5 rounded-2xl border border-[#273154] flex flex-col justify-between group hover:border-[#3B4975] transition-all shadow-md"
            >
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

                {/* Tokens pill sequence preview */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {proj.glossTokens.slice(0, 4).map((t) => (
                    <span
                      key={t.id}
                      className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-[#101735] text-[#A8B2D1] border border-[#273154]"
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
              </div>

              <div className="pt-3 mt-3 border-t border-[#273154] flex items-center justify-between text-xs text-[#A8B2D1]">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{proj.duration}s</span>
                </div>

                <button
                  onClick={() => {
                    onSelectProject(proj);
                    onNavigate('avatar');
                  }}
                  className="text-xs font-semibold text-white hover:text-[#22D3EE] flex items-center gap-1 transition-colors"
                >
                  <Play className="w-3.5 h-3.5 text-[#22D3EE]" />
                  <span>Play 3D Avatar</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
