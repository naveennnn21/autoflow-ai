"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChat } from "@/stores/chat";

export function ClarificationCard({ question }: { question: string }) {
  const [selected, setSelected] = useState(false);
  const send = useChat((s) => s.send);

  const handle = () => {
    if (selected) return;
    setSelected(true);
    send(`Yes — ${question}`);
  };

  return (
    <motion.button
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.97 }}
      onClick={handle}
      className={cn(
        "group flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
        selected
          ? "border-success/40 bg-success/10 text-success"
          : "border-border bg-card text-foreground hover:border-primary/50 hover:bg-primary/5",
      )}
    >
      {selected ? <Check className="h-3.5 w-3.5" /> : <span className="h-1.5 w-1.5 rounded-full bg-primary/60 group-hover:bg-primary" />}
      {question}
    </motion.button>
  );
}
