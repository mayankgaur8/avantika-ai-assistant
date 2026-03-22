import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f0f4ff",
          100: "#e0e9ff",
          200: "#bfcfff",
          300: "#8fa8ff",
          400: "#5678ff",
          500: "#2d4eff",    // primary brand blue
          600: "#1a35e6",
          700: "#1228bf",
          800: "#0f1f99",
          900: "#0b1673",
        },
        accent: {
          400: "#f97316",    // orange accent
          500: "#ea6c00",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
