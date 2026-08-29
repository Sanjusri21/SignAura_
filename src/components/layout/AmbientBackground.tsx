import React, { useEffect, useState } from 'react';

export const AmbientBackground: React.FC = () => {
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 100;
      const y = (e.clientY / window.innerHeight) * 100;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0 select-none" aria-hidden="true">
      {/* Deep Obsidian Spatial Base */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 0%, #080c1a 0%, #04060a 65%, #020306 100%)'
        }}
      />

      {/* Dynamic Cursor Reactive Ambient Glow */}
      <div 
        className="absolute w-[500px] h-[500px] rounded-full blur-[140px] opacity-15 transition-all duration-1000 ease-out"
        style={{
          left: `${mousePos.x}%`,
          top: `${mousePos.y}%`,
          transform: 'translate(-50%, -50%)',
          background: 'radial-gradient(circle, #38bdf8 0%, #7c3aed 45%, transparent 70%)'
        }}
      />

      {/* Soft Blue Ambient Emitter (Top Left) */}
      <div 
        className="absolute -top-36 -left-36 w-[650px] h-[650px] rounded-full blur-[160px] opacity-25 animate-spatial-orb-1"
        style={{
          background: 'radial-gradient(circle, #1d4ed8 0%, #2563eb 40%, transparent 75%)'
        }}
      />

      {/* Soft Violet Ambient Emitter (Right Center) */}
      <div 
        className="absolute top-1/4 -right-36 w-[700px] h-[700px] rounded-full blur-[180px] opacity-20 animate-spatial-orb-2"
        style={{
          background: 'radial-gradient(circle, #6d28d9 0%, #7c3aed 35%, transparent 75%)'
        }}
      />

      {/* Cyan Floor Ambient Glow */}
      <div 
        className="absolute -bottom-48 left-1/3 w-[800px] h-[600px] rounded-full blur-[180px] opacity-18 animate-soft-pulse"
        style={{
          background: 'radial-gradient(circle, #0891b2 0%, #2563eb 40%, transparent 70%)'
        }}
      />

      {/* Delicate Spatial Dot Matrix Texture */}
      <div 
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `radial-gradient(rgba(255, 255, 255, 0.4) 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }}
      />
    </div>
  );
};
