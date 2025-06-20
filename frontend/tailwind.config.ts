import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        coral: {
          DEFAULT: '#FF6B6B',
          dark: '#E85555',
          light: '#FF8A8A',
        },
        teal: {
          DEFAULT: '#4ECDC4',
          dark: '#3BA99F',
          light: '#6FD8D1',
        },
        dark: {
          DEFAULT: '#1a1a2e',
          card: 'rgba(26, 26, 46, 0.8)',
          lighter: '#16213e',
          darker: '#0f1419',
        }
      },
      backgroundImage: {
        'dark-gradient': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%)',
        'coral-gradient': 'linear-gradient(135deg, #FF6B6B 0%, #E85555 100%)',
        'teal-gradient': 'linear-gradient(135deg, #4ECDC4 0%, #3BA99F 100%)',
        'text-gradient': 'linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '10px',
        lg: '20px',
      },
      boxShadow: {
        'coral': '0 10px 30px rgba(255, 107, 107, 0.3)',
        'teal': '0 10px 30px rgba(78, 205, 196, 0.3)',
        'glow': '0 0 20px rgba(255, 107, 107, 0.5)',
      }
    },
  },
  plugins: [],
};

export default config;