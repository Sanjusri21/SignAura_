import React from 'react';

export interface GlassBadgeProps {
  variant?: 'neutral' | 'cyan' | 'purple' | 'green';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const GlassBadge: React.FC<GlassBadgeProps> = ({
  variant = 'neutral',
  size = 'md',
  icon,
  children,
  className = ''
}) => {
  const variantClass = {
    neutral: 'glass-badge',
    cyan: 'glass-badge glass-badge-cyan',
    purple: 'glass-badge glass-badge-purple',
    green: 'glass-badge glass-badge-green'
  }[variant];

  const sizeClass = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1'
  }[size];

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium ${variantClass} ${sizeClass} ${className}`}>
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
