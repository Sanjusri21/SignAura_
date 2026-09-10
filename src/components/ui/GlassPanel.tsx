import React from 'react';

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  level?: 'subtle' | 'medium' | 'prominent';
  glow?: 'none' | 'cyan' | 'purple' | 'blue';
  className?: string;
  children: React.ReactNode;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  level = 'medium',
  glow = 'none',
  className = '',
  children,
  ...props
}) => {
  const levelClass = {
    subtle: 'bg-[#101735] border border-[#273154]',
    medium: 'bg-[#151D40] border border-[#273154]',
    prominent: 'bg-[#151D40] border border-[#3B4975]'
  }[level];

  return (
    <div
      className={`rounded-2xl shadow-md transition-all duration-200 relative ${levelClass} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const SolidPanel = GlassPanel;
