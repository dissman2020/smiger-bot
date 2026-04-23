import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7ee",
          100: "#d5edd5",
          200: "#a8dba8",
          300: "#72c372",
          400: "#4caf50",
          500: "#2e7d32",
          600: "#256b29",
          700: "#1b5e20",
          800: "#164d1a",
          900: "#0e3b11",
        },
        dark: {
          50: "#f7f7f8",
          100: "#eeeef0",
          200: "#d9d9de",
          300: "#b8b8c0",
          400: "#91919e",
          500: "#747483",
          600: "#5e5e6b",
          700: "#4d4d57",
          800: "#2a2a32",
          900: "#1a1a22",
          950: "#111118",
        },
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
