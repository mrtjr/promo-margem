// Tailwind resolve `content` paths relativo a process.cwd(), nao ao
// diretorio deste config. O electron-vite roda do root do projeto, mas
// nosso renderer mora em ./frontend/ — paths como "./src/**/*" caem em
// <root>/src/ (inexistente) e o scan vira vazio (CSS final = so preflight).
//
// Fix: paths absolutos calculados a partir deste config. Mesma tecnica
// do postcss.config.js (Fase 3).
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    resolve(here, 'index.html'),
    resolve(here, 'src/**/*.{js,ts,jsx,tsx}'),
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'Iowan Old Style', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'Menlo', 'monospace'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Paleta Claude Design — referência direta para classes utilitárias
        claude: {
          coral:      "#CC785C",
          "coral-soft":"#E8B5A2",
          cream:      "#F5F4ED",
          "cream-deep":"#EFEADC",
          ink:        "#1C1B17",
          stone:      "#6B6558",
          sage:       "#7A8B5F",
          amber:      "#D4A24C",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      letterSpacing: {
        tightest: "-0.04em",
        editorial: "-0.02em",
      },
    },
  },
  plugins: [],
}
