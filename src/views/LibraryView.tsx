import React, { useState } from 'react';
import { 
  Film, 
  Search, 
  Play, 
  Calendar, 
  Sparkles, 
  X,
  UserSquare2
} from 'lucide-react';
import { VideoProject, NavigationTab } from '../types';
import { SignAvatar3D } from '../components/avatar/SignAvatar3D';
import { GlassButton } from '../components/ui/GlassButton';

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
  const [previewProject, setPreviewProject] = useState<VideoProject | null>(null);

  const filteredProjects = projects.filter((p) => {
    const matchesSearch = p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.transcript.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDialect = filterDialect === 'all' || p.dialect === filterDialect;
    return matchesSearch && matchesDialect;
  });

  return (
    <div className="space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Video Library</h1>
            <span className="glass-badge text-xs">{projects.length} Processed</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Archive of your converted media with generated Indian Sign Language translations
          </p>
        </div>

        <GlassButton
          variant="primary"
          size="sm"
          onClick={() => onNavigate('convert')}
          icon={<Sparkles className="w-3.5 h-3.5 text-slate-900" />}
        >
          Convert New Video
        </GlassButton>
      </div>

      {/* Search & Filter Glass Bar */}
      <div className="glass-card p-3 rounded-[24px] border border-white/14 flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by title, keywords, or transcript content..."
            className="w-full glass-input text-xs pl-10 pr-4 py-2 rounded-xl border-none shadow-none bg-black/30"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={filterDialect}
            onChange={(e) => setFilterDialect(e.target.value)}
            className="glass-input text-xs py-2 px-3 rounded-xl bg-black/40 text-white w-full sm:w-auto"
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
            className="glass-card p-5 rounded-[28px] border border-white/14 flex flex-col justify-between group hover:border-white/25 transition-all duration-300 shadow-xl"
          >
            {/* Card Stage Thumbnail */}
            <div className="relative rounded-2xl h-36 bg-gradient-to-br from-white/8 via-white/4 to-transparent border border-white/10 overflow-hidden flex items-center justify-center mb-4 group-hover:shadow-[0_0_24px_rgba(255,255,255,0.1)] transition-all">
              <div className="w-11 h-11 rounded-2xl bg-white/14 border border-white/20 flex items-center justify-center text-white shadow-lg group-hover:scale-110 transition-transform">
                <Play className="w-4 h-4 ml-0.5" />
              </div>

              {/* Badges */}
              <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-black/60 text-white border border-white/10 backdrop-blur-md">
                  {proj.duration}s
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/10 text-slate-200 border border-white/10 backdrop-blur-md uppercase">
                  {proj.dialect}
                </span>
              </div>

              <div className="absolute bottom-2.5 right-2.5">
                <span className="glass-badge text-[10px]">
                  {proj.accuracy}% Precision
                </span>
              </div>
            </div>

            {/* Title & Info */}
            <div className="space-y-2 mb-4 flex-1">
              <h3 className="text-sm font-bold text-white group-hover:text-slate-100 transition-colors line-clamp-1">
                {proj.title}
              </h3>
              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                "{proj.transcript}"
              </p>
              <div className="flex items-center gap-2 text-[11px] text-slate-400 pt-1">
                <Calendar className="w-3.5 h-3.5" />
                <span>{proj.createdAt}</span>
                <span>•</span>
                <span className="text-white font-medium">{proj.glossTokens.length} ISL signs</span>
              </div>
            </div>

            {/* Actions Footer */}
            <div className="pt-3 border-t border-white/10 flex items-center justify-between gap-2">
              <GlassButton
                variant="secondary"
                size="sm"
                onClick={() => setPreviewProject(proj)}
                className="flex-1"
              >
                Quick Preview
              </GlassButton>

              <GlassButton
                variant="primary"
                size="sm"
                onClick={() => {
                  onSelectProject(proj);
                  onNavigate('avatar');
                }}
                className="flex-1"
              >
                Launch Studio
              </GlassButton>
            </div>
          </div>
        ))}
      </div>

      {/* QUICK PREVIEW MODAL */}
      {previewProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-2xl">
          <div className="glass-prominent rounded-[36px] p-6 max-w-3xl w-full border border-white/20 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div>
                <h2 className="text-base font-bold text-white">{previewProject.title}</h2>
                <p className="text-xs text-slate-400">Synchronized 3D SignAvatar + ISL Gloss Preview</p>
              </div>

              <button
                onClick={() => setPreviewProject(null)}
                className="p-2 rounded-xl glass-subtle text-slate-400 hover:text-white border border-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <SignAvatar3D
              currentSign={previewProject.glossTokens[0]?.gloss || 'WELCOME'}
              isPlaying={true}
              height="320px"
            />

            <div className="p-3 rounded-2xl bg-black/40 border border-white/10 flex flex-wrap gap-2 text-xs font-mono text-white">
              {previewProject.glossTokens.map((t) => (
                <span key={t.id} className="px-2 py-0.5 rounded-lg bg-white/6 border border-white/10">
                  {t.gloss}
                </span>
              ))}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <GlassButton
                variant="secondary"
                size="sm"
                onClick={() => setPreviewProject(null)}
              >
                Close
              </GlassButton>
              <GlassButton
                variant="primary"
                size="sm"
                onClick={() => {
                  onSelectProject(previewProject);
                  setPreviewProject(null);
                  onNavigate('avatar');
                }}
              >
                Launch Studio
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
