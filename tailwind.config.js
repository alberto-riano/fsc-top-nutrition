/**
 * Configuración de Tailwind para TopTrack.
 *
 * El tema (colores de marca, superficies, tipografía) está centralizado aquí.
 * Re-tematizar el producto para otro vertical es cambiar la paleta `brand`
 * y las superficies `surface`, y reconstruir el CSS.
 *
 * Marca FSC Top Nutrition: verde vibrante sobre fondo casi negro.
 */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // Verde de marca (escala green de Tailwind, acento ~#22c55e).
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        // Superficies oscuras (fondo casi negro y grises muy oscuros).
        surface: {
          DEFAULT: '#141414',
          secondary: '#1a1a1a',
          tertiary: '#0a0a0a',
          border: '#262626',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 2px 8px -2px rgba(0, 0, 0, 0.4), 0 4px 16px -4px rgba(0, 0, 0, 0.4)',
        card: '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.4)',
        glow: '0 0 24px -6px rgba(34, 197, 94, 0.35)',
      },
    },
  },
  plugins: [],
};
