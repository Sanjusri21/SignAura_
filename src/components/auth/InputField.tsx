import React from 'react';

interface InputFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  icon?: React.ReactNode;
}

export const InputField: React.FC<InputFieldProps> = ({
  label,
  error,
  icon,
  id,
  className = '',
  ...props
}) => {
  const inputId = id || `input-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="space-y-1.5 w-full">
      <label
        htmlFor={inputId}
        className="block text-xs font-semibold text-[#A8B2D1] select-none tracking-wide"
      >
        {label}
        {props.required && <span className="text-[#22D3EE] ml-1" aria-hidden="true">*</span>}
      </label>

      <div className="relative flex items-center">
        {icon && (
          <div className="absolute left-3.5 text-[#6B7A99] pointer-events-none flex items-center justify-center">
            {icon}
          </div>
        )}

        <input
          id={inputId}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className={`w-full bg-[#101735] text-sm py-2.5 rounded-xl border border-[#273154] focus:border-[#22D3EE] focus:ring-1 focus:ring-[#22D3EE]/30 text-white placeholder-[#6B7A99] transition-colors outline-none ${
            icon ? 'pl-10 pr-4' : 'px-4'
          } ${error ? 'border-red-500/80 focus:border-red-500' : ''} ${className}`}
          {...props}
        />
      </div>

      {error && (
        <p id={`${inputId}-error`} className="text-xs text-rose-400 font-medium flex items-center gap-1 mt-1">
          <span>•</span> {error}
        </p>
      )}
    </div>
  );
};
