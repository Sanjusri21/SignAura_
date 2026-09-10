import React, { useState } from 'react';
import { SignAuraLogo } from '../brand/SignAuraLogo';
import { GlassButton } from '../ui/GlassButton';
import { NavigationTab } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { Menu, X, ArrowRight, Sparkles } from 'lucide-react';

interface NavbarProps {
  onNavigate: (tab: NavigationTab) => void;
  activeSection?: string;
  onScrollToSection?: (sectionId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onNavigate,
  onScrollToSection
}) => {
  const { isAuthenticated, user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Home', target: 'hero', isTab: true, tab: 'landing' as NavigationTab },
    { label: 'Features', target: 'features', isTab: false },
    { label: 'How It Works', target: 'how-it-works', isTab: false },
    { label: 'About', target: 'about', isTab: false },
  ];

  const handleLinkClick = (link: typeof navLinks[0]) => {
    setMobileMenuOpen(false);
    if (link.isTab && link.tab) {
      onNavigate(link.tab);
    } else if (onScrollToSection) {
      onScrollToSection(link.target);
    } else {
      const el = document.getElementById(link.target);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-[#080D24] border-b border-[#273154] py-3.5 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        {/* Left: SignAura Brand Logo */}
        <SignAuraLogo
          size="md"
          showText={true}
          onClick={() => onNavigate('landing')}
        />

        {/* Center: Clean Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 bg-[#101735] px-3 py-1.5 rounded-xl border border-[#273154]">
          {navLinks.map((link) => (
            <button
              key={link.label}
              onClick={() => handleLinkClick(link)}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#A8B2D1] hover:text-white hover:bg-[#151D40] transition-colors"
            >
              {link.label}
            </button>
          ))}
        </nav>

        {/* Right: Authentication Actions */}
        <div className="hidden sm:flex items-center gap-3">
          {isAuthenticated ? (
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => onNavigate('dashboard')}
                className="bg-[#151D40] hover:bg-[#1A244D] px-3.5 py-2 rounded-xl text-xs font-semibold text-white flex items-center gap-2 border border-[#273154] transition-colors"
              >
                <div className="w-5 h-5 rounded-md bg-[#6366F1]/20 text-[#22D3EE] flex items-center justify-center text-[10px] font-bold">
                  {user?.full_name?.charAt(0) || 'U'}
                </div>
                <span>Dashboard</span>
              </button>

              <GlassButton
                variant="primary"
                size="sm"
                onClick={() => onNavigate('convert')}
                icon={<Sparkles className="w-3.5 h-3.5 text-[#080D24]" />}
              >
                Launch Studio
              </GlassButton>
            </div>
          ) : (
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => onNavigate('signin')}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-[#A8B2D1] hover:text-white transition-colors"
              >
                Sign In
              </button>

              <GlassButton
                variant="primary"
                size="sm"
                onClick={() => onNavigate('signup')}
                icon={<ArrowRight className="w-3.5 h-3.5 text-[#080D24]" />}
                iconPosition="right"
              >
                Get Started
              </GlassButton>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Toggle Button */}
        <div className="sm:hidden flex items-center">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl bg-[#151D40] text-[#A8B2D1] hover:text-white border border-[#273154] focus:outline-none"
            aria-label={mobileMenuOpen ? 'Close Menu' : 'Open Menu'}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden bg-[#101735] mt-2 mx-4 rounded-xl p-4 border border-[#273154] shadow-2xl">
          <nav className="flex flex-col space-y-1 pb-3 border-b border-[#273154]">
            {navLinks.map((link) => (
              <button
                key={link.label}
                onClick={() => handleLinkClick(link)}
                className="text-left px-3 py-2 rounded-lg text-sm font-medium text-[#A8B2D1] hover:text-white hover:bg-[#151D40] transition-colors"
              >
                {link.label}
              </button>
            ))}
          </nav>

          <div className="pt-3 space-y-2">
            {isAuthenticated ? (
              <>
                <GlassButton
                  variant="primary"
                  size="md"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onNavigate('dashboard');
                  }}
                  className="w-full justify-center"
                >
                  Go to Dashboard
                </GlassButton>
                <button
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full py-2 text-xs text-rose-400 hover:text-rose-300 text-center"
                >
                  Log out
                </button>
              </>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onNavigate('signin');
                  }}
                  className="py-2.5 rounded-xl bg-[#151D40] text-xs font-semibold text-white text-center border border-[#273154]"
                >
                  Sign In
                </button>
                <GlassButton
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onNavigate('signup');
                  }}
                  className="w-full justify-center"
                >
                  Get Started
                </GlassButton>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
