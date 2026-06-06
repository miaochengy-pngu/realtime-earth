/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,ts,js,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        space: {
          950: "#050a18",
          900: "#0b1220",
          800: "#101a2e",
          700: "#172238",
        },
        accent: {
          DEFAULT: "#22d3ee",
          dim: "#0e7490",
        },
      },
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        glow: "0 0 20px rgba(34, 211, 238, 0.4)",
      },
    },
  },
  plugins: [],
};
