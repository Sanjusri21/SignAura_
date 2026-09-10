import React from 'react';
import { SignAuraLogo } from '../brand/SignAuraLogo';
import { SignGestureVisual } from '../brand/SignGestureVisual';
import { ShieldCheck, Sparkles } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
  onNavigateHome?: () => void;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title,
  subtitle,
  onNavigateHome
}) => {
  return (
    <div className="min-h-[85vh] flex items-center justify-center py-8 px-4 sm:px-6 lg:px-8 relative z-10">
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        
        {/* LEFT BRANDING COLUMN */}
        <div className="lg:col-span-5 flex flex-col items-center lg:items-start text-center lg:text-left space-y-6">
          <SignAuraLogo
            size="lg"
            showText={true}
            showTagline={false}
            onClick={onNavigateHome}
          />

          <div className="space-y-3 max-w-md">
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
              Communication without barriers.
            </h1>
            <p className="text-sm text-[#A8B2D1] leading-relaxed font-normal">
              SignAura uses AI to make digital communication more accessible through Indian Sign Language.
            </p>
          </div>

          {/* Animated Abstract Signing Visual */}
          <div className="relative py-2 flex items-center justify-center">
            <SignGestureVisual size="md" className="scale-95 sm:scale-100" />
          </div>

          {/* Accessibility Badges */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-1">
            <div className="bg-[#101735] px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs text-[#A8B2D1] border border-[#273154]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#22D3EE]" />
              <span>WCAG 2.1 AA Compliant</span>
            </div>
            <div className="bg-[#101735] px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs text-[#A8B2D1] border border-[#273154]">
              <Sparkles className="w-3.5 h-3.5 text-[#8B5CF6]" />
              <span>Pan-Indian ISL Lexicon</span>
            </div>
          </div>
        </div>

        {/* RIGHT AUTHENTICATION PANEL (Clean Solid Surface, NOT Glass) */}
        <div className="lg:col-span-7 flex justify-center w-full">
          <div className="w-full max-w-md bg-[#151D40] rounded-2xl p-6 sm:p-8 border border-[#273154] shadow-xl relative">
            {/* Header */}
            <div className="space-y-1 mb-6 text-left">
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                {title}
              </h2>
              <p className="text-xs sm:text-sm text-[#A8B2D1]">
                {subtitle}
              </p>
            </div>

            {/* Form Content */}
            {children}
          </div>
        </div>

      </div>
    </div>
  );
};
