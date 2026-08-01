import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/providers/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        "background-2": "hsl(var(--background-2))",
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
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        brand: {
          purple: "#A78BFA",
          cyan: "#59D6FF",
          blue: "#7C8CF8",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 6px)",
        "2xl": "calc(var(--radius) + 12px)",
        "3xl": "calc(var(--radius) + 18px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Rubik", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -8px hsl(var(--primary) / 0.5)",
        "glow-cyan": "0 0 40px -8px hsl(var(--info) / 0.5)",
        "glow-accent": "0 0 40px -8px hsl(var(--accent) / 0.5)",
        soft: "0 8px 40px -12px rgba(0, 0, 0, 0.4)",
        "soft-lg": "0 24px 80px -24px rgba(0, 0, 0, 0.5)",
        "inner-glow": "inset 0 1px 0 0 hsl(var(--foreground) / 0.06)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        aurora: {
          "0%, 100%": { transform: "translate(0, 0) rotate(0deg) scale(1)" },
          "25%": { transform: "translate(-5%, 8%) rotate(8deg) scale(1.08)" },
          "50%": { transform: "translate(4%, -6%) rotate(-6deg) scale(0.96)" },
          "75%": { transform: "translate(-3%, 4%) rotate(4deg) scale(1.05)" },
        },
        mesh: {
          "0%, 100%": { "background-position": "0% 0%" },
          "50%": { "background-position": "100% 100%" },
        },
        beam: {
          "0%": { transform: "translateX(-100%) skewX(-12deg)", opacity: "0" },
          "20%": { opacity: "0.6" },
          "80%": { opacity: "0.6" },
          "100%": { transform: "translateX(220%) skewX(-12deg)", opacity: "0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-14px)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "spin-slow": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        orbit: {
          "0%": { transform: "rotate(0deg) translateX(var(--orbit-r)) rotate(0deg)" },
          "100%": { transform: "rotate(360deg) translateX(var(--orbit-r)) rotate(-360deg)" },
        },
        "gradient-x": {
          "0%, 100%": { "background-position": "0% 50%" },
          "50%": { "background-position": "100% 50%" },
        },
        "border-flow": {
          "0%": { "background-position": "0% 50%" },
          "50%": { "background-position": "100% 50%" },
          "100%": { "background-position": "0% 50%" },
        },
        "bounce-dot": {
          "0%, 80%, 100%": { transform: "translateY(0)", opacity: "0.4" },
          "40%": { transform: "translateY(-6px)", opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(24px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px -4px hsl(var(--primary) / 0.35)" },
          "50%": { boxShadow: "0 0 44px -4px hsl(var(--primary) / 0.65)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 2s linear infinite",
        aurora: "aurora 14s ease-in-out infinite",
        mesh: "mesh 18s ease-in-out infinite",
        beam: "beam 3.2s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
        marquee: "marquee 32s linear infinite",
        "spin-slow": "spin-slow 8s linear infinite",
        orbit: "orbit 20s linear infinite",
        "gradient-x": "gradient-x 6s ease infinite",
        "border-flow": "border-flow 4s ease infinite",
        "bounce-dot": "bounce-dot 1.2s ease-in-out infinite",
        "fade-up": "fade-up 0.6s ease-out both",
        "scale-in": "scale-in 0.35s ease-out both",
        "slide-in-right": "slide-in-right 0.4s ease-out both",
        "glow-pulse": "glow-pulse 2.4s ease-in-out infinite",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [typography],
};

export default config;
