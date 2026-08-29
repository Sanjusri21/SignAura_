/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        deep: '#050816',
        'deep-secondary': '#0a0e27',
        'primary-blue': '#2563EB',
        'electric-blue': '#38BDF8',
        'purple-accent': '#8B5CF6',
        'cyan-accent': '#22D3EE',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Outfit"', 'system-ui', 'sans-serif'],
        display: ['"Outfit"', '"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
        '2xl': '24px',
        '3xl': '32px',
      }
    },
  },
  plugins: [],
}
