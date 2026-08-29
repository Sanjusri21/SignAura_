import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  LayoutDashboard, 
  Video, 
  UserSquare2, 
  BotMessageSquare, 
  Film, 
  Settings, 
  Compass,
  User
} from 'lucide-react';
import { NavigationTab } from '../../types';
import { GlassTooltip } from '../ui/GlassTooltip';

interface GlassNavigationRailProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
}

export const GlassNavigationRail: React.FC<GlassNavigationRailProps> = ({
  activeTab,
  onSelectTab
}) => {
  const mainNavItems: { id: NavigationTab; label: string; icon: React.FC<{ className?: string }>; badge?: string }[] = [
    { id: 'landing', label: 'Explore', icon: Compass },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'convert', label: 'Convert Media', icon: Video, badge: 'AI' },
    { id: 'avatar', label: 'SignAvatar 3D Studio', icon: UserSquare2, badge: '3D' },
    { id: 'assistant', label: 'ISL Copilot', icon: BotMessageSquare },
    { id: 'library', label: 'Video Archive', icon: Film },
  ];

  return (
    <>
      {/* DESKTOP & TABLET: COMPACT FLOATING NAVIGATION RAIL */}
      <aside
        className="fixed left-5 top-1/2 -translate-y-1/2 z-40 hidden md:flex flex-col items-center select-none"
        aria-label="Spatial Navigation Rail"
      >
        <div className="rounded-[28px] glass-medium p-2 flex flex-col items-center gap-4 border border-white/14 shadow-[0_16px_40px_rgba(0,0,0,0.5)] backdrop-blur-3xl relative">
          
          {/* Subtle Top Specular Sheen */}
          <div className="absolute top-0 left-3 right-3 h-[1px] bg-gradient-to-r from-transparent via-white/30 to-transparent pointer-events-none" />

          {/* Top Logo / Brand Sparkle */}
          <GlassTooltip content="SignAura AI" position="right">
            <button
              onClick={() => onSelectTab('landing')}
              className="w-11 h-11 rounded-2xl bg-white/10 hover:bg-white/15 flex items-center justify-center border border-white/18 shadow-md transition-all group active:scale-95"
              aria-label="Home"
            >
              <Sparkles className="w-5 h-5 text-white group-hover:rotate-12 transition-transform duration-300" />
            </button>
          </GlassTooltip>

          {/* Divider */}
          <div className="w-6 h-[1px] bg-white/10" />

          {/* Main Icon Navigation Rail */}
          <nav className="flex flex-col items-center gap-1.5" aria-label="Main Pages">
            {mainNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <GlassTooltip key={item.id} content={item.label} position="right">
                  <button
                    onClick={() => onSelectTab(item.id)}
                    className={`relative w-11 h-11 rounded-2xl flex items-center justify-center transition-all duration-200 group outline-none ${
                      isActive
                        ? 'text-white'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-white/6'
                    }`}
                    aria-label={item.label}
                  >
                    {/* Active Illuminated Glass Capsule */}
                    {isActive && (
                      <motion.div
                        layoutId="activeNavRailCapsule"
                        transition={{ type: 'spring', stiffness: 450, damping: 30 }}
                        className="absolute inset-0 rounded-2xl bg-white/15 border border-white/28 shadow-[0_0_20px_rgba(255,255,255,0.18)]"
                      />
                    )}

                    <Icon
                      className={`w-5 h-5 z-10 transition-transform duration-200 group-hover:scale-110 ${
                        isActive ? 'text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]' : ''
                      }`}
                    />

                    {/* Small Badge Dot if Available */}
                    {item.badge && !isActive && (
                      <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-cyan-400 opacity-80" />
                    )}
                  </button>
                </GlassTooltip>
              );
            })}
          </nav>

          {/* Divider */}
          <div className="w-6 h-[1px] bg-white/10" />

          {/* Bottom Settings & Profile Actions */}
          <div className="flex flex-col items-center gap-1.5">
            {/* Settings */}
            <GlassTooltip content="Settings & Accessibility" position="right">
              <button
                onClick={() => onSelectTab('settings')}
                className={`relative w-11 h-11 rounded-2xl flex items-center justify-center transition-all duration-200 group outline-none ${
                  activeTab === 'settings'
                    ? 'text-white'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-white/6'
                }`}
                aria-label="Settings"
              >
                {activeTab === 'settings' && (
                  <motion.div
                    layoutId="activeNavRailCapsule"
                    transition={{ type: 'spring', stiffness: 450, damping: 30 }}
                    className="absolute inset-0 rounded-2xl bg-white/15 border border-white/28 shadow-[0_0_20px_rgba(255,255,255,0.18)]"
                  />
                )}
                <Settings className="w-5 h-5 z-10 transition-transform group-hover:rotate-45" />
              </button>
            </GlassTooltip>

            {/* User Avatar Mini Pill */}
            <GlassTooltip content="Dr. Sanju • ISL Pro" position="right">
              <button
                onClick={() => onSelectTab('settings')}
                className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-500 border border-white/20 flex items-center justify-center text-xs font-bold text-white shadow-sm hover:scale-105 transition-transform"
                aria-label="User Profile"
              >
                SA
              </button>
            </GlassTooltip>
          </div>

        </div>
      </aside>

      {/* MOBILE: COMPACT FLOATING BOTTOM GLASS CAPSULE */}
      <nav
        className="fixed bottom-4 left-4 right-4 z-40 md:hidden glass-prominent rounded-full py-2 px-3 flex items-center justify-around border border-white/18 shadow-2xl backdrop-blur-3xl"
        aria-label="Mobile Bottom Navigation"
      >
        {mainNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`p-2.5 rounded-full relative transition-all ${
                isActive ? 'text-white' : 'text-slate-400 hover:text-white'
              }`}
              aria-label={item.label}
            >
              {isActive && (
                <motion.div
                  layoutId="activeMobileNavCapsule"
                  transition={{ type: 'spring', stiffness: 450, damping: 30 }}
                  className="absolute inset-0 rounded-full bg-white/15 border border-white/30 shadow-[0_0_15px_rgba(255,255,255,0.2)]"
                />
              )}
              <Icon className="w-5 h-5 relative z-10" />
            </button>
          );
        })}

        <button
          onClick={() => onSelectTab('settings')}
          className={`p-2.5 rounded-full relative transition-all ${
            activeTab === 'settings' ? 'text-white' : 'text-slate-400 hover:text-white'
          }`}
          aria-label="Settings"
        >
          {activeTab === 'settings' && (
            <motion.div
              layoutId="activeMobileNavCapsule"
              transition={{ type: 'spring', stiffness: 450, damping: 30 }}
              className="absolute inset-0 rounded-full bg-white/15 border border-white/30 shadow-[0_0_15px_rgba(255,255,255,0.2)]"
            />
          )}
          <Settings className="w-5 h-5 relative z-10" />
        </button>
      </nav>
    </>
  );
};
