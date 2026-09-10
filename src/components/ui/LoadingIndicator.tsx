import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingIndicatorProps {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  label = 'Loading...',
  size = 'md',
  className = ''
}) => {
  const sizeMap = {
    sm: { icon: 'w-4 h-4', text: 'text-xs' },
    md: { icon: 'w-6 h-6', text: 'text-sm' },
    lg: { icon: 'w-8 h-8', text: 'text-base' }
  }[size];

  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-6 select-none ${className}`} role="status">
      <div className="relative flex items-center justify-center">
        <div className="absolute inset-0 rounded-full blur-md bg-cyan-400/30 animate-pulse" />
        <Loader2 className={`${sizeMap.icon} text-cyan-400 animate-spin relative z-10`} />
      </div>
      {label && <p className={`${sizeMap.text} font-medium text-slate-300 tracking-wide`}>{label}</p>}
    </div>
  );
};
