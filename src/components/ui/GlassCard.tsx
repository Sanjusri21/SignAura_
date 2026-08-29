import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface GlassCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  interactive?: boolean;
  className?: string;
  children: React.ReactNode;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  interactive = false,
  className = '',
  children,
  ...props
}) => {
  if (interactive) {
    return (
      <motion.div
        whileHover={{ y: -3, scale: 1.008 }}
        whileTap={{ scale: 0.995 }}
        transition={{ type: 'spring', stiffness: 400, damping: 28 }}
        className={`glass-card cursor-pointer ${className}`}
        {...props}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <div className={`glass-card ${className}`} {...props as React.HTMLAttributes<HTMLDivElement>}>
      {children}
    </div>
  );
};
