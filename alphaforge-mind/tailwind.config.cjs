/**** Tailwind config for AlphaForge Mind ****/
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        equity: 'var(--color-equity)',
        drawdown: 'var(--color-drawdown)',
        mcpath: 'var(--color-mc-path)',
        mcbg: 'var(--color-mc-band)'
      }
    }
  },
  plugins: []
};
