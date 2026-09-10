import React from 'react';

interface SignGestureVisualProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const SignGestureVisual: React.FC<SignGestureVisualProps> = ({
  className = '',
  size = 'md'
}) => {
  const sizeStyles = {
    sm: 'w-44 h-44',
    md: 'w-64 h-64',
    lg: 'w-80 h-80'
  }[size];

  return (
    <div
      className={`relative flex items-center justify-center pointer-events-none select-none ${sizeStyles} ${className}`}
      aria-hidden="true"
    >
      {/* SVG Stylized Hand Kinetic Lines & Particle Nodes */}
      <svg
        viewBox="0 0 200 200"
        className="w-full h-full relative z-10"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="gestureGrad" x1="20" y1="20" x2="180" y2="180" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#22D3EE" />
            <stop offset="50%" stopColor="#6366F1" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>

          <radialGradient id="discGrad" cx="100" cy="100" r="90" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#151D40" />
            <stop offset="100%" stopColor="#101735" />
          </radialGradient>
        </defs>

        {/* Solid Container Disc */}
        <circle cx="100" cy="100" r="90" fill="url(#discGrad)" stroke="#273154" strokeWidth="1.5" />

        {/* Concentric Gesture Aura Rings */}
        <circle cx="100" cy="100" r="76" stroke="#273154" strokeWidth="1" strokeDasharray="4 6" />
        <circle cx="100" cy="100" r="62" stroke="#6366F1" strokeWidth="1.5" strokeDasharray="6 8" className="animate-aura-spin origin-center" opacity="0.6" />

        {/* Dynamic ISL Hand Silhouette & Kinematic Motion Arcs */}
        <path
          d="M75 145 C65 130 65 110 70 95 C75 80 85 70 100 68 C115 70 125 80 130 95 C135 110 135 130 125 145 Z"
          fill="#1A244D"
          stroke="url(#gestureGrad)"
          strokeWidth="1.5"
        />

        {/* Finger Gestural Flow Paths */}
        <path d="M72 110 Q55 105 48 90 Q46 80 54 75 Q62 72 74 88" stroke="url(#gestureGrad)" strokeWidth="2" strokeLinecap="round" />
        <path d="M82 80 Q80 50 82 32 Q86 24 92 25 Q96 28 94 48 L92 75" stroke="url(#gestureGrad)" strokeWidth="2" strokeLinecap="round" />
        <path d="M96 73 Q98 42 101 22 Q105 16 110 18 Q114 21 112 42 L108 73" stroke="url(#gestureGrad)" strokeWidth="2" strokeLinecap="round" />
        <path d="M112 76 Q118 50 122 36 Q126 30 130 32 Q133 36 128 54 L122 78" stroke="url(#gestureGrad)" strokeWidth="2" strokeLinecap="round" />
        <path d="M125 88 Q136 70 144 58 Q148 54 152 58 Q154 62 144 78 L132 98" stroke="url(#gestureGrad)" strokeWidth="2" strokeLinecap="round" />

        {/* Kinetic Nodes */}
        <circle cx="50" cy="78" r="3" fill="#22D3EE" />
        <circle cx="87" cy="27" r="3" fill="#FFFFFF" />
        <circle cx="106" cy="20" r="3" fill="#22D3EE" />
        <circle cx="127" cy="33" r="3" fill="#8B5CF6" />
        <circle cx="149" cy="58" r="2.5" fill="#22D3EE" />
        <circle cx="100" cy="110" r="3.5" fill="#FFFFFF" />
        <circle cx="100" cy="110" r="7" stroke="#22D3EE" strokeWidth="1" opacity="0.6" />
        <circle cx="85" cy="135" r="2" fill="#6366F1" />
        <circle cx="115" cy="135" r="2" fill="#6366F1" />
      </svg>
    </div>
  );
};
