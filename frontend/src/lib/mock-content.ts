import type { FaqItem, Feature, Integration, PricingTier, Testimonial } from "@/types";

export const features: Feature[] = [
  {
    icon: "wand2",
    title: "Describe it. We build it.",
    description: "Type what you want in plain English and the AI Planner compiles a validated, executable workflow graph instantly.",
    gradient: "from-violet-500 to-indigo-500",
  },
  {
    icon: "workflow",
    title: "Visual workflow builder",
    description: "Drag, connect, and arrange nodes on an infinite canvas with live execution states, auto-layout, and undo history.",
    gradient: "from-cyan-400 to-sky-500",
  },
  {
    icon: "plug",
    title: "200+ connectors",
    description: "Slack, Gmail, GitHub, Stripe, Notion and more. One OAuth flow, automatic token refresh, and per-connector rate limits.",
    gradient: "from-emerald-400 to-teal-500",
  },
  {
    icon: "shield",
    title: "Enterprise-grade security",
    description: "SOC 2, encrypted secrets, granular permissions, tenant isolation, and full audit trails on every execution.",
    gradient: "from-amber-400 to-orange-500",
  },
  {
    icon: "gauge",
    title: "Observability built-in",
    description: "Latency, cost, retries and failure analytics per workflow, node and connector - streaming in real time.",
    gradient: "from-rose-400 to-pink-500",
  },
  {
    icon: "rocket",
    title: "Deploy in seconds",
    description: "Versioned specifications, automatic rollbacks, and zero-downtime updates. Your automations just keep running.",
    gradient: "from-blue-500 to-violet-500",
  },
];

export const integrations: Integration[] = [
  { name: "Slack", logo: "slack", color: "#611f69" },
  { name: "Gmail", logo: "mail", color: "#EA4335" },
  { name: "GitHub", logo: "github", color: "#24292F" },
  { name: "Notion", logo: "notion", color: "#111111" },
  { name: "Stripe", logo: "stripe", color: "#635BFF" },
  { name: "Shopify", logo: "shopping-bag", color: "#96BF48" },
  { name: "Discord", logo: "message-square", color: "#5865F2" },
  { name: "Linear", logo: "git-branch", color: "#5E6AD2" },
  { name: "Airtable", logo: "table", color: "#F82B60" },
  { name: "Google Drive", logo: "hard-drive", color: "#4285F4" },
  { name: "HubSpot", logo: "users", color: "#FF7A59" },
  { name: "PostgreSQL", logo: "database", color: "#336791" },
];

export const testimonials: Testimonial[] = [
  {
    name: "Sarah Chen", role: "VP Engineering", company: "Acme Corp",
    quote: "We replaced six point solutions with AutoFlow. The AI builder wrote our entire ops pipeline in a weekend.",
    avatarColor: "from-violet-500 to-indigo-500",
  },
  {
    name: "Marcus Reid", role: "Head of Growth", company: "Nimbus",
    quote: "The planner understands intent better than any tool we have used. Our lead-to-cash automation went live in hours.",
    avatarColor: "from-cyan-400 to-sky-500",
  },
  {
    name: "Priya Patel", role: "Founder", company: "Loopline",
    quote: "It feels like magic. I describe the workflow and watch the graph assemble itself - then it just runs.",
    avatarColor: "from-emerald-400 to-teal-500",
  },
  {
    name: "James Okafor", role: "DevOps Lead", company: "Corestack",
    quote: "Observability is incredible. Per-node latency and cost breakdowns helped us cut our connector spend by 40%.",
    avatarColor: "from-amber-400 to-orange-500",
  },
  {
    name: "Elena Rossi", role: "COO", company: "Brightpath",
    quote: "Our team shipped 30 automations in the first month. Support loves the AI triage workflow we built in minutes.",
    avatarColor: "from-rose-400 to-pink-500",
  },
  {
    name: "Tom Becker", role: "CTO", company: "Fleetline",
    quote: "The workflow builder is the best I have used - it finally feels like a real product, not a prototype.",
    avatarColor: "from-blue-500 to-violet-500",
  },
];

export const pricingTiers: PricingTier[] = [
  {
    name: "Starter", price: 0, cadence: "/mo",
    description: "For individuals exploring automation.",
    features: ["10 workflows", "20 active connectors", "1,000 runs / month", "Community support", "Core integrations"],
    cta: "Start for free",
  },
  {
    name: "Pro", price: 49, cadence: "/mo",
    description: "For teams building serious automations.",
    features: [
      "Unlimited workflows", "200+ connectors", "50,000 runs / month", "AI Planner & compiler", "Advanced analytics", "Priority support",
    ],
    highlight: true,
    cta: "Start 14-day trial",
  },
  {
    name: "Enterprise", price: 499, cadence: "/mo",
    description: "For organizations with compliance needs.",
    features: [
      "Everything in Pro", "Unlimited runs", "SSO / SAML", "SOC 2 report & DPA", "Dedicated success manager", "99.99% SLA",
    ],
    cta: "Talk to sales",
  },
];

export const faqItems: FaqItem[] = [
  {
    question: "How does the AI Planner work?",
    answer: "Describe your automation in plain language. The planner detects intent, extracts tasks, discovers matching connectors, resolves dependencies, and compiles a validated workflow specification - no prompts required.",
  },
  {
    question: "Which connectors are supported?",
    answer: "Over 200 connectors including Slack, Gmail, GitHub, Stripe, Notion, Shopify, Discord, Linear, Airtable and PostgreSQL - with OAuth, API keys, and automatic token refresh.",
  },
  {
    question: "Is my data secure?",
    answer: "Yes. Credentials are encrypted at rest, secrets are scoped per tenant, and every execution is audited. We are SOC 2 Type II certified and GDPR compliant.",
  },
  {
    question: "Can I migrate from Zapier or Make?",
    answer: "Absolutely. Import existing workflows and we map them to native AutoFlow nodes. Our planner can even recreate legacy automations from a plain-English description.",
  },
  {
    question: "What happens if a workflow fails?",
    answer: "Built-in retries with exponential backoff, per-node dead-letter queues, and automatic rollback. You get full error context and one-click replay for any execution.",
  },
  {
    question: "Do you offer a free trial?",
    answer: "The Pro plan includes a 14-day free trial with no credit card required. The Starter plan is free forever with 1,000 runs per month.",
  },
];
