import React, { useState } from 'react';
import { 
  Globe, 
  Bell, 
  Sparkles, 
  ChevronDown, 
  Check, 
  Zap,
  Sliders,
  ShieldCheck
} from 'lucide-react';
import { ISLDialect, NavigationTab } from '../../types';
import { GlassButton } from '../ui/GlassButton';

interface GlassHeaderProps {
  currentDialect: ISLDialect;
  onDialectChange: (dialect: ISLDialect) => void;
  onNavigate: (tab: NavigationTab) => void;
  onOpenSettings: () => void;
}

export const GlassHeader: React.FC<GlassHeaderProps> = ({
  currentDialect,
  onDialectChange,
  onNavigate,
  onOpenSettings
}) => {
  const [showDialectMenu, setShowDialectMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const dialects: { id: ISLDialect; label: string; desc: string }[] = [
    { id: 'standard', label: 'ISL Standard (National)', desc: 'Pan-Indian standard signs & formal SOV syntax' },
    { id: 'north', label: 'ISL Northern Dialect', desc: 'Regional lexicon variants for Delhi NCR, Punjab, UP' },
    { id: 'south', label: 'ISL Southern Dialect', desc: 'Lexicon adaptations for Tamil Nadu, Karnataka, Kerala' }
  ];

  return (
    <header className="w-full flex items-center justify-between gap-4 mb-8 relative z-30 select-none">
      {/* Left Minimal Floating Brand Pill */}
      <div className="flex items-center gap-3">
        <div className="glass-subtle px-3.5 py-1.5 rounded-full flex items-center gap-2.5 border border-white/14 shadow-sm hover:border-white/25 transition-all">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
            <span>SignAura</span>
            <span className="text-slate-500">•</span>
            <span className="text-slate-300 font-normal">AI Accessibility</span>
          </div>
          <span className="hidden sm:inline-block text-[10px] font-mono font-bold text-slate-300 bg-white/10 px-1.5 py-0.5 rounded-md">
            v4.2
          </span>
        </div>
      </div>

      {/* Right Floating Minimal Glass Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Dialect Selector Floating Pill */}
        <div className="relative">
          <button
            onClick={() => setShowDialectMenu(!showDialectMenu)}
            className="glass-subtle hover:bg-white/10 px-3 py-1.5 rounded-full text-xs font-medium text-slate-200 flex items-center gap-2 border border-white/14 transition-all shadow-sm"
          >
            <Globe className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden sm:inline text-slate-400">Dialect:</span>
            <span className="font-semibold text-white capitalize">{currentDialect}</span>
            <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform ${showDialectMenu ? 'rotate-180' : ''}`} />
          </button>

          {showDialectMenu && (
            <div className="absolute right-0 mt-2 w-72 glass-prominent rounded-2xl p-2 border border-white/20 shadow-2xl backdrop-blur-3xl z-50 animate-in fade-in zoom-in-95 duration-150">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1.5">
                Select ISL Grammar Variant
              </p>
              <div className="space-y-1">
                {dialects.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => {
                      onDialectChange(d.id);
                      setShowDialectMenu(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-xl text-xs transition-all flex items-start justify-between ${
                      currentDialect === d.id
                        ? 'bg-white/15 border border-white/25 text-white'
                        : 'text-slate-300 hover:bg-white/8'
                    }`}
                  >
                    <div>
                      <p className="font-semibold text-white">{d.label}</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">{d.desc}</p>
                    </div>
                    {currentDialect === d.id && (
                      <Check className="w-3.5 h-3.5 text-white mt-0.5 flex-shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="glass-subtle hover:bg-white/10 p-2 rounded-full text-slate-300 hover:text-white border border-white/14 transition-all relative"
            title="System Updates"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#38bdf8]" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 glass-prominent rounded-2xl p-3 border border-white/20 shadow-2xl backdrop-blur-3xl z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-2 border-b border-white/10 mb-2">
                <span className="text-xs font-bold text-white">System Notifications</span>
                <span className="text-[10px] text-cyan-300 bg-cyan-500/20 px-2 py-0.5 rounded-full font-semibold">2 New</span>
              </div>
              <div className="space-y-2">
                <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-xs">
                  <p className="font-semibold text-white flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-cyan-300" /> 3D SignAvatar Rig v2.4 Active
                  </p>
                  <p className="text-[11px] text-slate-300 mt-0.5">High-fidelity 5-finger articulated signs are now live at 60 FPS.</p>
                </div>
                <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-xs">
                  <p className="font-semibold text-white flex items-center gap-1.5">
                    <Zap className="w-3 h-3 text-purple-300" /> Fast Neural Audio Transcription
                  </p>
                  <p className="text-[11px] text-slate-300 mt-0.5">Whisper AI processing latency reduced to 420ms.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick New Conversion Button */}
        <GlassButton
          variant="primary"
          size="sm"
          onClick={() => onNavigate('convert')}
          icon={<Sparkles className="w-3.5 h-3.5 text-slate-900" />}
          className="hidden sm:inline-flex"
        >
          New Conversion
        </GlassButton>

        {/* Quick Settings Action */}
        <button
          onClick={onOpenSettings}
          className="glass-subtle hover:bg-white/10 p-2 rounded-full text-slate-300 hover:text-white border border-white/14 transition-all"
          title="Accessibility & Render Settings"
          aria-label="Settings"
        >
          <Sliders className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
