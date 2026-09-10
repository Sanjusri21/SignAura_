import React, { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  alpha: number;
  baseAlpha: number;
  pulseSpeed: number;
}

export const AmbientBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mouseRef = useRef({ x: -1000, y: -1000, targetX: -1000, targetY: -1000 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.targetX = e.clientX;
      mouseRef.current.targetY = e.clientY;
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Initialize Gesture Landmark Particles (representing 3D sign joint nodes)
    const particleCount = Math.min(Math.floor((width * height) / 22000), 55);
    const colors = ['#22D3EE', '#6366F1', '#8B5CF6', '#38BDF8'];
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        size: Math.random() * 2.2 + 1.2,
        color: colors[Math.floor(Math.random() * colors.length)],
        alpha: Math.random() * 0.6 + 0.2,
        baseAlpha: Math.random() * 0.4 + 0.2,
        pulseSpeed: Math.random() * 0.02 + 0.008
      });
    }

    let tick = 0;

    const render = () => {
      tick++;

      // Smooth mouse interpolation
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.08;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.08;

      ctx.clearRect(0, 0, width, height);

      // 1. Draw connecting neural gesture kinematic lines between close particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const maxDist = 140;

          if (dist < maxDist) {
            const opacity = (1 - dist / maxDist) * 0.22;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(99, 102, 241, ${opacity})`;
            ctx.lineWidth = 0.9;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // 2. Draw & update landmark particle nodes
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        // Bounce off canvas boundaries
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Subtle mouse interaction (interactive particle glow & slight repulsion)
        const dx = mouseRef.current.x - p.x;
        const dy = mouseRef.current.y - p.y;
        const mouseDist = Math.sqrt(dx * dx + dy * dy);
        let extraAlpha = 0;

        if (mouseDist < 160) {
          extraAlpha = (1 - mouseDist / 160) * 0.5;
          p.x -= (dx / mouseDist) * 0.5;
          p.y -= (dy / mouseDist) * 0.5;
        }

        const currentAlpha = Math.min(
          1,
          p.baseAlpha + Math.sin(tick * p.pulseSpeed) * 0.2 + extraAlpha
        );

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = currentAlpha;
        ctx.shadowBlur = 8;
        ctx.shadowColor = p.color;
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.globalAlpha = 1;
      });

      // 3. Draw subtle flowing gesture motion curves
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(34, 211, 238, 0.12)';
      ctx.lineWidth = 1.2;
      const waveOffset = tick * 0.008;
      ctx.moveTo(0, height * 0.35 + Math.sin(waveOffset) * 40);
      
      for (let x = 0; x < width; x += 40) {
        const y = height * 0.35 + Math.sin(x * 0.003 + waveOffset) * 50 + Math.cos(x * 0.002 + waveOffset * 0.7) * 30;
        ctx.lineTo(x, y);
      }
      ctx.stroke();

      ctx.beginPath();
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.1)';
      ctx.lineWidth = 1.0;
      ctx.moveTo(0, height * 0.65 + Math.cos(waveOffset * 0.8) * 40);
      
      for (let x = 0; x < width; x += 40) {
        const y = height * 0.65 + Math.cos(x * 0.0025 + waveOffset * 0.9) * 45 + Math.sin(x * 0.0018 + waveOffset) * 25;
        ctx.lineTo(x, y);
      }
      ctx.stroke();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden z-0 select-none bg-[#080D24]"
      aria-hidden="true"
    >
      {/* 1. Deep Navy Base Gradient Mesh */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 10%, #101735 0%, #080D24 75%)'
        }}
      />

      {/* 2. Slowly Drifting Ambient Light Blooms (Multi-Color Fluid Aurora) */}
      <div
        className="absolute -top-32 -left-32 w-[650px] h-[650px] rounded-full blur-[150px] opacity-30 animate-pulse-subtle"
        style={{
          background: 'radial-gradient(circle, #6366F1 0%, #8B5CF6 50%, transparent 75%)'
        }}
      />

      <div
        className="absolute top-1/3 -right-40 w-[700px] h-[700px] rounded-full blur-[170px] opacity-25 animate-pulse-subtle"
        style={{
          animationDelay: '3.5s',
          background: 'radial-gradient(circle, #22D3EE 0%, #6366F1 45%, transparent 75%)'
        }}
      />

      <div
        className="absolute -bottom-40 left-1/4 w-[750px] h-[550px] rounded-full blur-[160px] opacity-20 animate-pulse-subtle"
        style={{
          animationDelay: '2s',
          background: 'radial-gradient(circle, #8B5CF6 0%, #101735 55%, transparent 75%)'
        }}
      />

      {/* 3. Top Sheen Light Ray */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[250px] opacity-15 blur-3xl pointer-events-none"
        style={{
          background: 'linear-gradient(90deg, transparent 0%, #22D3EE 50%, transparent 100%)'
        }}
      />

      {/* 4. Interactive Neural Landmark Canvas (Connecting ISL Node Constellations) */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full block"
      />

      {/* 5. Clean Grid Overlay */}
      <div
        className="absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage: `
            linear-gradient(to right, #273154 1px, transparent 1px),
            linear-gradient(to bottom, #273154 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px'
        }}
      />
    </div>
  );
};
