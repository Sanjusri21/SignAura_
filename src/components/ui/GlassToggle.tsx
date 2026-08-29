import React from 'react';
import { motion } from 'framer-motion';

export interface GlassToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export const GlassToggle: React.FC<GlassToggleProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className = ''
}) => {
  return (
    <div className={`flex items-center justify-between gap-4 select-none ${className}`}>
      {(label || description) && (
        <div className="flex-1 min-w-0">
          {label && <p className="text-sm font-semibold text-white tracking-tight">{label}</p>}
          {description && <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{description}</p>}
        </div>
      )}

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`w-12 h-7 rounded-full p-1 transition-all relative border flex items-center ${
          checked
            ? 'bg-white/25 border-white/40 shadow-[0_0_16px_rgba(255,255,255,0.25)]'
            : 'bg-white/6 border-white/10'
        } ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <motion.div
          animate={{ x: checked ? 20 : 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          className={`w-5 h-5 rounded-full shadow-md ${
            checked
              ? 'bg-white shadow-[0_2px_8px_rgba(0,0,0,0.4)]'
              : 'bg-slate-300'
          }`}
        />
      </button>
    </div>
  );
};
