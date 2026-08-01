# AutoFlow AI — Frontend Platform

A premium, dark-first AI automation SaaS frontend built with Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Framer Motion, React Flow, and Zustand.

## Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 15.1 (App Router, RSC + client components) |
| UI | React 19, TypeScript (strict), Tailwind CSS, shadcn-style primitives on Radix UI |
| Motion | Framer Motion (page/layout/spring animations) + CSS keyframes |
| Graphs | @xyflow/react (React Flow) with custom animated nodes |
| Charts | Recharts (dynamically imported, `ssr: false`) |
| State | Zustand (session, workflows, chat, command palette, sidebar) |
| Data | TanStack Query + mock-data services layer with live-API fallback |
| Forms/validation | react-hook-form + zod (available in deps), React Hook Form ready |
| Markdown | react-markdown + remark-gfm with @tailwindcss/typography |
| Notifications | sonner toasts |
| Command palette | cmdk |

## Architecture

```
src/
  app/                    # Routes (App Router)
    page.tsx              # Landing page
    (app)/                # Authenticated workspace (AppShell: sidebar + topbar)
      dashboard/          # Analytics overview
      workflows/          # List + [id]/builder (React Flow canvas)
      chat/               # AI Copilot (streaming, clarification, deploy)
      marketplace/        # Connector marketplace + [slug] detail
      analytics/          # Usage/latency/cost/reliability
      settings/           # Org, API keys, notifications, preferences
    (auth)/               # Login / Register (aurora background)
    not-found.tsx loading.tsx error.tsx
  components/
    ui/                   # Button, Card, Input, Dialog, Tabs, Select, Switch...
    motion/               # Aurora, Particles, Typing, CountUp, Marquee, Shimmer, GlowBorder
    layout/               # AppShell, Sidebar, Topbar, CommandPalette, ThemeToggle, UserMenu
    landing/              # Navbar, Hero, InteractiveDemo, Sections, Social, Footer
    dashboard/            # MetricCard, Charts, ActivityFeed, ExecutionsTable, WorkflowCard
    chat/                 # Message, ChatInput, Clarification, WorkflowPreview
    builder/              # CustomNode, FlowCanvas
    marketplace/          # ConnectorCard
    shared/               # Logo, Icon, StatusBadge, PageHeader, EmptyState
  hooks/                  # useMediaQuery, useCountUp, useDebounce, useHotkey, useLocalStorage
  lib/                    # utils, animations, navigation, mock-* data
  services/               # api.ts (fetch client) + data.ts (mock/API switch)
  stores/                 # Zustand stores
  types/                  # Domain types
```

## Design System

