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
        elevated: "hsl(var(--elevated))",
        surface: "hsl(var(--surface))",
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
        error: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        brand: {
          purple: "#A78BFA",
          cyan: "#59D6FF",
          blue: "#7C8CF8",
          bg: "#0B1018",
          "bg-2": "#101827",
          elevated: "#161F2C",
          surface: "#1B2636",
          border: "#2A3A52",
          success: "#4ADE80",
          warning: "#FBBF24",
          error: "#FB7185",
          text: "#F7F9FC",
          "text-secondary": "#B5C0D0",
          muted: "#778399",
          paper: "#F5F7FA",
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
      fontSize: {
        hero: "clamp(3.75rem, 9vw, 9.5rem)",
        section: "clamp(2.75rem, 6vw, 6.5rem)",
        display: "clamp(2.25rem, 4.5vw, 4.5rem)",
        title: "clamp(1.875rem, 3vw, 3rem)",
      },
      lineHeight: {
        tightest: "0.95",
        tighter: "1.05",
      },
      letterSpacing: {
        tighter: "-0.03em",
        tightest: "-0.045em",
        "wide-2": "0.12em",
      },
      boxShadow: {
        glow: "0 0 40px -8px hsl(var(--primary) / 0.5)",
        "glow-cyan": "0 0 40px -8px hsl(var(--info) / 0.5)",
        "glow-accent": "0 0 40px -8px hsl(var(--accent) / 0.5)",
        "glow-success": "0 0 40px -8px hsl(var(--success) / 0.5)",
        "glow-warning": "0 0 40px -8px hsl(var(--warning) / 0.5)",
        "glow-destructive": "0 0 40px -8px hsl(var(--destructive) / 0.5)",
        "glow-soft": "0 0 48px -12px hsl(var(--primary) / 0.35)",
        "glow-ring": "0 0 0 1px hsl(var(--ring) / 0.6), 0 0 32px -4px hsl(var(--ring) / 0.45)",
        "elevation-1": "var(--elevation-1)",
        "elevation-2": "var(--elevation-2)",
        "elevation-3": "var(--elevation-3)",
        soft: "0 8px 40px -12px rgba(0, 0, 0, 0.4)",
        "soft-lg": "0 24px 80px -24px rgba(0, 0, 0, 0.5)",
        "inner-glow": "inset 0 1px 0 0 hsl(var(--foreground) / 0.06)",
        lift: "0 1px 0 0 hsl(var(--foreground) / 0.04), 0 12px 48px -16px rgba(0, 0, 0, 0.6)",
        hairline: "inset 0 1px 0 0 hsl(var(--foreground) / 0.05)",
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
        "float-slow": {
          "0%, 100%": { transform: "translateY(0) translateX(0)" },
          "50%": { transform: "translateY(-22px) translateX(8px)" },
        },
        drift: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "33%": { transform: "translate(3%, -4%) scale(1.04)" },
          "66%": { transform: "translate(-3%, 3%) scale(0.97)" },
        },
        "dash-flow": {
          to: { "stroke-dashoffset": "-24" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "0.35" },
          "50%": { opacity: "0.85" },
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
        "wiggle": {
          "0%, 100%": { transform: "rotate(-3deg)" },
          "50%": { transform: "rotate(3deg)" },
        },
        "line-grow": {
          from: { transform: "scaleX(0)" },
          to: { transform: "scaleX(1)" },
        },
        "flicker": {
          "0%, 100%": { opacity: "1" },
          "92%": { opacity: "1" },
          "93%": { opacity: "0.4" },
          "94%": { opacity: "1" },
          "97%": { opacity: "0.6" },
          "98%": { opacity: "1" },
        },
        fog: {
          "0%, 100%": { transform: "translate3d(-4%, -2%, 0) scale(1)" },
          "50%": { transform: "translate3d(5%, 3%, 0) scale(1.08)" },
        },
        "fog-reverse": {
          "0%, 100%": { transform: "translate3d(4%, 2%, 0) scale(1.06)" },
          "50%": { transform: "translate3d(-5%, -3%, 0) scale(0.98)" },
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
        "float-slow": "float-slow 11s ease-in-out infinite",
        drift: "drift 22s ease-in-out infinite",
        "dash-flow": "dash-flow 1.1s linear infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
        "pulse-soft": "pulse-soft 4s ease-in-out infinite",
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
        wiggle: "wiggle 5s ease-in-out infinite",
        "line-grow": "line-grow 0.8s cubic-bezier(0.22, 1, 0.36, 1) both",
        flicker: "flicker 6s linear infinite",
        fog: "fog 36s ease-in-out infinite",
        "fog-reverse": "fog-reverse 48s ease-in-out infinite",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [typography],
};

export default config;
