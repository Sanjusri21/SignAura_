import React, { useState } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';

interface PasswordFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  showStrength?: boolean;
}

export const PasswordField: React.FC<PasswordFieldProps> = ({
  label,
  error,
  showStrength = false,
  value,
  id,
  className = '',
  ...props
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const inputId = id || `input-${label.toLowerCase().replace(/\s+/g, '-')}`;

  const calculateStrength = (pwd: string) => {
    if (!pwd) return { score: 0, label: '', color: 'bg-transparent' };
    let score = 0;
    if (pwd.length >= 8) score += 1;
    if (/[A-Z]/.test(pwd)) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

    if (score <= 1) return { score: 1, label: 'Weak', color: 'bg-rose-500' };
    if (score === 2 || score === 3) return { score: 2, label: 'Medium', color: 'bg-amber-400' };
    return { score: 3, label: 'Strong', color: 'bg-emerald-400' };
  };

  const strength = calculateStrength(String(value || ''));

  return (
    <div className="space-y-1.5 w-full">
      <div className="flex items-center justify-between">
        <label
          htmlFor={inputId}
          className="block text-xs font-semibold text-[#A8B2D1] select-none tracking-wide"
        >
          {label}
          {props.required && <span className="text-[#22D3EE] ml-1" aria-hidden="true">*</span>}
        </label>

        {showStrength && value && (
          <span className="text-[11px] font-semibold text-[#A8B2D1]">
            Strength: <span className={strength.score === 3 ? 'text-emerald-400' : strength.score === 2 ? 'text-amber-400' : 'text-rose-400'}>{strength.label}</span>
          </span>
        )}
      </div>

      <div className="relative flex items-center">
        <div className="absolute left-3.5 text-[#6B7A99] pointer-events-none flex items-center justify-center">
          <Lock className="w-4 h-4" />
        </div>

        <input
          id={inputId}
          type={showPassword ? 'text' : 'password'}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          value={value}
          className={`w-full bg-[#101735] text-sm py-2.5 pl-10 pr-11 rounded-xl border border-[#273154] focus:border-[#22D3EE] focus:ring-1 focus:ring-[#22D3EE]/30 text-white placeholder-[#6B7A99] transition-colors outline-none ${
            error ? 'border-red-500/80 focus:border-red-500' : ''
          } ${className}`}
          {...props}
        />

        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 text-[#6B7A99] hover:text-white transition-colors p-1 rounded-lg focus:outline-none"
          title={showPassword ? 'Hide password' : 'Show password'}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>

      {showStrength && value && (
        <div className="flex items-center gap-1.5 mt-1.5" aria-hidden="true">
          <div className={`h-1 flex-1 rounded-full transition-all ${strength.score >= 1 ? strength.color : 'bg-[#273154]'}`} />
          <div className={`h-1 flex-1 rounded-full transition-all ${strength.score >= 2 ? strength.color : 'bg-[#273154]'}`} />
          <div className={`h-1 flex-1 rounded-full transition-all ${strength.score >= 3 ? strength.color : 'bg-[#273154]'}`} />
        </div>
      )}

      {error && (
        <p id={`${inputId}-error`} className="text-xs text-rose-400 font-medium flex items-center gap-1 mt-1">
          <span>•</span> {error}
        </p>
      )}
    </div>
  );
};
