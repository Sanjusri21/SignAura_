import React from 'react';

interface SignAuraLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  showTagline?: boolean;
  className?: string;
  onClick?: () => void;
}

export const SignAuraLogo: React.FC<SignAuraLogoProps> = ({
  size = 'md',
  showText = true,
  showTagline = false,
  className = '',
  onClick
}) => {
  const sizeMap = {
    sm: { icon: 28, text: 'text-base', tagline: 'text-[9px]' },
    md: { icon: 34, text: 'text-lg', tagline: 'text-[10px]' },
    lg: { icon: 44, text: 'text-2xl', tagline: 'text-xs' },
    xl: { icon: 56, text: 'text-3xl', tagline: 'text-sm' },
  };

  const current = sizeMap[size];

  return (
    <div
      onClick={onClick}
      className={`inline-flex items-center gap-2.5 select-none ${onClick ? 'cursor-pointer group' : ''} ${className}`}
      role={onClick ? 'button' : 'img'}
      aria-label="SignAura Logo - AI-Powered Indian Sign Language Accessibility"
    >
      {/* Crisp Emblem: Stylized Signing Hand + Circular Aura Ring */}
      <div className="relative flex items-center justify-center flex-shrink-0">
        <svg
          width={current.icon}
          height={current.icon}
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="transition-transform duration-200 group-hover:scale-105"
        >
          <defs>
            <linearGradient id="auraGradient" x1="2" y1="2" x2="38" y2="38" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#22D3EE" />
              <stop offset="50%" stopColor="#6366F1" />
              <stop offset="100%" stopColor="#8B5CF6" />
            </linearGradient>

            <linearGradient id="handGradient" x1="12" y1="10" x2="28" y2="32" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FFFFFF" />
              <stop offset="100%" stopColor="#22D3EE" />
            </linearGradient>
          </defs>

          {/* Solid Dark Surface Disc */}
          <circle cx="20" cy="20" r="18" fill="#151D40" stroke="#273154" strokeWidth="1.5" />

          {/* Circular Aura Ring (Communicates AI / Aura / Universal Inclusion) */}
          <circle
            cx="20"
            cy="20"
            r="15"
            stroke="url(#auraGradient)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray="72 24"
            className="animate-aura-spin origin-center"
          />

          {/* Stylized ISL Hand Gesture Silhouette (Palm & Expressive Signing Fingers) */}
          <path
            d="M17 28C15.3 28 14 26.7 14 25V20C14 19.5 14.4 19.1 14.9 19.1C15.4 19.1 15.8 19.5 15.8 20V24H16.6V15.5C16.6 15 17 14.6 17.5 14.6C18 14.6 18.4 15 18.4 15.5V23H19.2V13C19.2 12.4 19.6 12 20.1 12C20.6 12 21 12.4 21 13V23H21.8V14.8C21.8 14.3 22.2 13.9 22.7 13.9C23.2 13.9 23.6 14.3 23.6 14.8V24H24.4V18C24.4 17.5 24.8 17.1 25.3 17.1C25.8 17.1 26.2 17.5 26.2 18V23.5C26.2 26 24.2 28 21.7 28H17Z"
            fill="url(#handGradient)"
          />

          {/* Accessibility Wave Arc */}
          <path
            d="M10 24C11.5 27 14.5 29.5 18.5 30C22.5 30.5 26.5 28.5 29 25"
            stroke="#22D3EE"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.85"
          />

          {/* AI Sparkle Point (Top Right) */}
          <circle cx="29" cy="11" r="1.5" fill="#FFFFFF" />
          <circle cx="29" cy="11" r="3" stroke="#22D3EE" strokeWidth="0.8" opacity="0.6" />
        </svg>
      </div>

      {/* Brand Text */}
      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1">
            <span className={`font-bold tracking-tight text-white ${current.text}`}>
              Sign<span className="text-[#22D3EE]">Aura</span>
            </span>
          </div>

          {showTagline && (
            <span className={`text-[#A8B2D1] font-medium tracking-wide ${current.tagline}`}>
              AI-Powered Indian Sign Language
            </span>
          )}
        </div>
      )}
    </div>
  );
};
