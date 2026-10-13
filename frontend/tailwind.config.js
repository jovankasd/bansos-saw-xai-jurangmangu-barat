/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#003426",
          container: "#0f4c3a",
          fixed: "#b4efd6",
          "fixed-dim": "#99d3ba",
        },
        "on-primary": {
          DEFAULT: "#ffffff",
          container: "#82bba4",
          fixed: "#002117",
        },
        surface: {
          DEFAULT: "#ffffff",
          canvas: "#f8f9ff",
          subtle: "#F1F5F9",
          container: "#e6eeff",
          "container-low": "#eff4ff",
          "container-lowest": "#ffffff",
          "container-high": "#dce9ff",
        },
        "on-surface": {
          DEFAULT: "#0d1c2e",
          variant: "#404944",
        },
        border: {
          subtle: "#E2E8F0",
          strong: "#CBD5E1",
        },
        outline: {
          DEFAULT: "#707974",
          variant: "#bfc9c3",
        },
        status: {
          "approved-bg": "#ECFDF5",
          "approved-fg": "#065F46",
          "review-bg": "#FFFBEB",
          "review-fg": "#92400E",
          "rejected-bg": "#FEF2F2",
          "rejected-fg": "#991B1B",
        },
        xai: {
          "weight-positive": "#059669",
          "weight-negative": "#E11D48",
          confidence: "#0284C7",
        },
      },
      fontFamily: {
        sans: ['"Hanken Grotesk"', "system-ui", "-apple-system", "sans-serif"],
        headline: ['"Hanken Grotesk"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px",
      },
    },
  },
  plugins: [],
};
