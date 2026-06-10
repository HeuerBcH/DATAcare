/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        ink: { DEFAULT: '#14292b', soft: '#3f5b5e', faint: '#7a9092' },
        surface: { DEFAULT: '#f3f6f2', raised: '#ffffff', sunken: '#e9ede6' },
        line: '#dde3db',
        brand: {
          50: '#ecfdf6',
          100: '#d2f7e7',
          200: '#a8edd2',
          300: '#6fdcb7',
          400: '#38c39a',
          500: '#14a682',
          600: '#0c8a6e',
          700: '#0f766e',
          800: '#115e57',
          900: '#134e49',
        },
        risk: { baixo: '#15803d', medio: '#b45309', alto: '#b91c1c' },
      },
      boxShadow: {
        card: '0 1px 2px rgba(20,41,43,0.04), 0 10px 30px -16px rgba(20,41,43,0.18)',
        float: '0 18px 50px -18px rgba(20,41,43,0.30)',
      },
      borderRadius: { '2xl': '1.1rem', '3xl': '1.5rem' },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.55s cubic-bezier(0.22,0.8,0.26,1) both',
        'scale-in': 'scale-in 0.4s cubic-bezier(0.22,0.8,0.26,1) both',
      },
    },
  },
  plugins: [],
};
