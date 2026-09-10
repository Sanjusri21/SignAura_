import React from 'react';

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
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
  return (
    <div
      className={`bg-[#151D40] border border-[#273154] rounded-2xl shadow-md transition-all duration-200 ${
        interactive ? 'hover:-translate-y-0.5 hover:border-[#3B4975] hover:shadow-lg cursor-pointer' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const SolidCard = GlassCard;
