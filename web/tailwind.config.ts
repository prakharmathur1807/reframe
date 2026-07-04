import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * Reframe design tokens — an editing-suite palette:
 * graphite panels, chalk text, a REC-red accent, and an amber guide color
 * borrowed from safe-area overlays.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "hsl(var(--ink))",
        panel: "hsl(var(--panel))",
        raised: "hsl(var(--raised))",
        line: "hsl(var(--line))",
        chalk: "hsl(var(--chalk))",
        dim: "hsl(var(--dim))",
        rec: "hsl(var(--rec))",
        guide: "hsl(var(--guide))",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
        lg: "10px",
      },
      keyframes: {
        "crop-track": {
          "0%, 12%": { transform: "translateX(0%)" },
          "42%, 62%": { transform: "translateX(118%)" },
          "88%, 100%": { transform: "translateX(0%)" },
        },
        "rec-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "crop-track": "crop-track 9s cubic-bezier(0.45, 0, 0.25, 1) infinite",
        "rec-blink": "rec-blink 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
