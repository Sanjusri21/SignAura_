import React, { useState } from 'react';
import { 
  Globe, 
  Bell, 
  ChevronDown, 
  Check, 
  Plus
} from 'lucide-react';
import { ISLDialect, NavigationTab } from '../../types';
import { GlassButton } from '../ui/GlassButton';

interface DashboardHeaderProps {
  currentTab: NavigationTab;
  currentDialect: ISLDialect;
  onDialectChange: (dialect: ISLDialect) => void;
  onNavigate: (tab: NavigationTab) => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  currentTab,
  currentDialect,
  onDialectChange,
  onNavigate,
}) => {
  const [showDialectMenu, setShowDialectMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const titleMap: Record<NavigationTab, { title: string; subtitle: string }> = {
    landing: { title: 'SignAura', subtitle: 'AI-Powered Indian Sign Language Accessibility' },
    signin: { title: 'Sign In', subtitle: 'Access your workspace' },
    signup: { title: 'Sign Up', subtitle: 'Create account' },
    'forgot-password': { title: 'Reset Password', subtitle: 'Account recovery' },
    dashboard: { title: 'Dashboard', subtitle: 'AI accessibility operations & pipeline overview' },
    convert: { title: 'Video to ISL', subtitle: 'Synthesize 3D sign keyframes from speech and video' },
    translator: { title: 'Translator', subtitle: 'Convert text into ISL Subject-Object-Verb gloss' },
    avatar: { title: '3D Sign Avatar', subtitle: 'Interactive 3D humanoid avatar motion rig' },
    assistant: { title: 'AI Assistant', subtitle: 'Conversational ISL accessibility copilot' },
    library: { title: 'History & Archive', subtitle: 'Previous conversions, gloss tokens & transcripts' },
    settings: { title: 'Settings & Lexicon', subtitle: 'Accessibility preferences & certified ISL dictionary' },
  };

  const currentInfo = titleMap[currentTab] || { title: 'Dashboard', subtitle: 'SignAura' };

  const dialects: { id: ISLDialect; label: string; desc: string }[] = [
    { id: 'standard', label: 'ISL Standard (National)', desc: 'Pan-Indian standard signs & formal SOV syntax' },
    { id: 'north', label: 'ISL Northern Dialect', desc: 'Regional lexicon variants for North India' },
    { id: 'south', label: 'ISL Southern Dialect', desc: 'Regional lexicon variants for South India' }
  ];

  return (
    <header className="w-full flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 relative z-30 select-none">
      {/* Left: Current Page Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full bg-[#22D3EE] animate-pulse" />
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#22D3EE] font-semibold">
            AI Engine Online
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          {currentInfo.title}
        </h1>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2.5 sm:gap-3 flex-wrap">
        {/* Dialect Selector */}
        <div className="relative">
          <button
            onClick={() => setShowDialectMenu(!showDialectMenu)}
            className="bg-[#151D40] hover:bg-[#1A244D] px-3.5 py-2 rounded-xl text-xs font-medium text-[#A8B2D1] hover:text-white flex items-center gap-2 border border-[#273154] transition-colors"
            aria-expanded={showDialectMenu}
            aria-label="Select ISL dialect"
          >
            <Globe className="w-3.5 h-3.5 text-[#22D3EE]" />
            <span className="capitalize">{currentDialect} ISL</span>
            <ChevronDown className="w-3.5 h-3.5 opacity-60" />
          </button>

          {showDialectMenu && (
            <div className="absolute right-0 mt-2 w-64 bg-[#151D40] rounded-xl p-2 border border-[#273154] shadow-xl z-50 animate-in fade-in duration-150">
              <p className="text-[10px] font-semibold text-[#6B7A99] px-2.5 py-1 uppercase tracking-wider">
                Select Dialect
              </p>
              <div className="space-y-1 mt-1">
                {dialects.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => {
                      onDialectChange(d.id);
                      setShowDialectMenu(false);
                    }}
                    className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors flex items-start justify-between gap-2 ${
                      currentDialect === d.id
                        ? 'bg-[#101735] text-[#22D3EE] font-semibold border border-[#273154]'
                        : 'text-[#A8B2D1] hover:text-white hover:bg-[#1A244D]'
                    }`}
                  >
                    <div>
                      <p className="font-semibold">{d.label}</p>
                      <p className="text-[10px] text-[#6B7A99] leading-tight mt-0.5">{d.desc}</p>
                    </div>
                    {currentDialect === d.id && <Check className="w-3.5 h-3.5 text-[#22D3EE] flex-shrink-0 mt-0.5" />}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Quick Action */}
        <GlassButton
          variant="primary"
          size="sm"
          onClick={() => onNavigate('convert')}
          icon={<Plus className="w-3.5 h-3.5 text-[#080D24]" />}
        >
          New Video
        </GlassButton>
      </div>
    </header>
  );
};
