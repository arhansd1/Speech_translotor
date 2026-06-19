/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      },
      colors: {
        terminal: {
          bg: "#070A0E",
          panel: "#0D1117",
          panelLight: "#131920",
          border: "#1C2730",
          borderLight: "#243040",
          muted: "#3D5066",
          secondary: "#607D93",
          body: "#C8D8E8",
          bright: "#E8F1F8",
          orange: "#FF4F1F",
          mint: "#2DFF9A",
        },
      },
      animation: {
        "pulse-ring": "pulse-ring 1.5s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-in":    "fade-in 0.3s ease-in",
        "glow-ring":  "glow-ring 2s cubic-bezier(0.4,0,0.6,1) infinite",
      },
      keyframes: {
        "pulse-ring": {
          "0%, 100%": { opacity: "1" },
          "50%":       { opacity: "0.4" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "glow-ring": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.3" },
          "50%":       { transform: "scale(1.15)", opacity: "0.1" },
        },
      },
    },
  },
  plugins: [],
}
