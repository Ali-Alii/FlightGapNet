/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Syne'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        body: ["'DM Sans'", "sans-serif"],
      },
      colors: {
        radar: {
          bg: "#050c14",
          panel: "#0a1628",
          border: "#0f2847",
          accent: "#00d4ff",
          green: "#00ff88",
          amber: "#ffaa00",
          red: "#ff4466",
          muted: "#4a6b8a",
          text: "#c8dff0",
        },
      },
    },
  },
  plugins: [],
};