- **Tokens** (`globals.css` + `tailwind.config.ts`): CSS variables for background/foreground, brand (purple #8B5CF6, cyan #22D3EE, blue #3B82F6), success/warning/danger/info, radius, shadows (`shadow-glow`, `shadow-soft`), and a full keyframe/animation token set.
- **Dark-first** with light/system support via next-themes and animated class transitions.
- **Utilities**: `gradient-text`, `gradient-border`, `glass`, `card-hover`, `bg-dots`, `bg-grid`, `no-scrollbar`, reduced-motion support.
- **Typography**: Inter Variable + JetBrains Mono Variable, typography plugin for markdown prose.

## Key Interactions

- **Command palette**: ⌘K opens cmdk search across pages, workflows, and connectors.
- **AI Copilot**: streaming/thinking states, markdown answers, clarification chips, and a Workflow Preview card with a 3-phase deploy animation.
- **Workflow builder**: React Flow canvas with custom nodes (waiting/running/retrying/success states), animated edges, mini-map, and a Test run that lights nodes up sequentially. Canvas is keyed by workflow id so navigation remounts cleanly.
- **Marketplace**: search + category filters, install toasts, connector detail with tabs (overview/actions/triggers/auth).
- **Auth**: animated login/register with magic-link and OAuth affordances.

## Running

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
npm run build     # production build
npm run lint      # eslint (flat config)
npm run typecheck # tsc --noEmit
```

Uses mock data by default (`NEXT_PUBLIC_MOCK` defaults to true). Point `NEXT_PUBLIC_API_URL` at the FastAPI backend and set `NEXT_PUBLIC_MOCK=false` to talk to the real API.

## Validation Status

- TypeScript: pass (strict, no errors)
- ESLint: pass (flat config, next/core-web-vitals + next/typescript, zero warnings)
- Production build: pass — 12 routes, ~106 kB shared First Load JS
- Accessibility: focus rings, aria labels, reduced-motion media query, semantic landmarks
- Responsive: sidebar collapse, grid breakpoints, mobile auth/landing layouts

## Stormy Morning Redesign (v2)

The entire frontend was redesigned around the **Stormy Morning** palette — a dark-first, premium AI-SaaS visual language.

### Color system
| Token | Hex | Role |
|---|---|---|
| Background | `#0B1018` | Near-black base |
| Background 2 | `#101827` | Secondary panels |
| Card | `#161F2C` / Surface `#1B2636` | Elevated surfaces |
| Border | `#2A3A52` | Hairlines |
| Primary | `#7C8CF8` | Periwinkle brand accent |
| Secondary | `#59D6FF` | Cyan |
| Accent | `#A78BFA` | Violet |
| Success / Warning / Danger | `#4ADE80` / `#FBBF24` / `#FB7185` | Semantic |

Legacy `brand-purple` / `brand-cyan` / `brand-blue` utilities are aliased to the new palette, so every pre-existing gradient still resolves.

### Typography
- **Rubik Variable** (300–700) via `@fontsource-variable/rubik` — primary UI font
- **JetBrains Mono Variable** — code font
- `--font-sans` / `--font-mono` CSS variables wired through `tailwind.config.ts`

### Animation system
18 keyframes registered in Tailwind: `aurora`, `mesh`, `beam`, `float`, `pulse-glow`, `marquee`, `spin-slow`, `orbit`, `gradient-x`, `border-flow`, `bounce-dot`, `fade-up`, `scale-in`, `slide-in-right`, `glow-pulse`, `shimmer`, `accordion-*`. Framer Motion drives magnetic buttons, cursor glow, scroll progress, pathname-keyed page transitions, staggered reveals, count-ups, and node execution states.

### Motion primitives (new)
- `Magnetic` — cursor-tracking spring wrapper for CTAs
- `CursorGlow` — ambient cursor-following light
- `ScrollProgress` — top gradient progress bar
- `LightBeams` — staggered sweeping light beams
- `GradientOrb` — pulsing radial gradient orbs
- `PageTransition` — reusable fade/slide wrapper
- `MeshBackground` — animated conic mesh + vignette

### Layout & pages
- **App shell**: pathname-keyed `AnimatePresence` transitions (exit actually fires), cursor glow + scroll progress, glass sidebar (blur-2xl, glow active pill, gradient CTA with shine sweep), topbar with premium search affordance
- **Landing**: hero with aurora + particles + light beams + orbs + magnetic gradient CTAs, animated headline, premium footer with gradient hairline
- **AI chat**: glass bubbles, gradient user messages, glow avatar, premium composer with gradient send button — all with WCAG AA contrast (dark `text-primary-foreground` on light gradients)
- **Builder**: glass custom nodes, glow handles, kind badges with colored glows (flow-canvas execution logic untouched)
- **Marketplace**: connector cards with gradient hairline, connector-color logo glow (`--tw-shadow-color`), gradient install button
- **Auth**: ambient layers + premium glass cards on login/register
- **Dashboard**: glass metric cards with gradient hairline

### Validation
- `tsc --noEmit` ✓ · `eslint --max-warnings=0` ✓ · `next build` ✓ (12 routes) · no TODO/FIXME/lorem ipsum ✓
