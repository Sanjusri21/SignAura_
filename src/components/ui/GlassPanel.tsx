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
    subtle: 'glass-subtle',
    medium: 'glass-medium',
    prominent: 'glass-prominent'
  }[level];

  const glowClass = {
    none: '',
    cyan: 'shadow-[0_0_30px_rgba(56,189,248,0.15)]',
    purple: 'shadow-[0_0_30px_rgba(168,85,247,0.15)]',
    blue: 'shadow-[0_0_30px_rgba(37,99,235,0.15)]'
  }[glow];

  return (
    <div
      className={`rounded-3xl transition-all duration-300 relative ${levelClass} ${glowClass} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
