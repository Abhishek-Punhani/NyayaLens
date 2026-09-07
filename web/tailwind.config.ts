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
        background: "#1a1a1a",
        surface: "#262626",
        "surface-hover": "#2f2f2f",
        border: "#383838",
        accent: {
          DEFAULT: "#d97706",
          dim: "#92400e",
          light: "#f59e0b",
        },
        muted: "#9ca3af",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["Space Mono", "JetBrains Mono", "monospace"],
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'none' }
        }
      },
      animation: {
        'fadeIn': 'fadeIn 0.3s ease'
      }
    },
  },
  plugins: [],
};
export default config;
