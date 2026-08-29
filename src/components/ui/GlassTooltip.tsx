import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

export interface GlassTooltipProps {
  content: React.ReactNode;
  position?: 'right' | 'top' | 'bottom' | 'left';
  children: React.ReactNode;
  delay?: number;
}

export const GlassTooltip: React.FC<GlassTooltipProps> = ({
  content,
  position = 'right',
  children,
  delay = 0.1
}) => {
  const [isVisible, setIsVisible] = useState(false);

  const positionClasses = {
    right: 'left-full ml-3 top-1/2 -translate-y-1/2',
    left: 'right-full mr-3 top-1/2 -translate-y-1/2',
    top: 'bottom-full mb-3 left-1/2 -translate-x-1/2',
    bottom: 'top-full mt-3 left-1/2 -translate-x-1/2'
  }[position];

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}

      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: position === 'top' ? 4 : position === 'bottom' ? -4 : 0 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ duration: 0.15, delay, ease: [0.16, 1, 0.3, 1] }}
            className={`absolute z-50 pointer-events-none whitespace-nowrap px-3 py-1.5 rounded-xl bg-[#090d1c]/90 backdrop-blur-2xl border border-white/18 text-xs font-semibold text-white shadow-[0_8px_24px_rgba(0,0,0,0.5)] ${positionClasses}`}
            role="tooltip"
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
