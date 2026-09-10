import React from 'react';

export interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'cyan' | 'ghost' | 'indigo';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  children?: React.ReactNode;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  className?: string;
}

export const GlassButton: React.FC<GlassButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  children,
  icon,
  iconPosition = 'left',
  className = '',
  disabled,
  ...props
}) => {
  const variantClass = {
    primary: 'bg-[#22D3EE] text-[#080D24] hover:bg-[#38BDF8] border border-[#22D3EE] shadow-sm font-semibold hover:-translate-y-0.5',
    cyan: 'bg-[#22D3EE] text-[#080D24] hover:bg-[#38BDF8] border border-[#22D3EE] shadow-sm font-semibold hover:-translate-y-0.5',
    secondary: 'bg-[#151D40] text-white hover:bg-[#1A244D] border border-[#273154] hover:border-[#3B4975] hover:-translate-y-0.5',
    indigo: 'bg-gradient-to-r from-[#6366F1] to-[#8B5CF6] text-white hover:opacity-95 border border-[#6366F1] font-semibold hover:-translate-y-0.5 shadow-sm',
    ghost: 'bg-transparent hover:bg-[#151D40] text-[#A8B2D1] hover:text-white border border-transparent hover:border-[#273154]'
  }[variant];

  const sizeClass = {
    sm: 'text-xs py-1.5 px-3 rounded-lg gap-1.5',
    md: 'text-xs sm:text-sm py-2 px-4 rounded-xl gap-2 font-medium',
    lg: 'text-sm sm:text-base py-2.5 px-5 rounded-xl gap-2.5 font-medium',
    icon: 'p-2 rounded-xl justify-center'
  }[size];

  return (
    <button
      disabled={disabled}
      className={`inline-flex items-center justify-center transition-all duration-150 outline-none select-none disabled:opacity-40 disabled:pointer-events-none ${variantClass} ${sizeClass} ${className}`}
      {...props}
    >
      {icon && iconPosition === 'left' && <span className="flex-shrink-0">{icon}</span>}
      {children && <span>{children}</span>}
      {icon && iconPosition === 'right' && <span className="flex-shrink-0">{icon}</span>}
    </button>
  );
};

export const SolidButton = GlassButton;
