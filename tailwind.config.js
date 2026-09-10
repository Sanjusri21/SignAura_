/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'navy-base': '#080D24',
        'navy-secondary': '#101735',
        'surface': '#151D40',
        'surface-hover': '#1A244D',
        'surface-light': '#1E2952',
        'accent-cyan': '#22D3EE',
        'accent-indigo': '#6366F1',
        'accent-purple': '#8B5CF6',
        'border-subtle': '#273154',
        'border-accent': '#3B4975',
        'text-primary': '#FFFFFF',
        'text-secondary': '#A8B2D1',
        'text-muted': '#6B7A99',
        // Retain legacy aliases for backward compatibility
        deep: '#080D24',
        'deep-secondary': '#101735',
        'primary-blue': '#6366F1',
        'electric-blue': '#22D3EE',
        'purple-accent': '#8B5CF6',
        'cyan-accent': '#22D3EE',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', '"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'solid-sm': '0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)',
        'solid-md': '0 4px 12px 0 rgba(0, 0, 0, 0.45)',
        'solid-lg': '0 10px 24px -3px rgba(0, 0, 0, 0.55)',
        'solid-xl': '0 20px 32px -4px rgba(0, 0, 0, 0.65)',
        'glow-cyan': '0 0 20px rgba(34, 211, 238, 0.25)',
        'glow-indigo': '0 0 20px rgba(99, 102, 241, 0.25)',
      },
      borderRadius: {
        'card': '16px',
        'panel': '20px',
        'modal': '24px',
      }
    },
  },
  plugins: [],
}
