"use client";

import { create } from "zustand";
import type { ChatMessage } from "@/types";

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  send: (text: string) => void;
  clear: () => void;
}

export const useChat = create<ChatState>((set, get) => ({
  messages: [
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm your automation copilot. Describe what you want to automate and I'll design, validate, and deploy the workflow for you.\n\nTry something like:\n- \"When a new contact is created in HubSpot, enrich it with GitHub and log it to Airtable\"\n- \"Send a weekly revenue summary from Stripe to my email every Monday\"",
      timestamp: new Date().toISOString(),
    },
  ],
  isStreaming: false,
  send: async (text) => {
    const trimmed = text.trim();
    if (!trimmed || get().isStreaming) return;
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isStreaming: true }));

    const reply = buildReply(trimmed);
    const assistantId = `a_${Date.now()}`;
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date().toISOString(),
          thinking: true,
          streaming: true,
        },
      ],
    }));

    await new Promise((r) => setTimeout(r, 1400));
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === assistantId ? { ...m, thinking: false, content: reply.text } : m,
      ),
    }));
    await new Promise((r) => setTimeout(r, 500));
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === assistantId
          ? { ...m, clarifications: reply.clarifications, workflowPreview: reply.preview, streaming: false }
          : m,
      ),
      isStreaming: false,
    }));
  },
  clear: () => set({ messages: [] }),
}));

function buildReply(prompt: string) {
  const lower = prompt.toLowerCase();
  if (lower.includes("slack") || lower.includes("email") || lower.includes("notify")) {
    return {
      text:
        "I've designed a **notification workflow** for you. It watches for new inbound events, classifies priority with an AI step, and routes alerts to Slack with fallback to email on failure.\n\nHere's the plan I compiled:",
      clarifications: ["Which channel should alerts go to?", "Include daily digest as well?", "Add human approval step?"],
      preview: {
        name: "Smart Notification Router",
        description: "Classify inbound events and route alerts intelligently",
        steps: [
          { connector: "gmail", action: "New Email", label: "Watch inbox" },
          { connector: "ai", action: "Classify", label: "Priority + intent" },
          { connector: "slack", action: "Post Message", label: "Route alert" },
        ],
        estimate: "~2.1s avg · 99.4% success",
      },
    };
  }
  if (lower.includes("lead") || lower.includes("crm") || lower.includes("hubspot")) {
    return {
      text:
        "I've designed a **lead intelligence pipeline**. New contacts are enriched with developer activity, scored for fit, and routed to your CRM plus a Slack notification for high-value leads.\n\nHere's the compiled plan:",
      clarifications: ["Score leads over 80 points only?", "Sync to Airtable too?", "Notify sales on enterprise accounts?"],
      preview: {
        name: "Lead Intelligence Pipeline",
        description: "Enrich, score, and route new leads automatically",
        steps: [
          { connector: "hubspot", action: "Contact Created", label: "New lead" },
          { connector: "github", action: "Enrich Profile", label: "Dev activity" },
          { connector: "ai", action: "Score Fit", label: "Lead scoring" },
          { connector: "airtable", action: "Create Record", label: "File lead" },
        ],
        estimate: "~4.2s avg · 98.6% success",
      },
    };
  }
  if (lower.includes("invoice") || lower.includes("payment") || lower.includes("stripe")) {
    return {
      text:
        "I've designed a **payments automation**. Paid invoices are reconciled against your ledger, receipts are filed to Drive, and a Slack digest notifies finance each evening.\n\nHere's the compiled plan:",
      clarifications: ["Digest at 6pm daily?", "Include failed-payment alerts?", "Attach PDF receipts to Drive?"],
      preview: {
        name: "Payments Reconciliation",
        description: "Reconcile invoices and notify finance automatically",
        steps: [
          { connector: "stripe", action: "Invoice Paid", label: "Payment event" },
          { connector: "postgres", action: "Run Query", label: "Reconcile ledger" },
          { connector: "google-drive", action: "Upload File", label: "File receipt" },
          { connector: "slack", action: "Post Message", label: "Finance digest" },
        ],
        estimate: "~1.8s avg · 99.9% success",
      },
    };
  }
  return {
    text:
      "I've analyzed your request and compiled a **general automation plan**. I can scaffold the workflow now and refine it once you confirm the details.\n\nHere's what I propose:",
    clarifications: ["What triggers this workflow?", "Which connectors should be involved?", "How should failures be handled?"],
    preview: {
      name: "New Automation",
      description: "Scaffold from your description",
      steps: [
        { connector: "webhook", action: "Trigger", label: "Event source" },
        { connector: "ai", action: "Transform", label: "Process payload" },
        { connector: "slack", action: "Post Message", label: "Deliver result" },
      ],
      estimate: "~2.5s avg · 98.0% success",
    },
  };
}
