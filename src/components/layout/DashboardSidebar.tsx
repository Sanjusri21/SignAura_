import React, { useState } from 'react';
import { SignAuraLogo } from '../brand/SignAuraLogo';
import { NavigationTab } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { 
  LayoutDashboard, 
  Video, 
  Languages, 
  UserSquare2, 
  BotMessageSquare, 
  History, 
  Settings, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  X
} from 'lucide-react';

interface DashboardSidebarProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
}

export const DashboardSidebar: React.FC<DashboardSidebarProps> = ({
  activeTab,
  onSelectTab,
}) => {
  const { user, logout } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  const navItems = [
    { id: 'dashboard' as NavigationTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'convert' as NavigationTab, label: 'Video to ISL', icon: Video },
    { id: 'translator' as NavigationTab, label: 'Translator', icon: Languages },
    { id: 'avatar' as NavigationTab, label: '3D Avatar', icon: UserSquare2 },
    { id: 'assistant' as NavigationTab, label: 'AI Assistant', icon: BotMessageSquare },
    { id: 'library' as NavigationTab, label: 'History', icon: History },
    { id: 'settings' as NavigationTab, label: 'Settings', icon: Settings },
  ];

  const handleNav = (tab: NavigationTab) => {
    onSelectTab(tab);
    setMobileDrawerOpen(false);
  };

  return (
    <>
      {/* DESKTOP SOLID SIDEBAR */}
      <aside
        className={`hidden md:flex flex-col justify-between fixed top-0 left-0 bottom-0 z-40 bg-[#101735] border-r border-[#273154] transition-all duration-200 select-none ${
          isCollapsed ? 'w-20 p-3' : 'w-64 p-5'
        }`}
        aria-label="Dashboard Sidebar"
      >
        {/* Top: Logo & Collapse Toggle */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            {isCollapsed ? (
              <div className="w-full flex justify-center">
                <SignAuraLogo
                  size="sm"
                  showText={false}
                  onClick={() => handleNav('dashboard')}
                />
              </div>
            ) : (
              <SignAuraLogo
                size="sm"
                showText={true}
                onClick={() => handleNav('dashboard')}
              />
            )}

            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1.5 rounded-lg bg-[#151D40] text-[#A8B2D1] hover:text-white border border-[#273154] transition-colors hidden lg:flex"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Nav List */}
          <nav className="space-y-1" aria-label="Main Navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNav(item.id)}
                  title={isCollapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors ${
                    isActive
                      ? 'bg-[#151D40] text-[#22D3EE] border border-[#22D3EE]/40 font-bold'
                      : 'text-[#A8B2D1] hover:text-white hover:bg-[#151D40] border border-transparent'
                  } ${isCollapsed ? 'justify-center px-0' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon
                    className={`w-4 h-4 flex-shrink-0 ${
                      isActive ? 'text-[#22D3EE]' : 'text-[#A8B2D1]'
                    }`}
                  />

                  {!isCollapsed && (
                    <span className="truncate">{item.label}</span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom: User Profile & Logout */}
        <div className="pt-4 border-t border-[#273154] space-y-3">
          {/* User Capsule */}
          <div
            onClick={() => handleNav('settings')}
            className={`rounded-xl bg-[#151D40] p-2.5 flex items-center gap-3 border border-[#273154] hover:border-[#3B4975] transition-colors cursor-pointer ${
              isCollapsed ? 'justify-center p-2' : ''
            }`}
            title={isCollapsed ? (user?.full_name || 'Profile') : undefined}
          >
            <div className="w-8 h-8 rounded-lg bg-[#6366F1]/20 text-[#22D3EE] border border-[#273154] flex items-center justify-center text-xs font-bold flex-shrink-0">
              {user?.full_name?.charAt(0) || 'U'}
            </div>

            {!isCollapsed && (
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-bold text-white truncate">
                  {user?.full_name || 'SignAura User'}
                </p>
                <p className="text-[10px] text-[#A8B2D1] truncate">
                  {user?.role || 'Educator'}
                </p>
              </div>
            )}
          </div>

          {/* Logout Trigger */}
          <button
            onClick={() => {
              logout();
              onSelectTab('landing');
            }}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors ${
              isCollapsed ? 'justify-center px-0' : ''
            }`}
            title="Log out"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {!isCollapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* MOBILE TOP BAR */}
      <div className="md:hidden sticky top-0 z-30 bg-[#101735] border-b border-[#273154] px-4 py-3 flex items-center justify-between">
        <SignAuraLogo size="sm" showText={true} onClick={() => handleNav('dashboard')} />

        <button
          onClick={() => setMobileDrawerOpen(true)}
          className="p-2 rounded-xl bg-[#151D40] text-[#A8B2D1] hover:text-white border border-[#273154]"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* MOBILE DRAWER */}
      {mobileDrawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            onClick={() => setMobileDrawerOpen(false)}
            className="fixed inset-0 bg-black/70"
          />

          <div className="relative w-72 max-w-[80vw] bg-[#101735] border-r border-[#273154] p-5 flex flex-col justify-between z-10 shadow-2xl">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-2 border-b border-[#273154]">
                <SignAuraLogo size="sm" showText={true} />
                <button
                  onClick={() => setMobileDrawerOpen(false)}
                  className="p-1.5 rounded-lg text-[#A8B2D1] hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <nav className="space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id;

                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNav(item.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors ${
                        isActive
                          ? 'bg-[#151D40] text-[#22D3EE] border border-[#22D3EE]/40'
                          : 'text-[#A8B2D1] hover:bg-[#151D40] hover:text-white'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-[#22D3EE]' : 'text-[#A8B2D1]'}`} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </nav>
            </div>

            <div className="pt-4 border-t border-[#273154] space-y-3">
              <div className="flex items-center gap-3 p-2 rounded-xl bg-[#151D40] border border-[#273154]">
                <div className="w-8 h-8 rounded-lg bg-[#6366F1]/20 text-[#22D3EE] flex items-center justify-center text-xs font-bold">
                  {user?.full_name?.charAt(0) || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-white truncate">{user?.full_name || 'User'}</p>
                  <p className="text-[10px] text-[#A8B2D1] truncate">{user?.email || 'user@signaura.ai'}</p>
                </div>
              </div>

              <button
                onClick={() => {
                  logout();
                  handleNav('landing');
                }}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span>Log out</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
