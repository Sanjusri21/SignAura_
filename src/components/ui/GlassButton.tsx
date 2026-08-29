import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface GlassButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'primary' | 'secondary' | 'cyan' | 'ghost';
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
    primary: 'glass-btn-primary',
    secondary: 'glass-btn-secondary',
    cyan: 'glass-btn-cyan',
    ghost: 'bg-transparent hover:bg-white/10 text-slate-300 hover:text-white border border-transparent hover:border-white/15'
  }[variant];

  const sizeClass = {
    sm: 'text-xs py-1.5 px-3 rounded-xl gap-1.5',
    md: 'text-sm py-2.5 px-4 rounded-2xl gap-2',
    lg: 'text-base py-3 px-6 rounded-2xl gap-2.5',
    icon: 'p-2.5 rounded-2xl justify-center'
  }[size];

  return (
    <motion.button
      whileHover={disabled ? undefined : { scale: 1.02, y: -1 }}
      whileTap={disabled ? undefined : { scale: 0.97, y: 1 }}
      transition={{ type: 'spring', stiffness: 450, damping: 25 }}
      disabled={disabled}
      className={`inline-flex items-center justify-center font-medium transition-colors outline-none select-none disabled:opacity-40 disabled:pointer-events-none ${variantClass} ${sizeClass} ${className}`}
      {...props}
    >
      {icon && iconPosition === 'left' && <span className="flex-shrink-0">{icon}</span>}
      {children && <span>{children}</span>}
      {icon && iconPosition === 'right' && <span className="flex-shrink-0">{icon}</span>}
    </motion.button>
  );
};
