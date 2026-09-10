import React from 'react';
import { CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';

interface StatusBadgeProps {
  status: 'completed' | 'processing' | 'queued' | 'failed';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const configs = {
    completed: {
      label: 'Completed',
      icon: CheckCircle2,
      style: 'bg-emerald-500/15 border-emerald-400/30 text-emerald-300'
    },
    processing: {
      label: 'Processing',
      icon: Loader2,
      style: 'bg-cyan-500/15 border-cyan-400/30 text-cyan-300 animate-pulse'
    },
    queued: {
      label: 'Queued',
      icon: Clock,
      style: 'bg-amber-500/15 border-amber-400/30 text-amber-300'
    },
    failed: {
      label: 'Failed',
      icon: AlertCircle,
      style: 'bg-rose-500/15 border-rose-400/30 text-rose-300'
    }
  };

  const config = configs[status] || configs.completed;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide border ${config.style} ${className}`}
      role="status"
    >
      <Icon className={`w-3.5 h-3.5 ${status === 'processing' ? 'animate-spin' : ''}`} />
      <span>{config.label}</span>
    </span>
  );
};
