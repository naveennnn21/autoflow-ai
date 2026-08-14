"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Settings2, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Node } from "@xyflow/react";

export function NodeInspector({
  node,
  onChange,
  onDelete,
}: {
  node: Node | null;
  onChange: (patch: Partial<{ label: string; connector: string; action: string; prompt: string }>) => void;
  onDelete: () => void;
}) {
  return (
    <AnimatePresence>
      {node ? (
        <motion.div
          key="inspector"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ type: "spring", stiffness: 260, damping: 26 }}
          className="flex w-60 shrink-0 flex-col gap-3 overflow-y-auto rounded-xl border border-border bg-card/60 p-3 no-scrollbar"
        >
          <div className="flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Settings2 className="h-3.5 w-3.5" />
              Node settings
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                className="h-6 w-6 text-destructive hover:bg-destructive/10"
                aria-label="Delete node"
                onClick={onDelete}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                className="h-6 w-6"
                aria-label="Close inspector"
                onClick={onDelete}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ni-label" className="text-[11px] font-medium">Label</Label>
            <Input
              id="ni-label"
              value={String(node.data?.label ?? "")}
              onChange={(e) => onChange({ label: e.target.value })}
              className="h-8 text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ni-connector" className="text-[11px] font-medium">Connector</Label>
            <Input
              id="ni-connector"
              value={String(node.data?.connector ?? "")}
              onChange={(e) => onChange({ connector: e.target.value })}
              className="h-8 text-sm"
              placeholder="e.g. slack, gmail, notion"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ni-action" className="text-[11px] font-medium">Action</Label>
            <Input
              id="ni-action"
              value={String(node.data?.action ?? "")}
              onChange={(e) => onChange({ action: e.target.value })}
              className="h-8 text-sm"
              placeholder="e.g. post_message"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ni-prompt" className="text-[11px] font-medium">Prompt</Label>
            <Textarea
              id="ni-prompt"
              value={String(node.data?.prompt ?? "")}
              onChange={(e) => onChange({ prompt: e.target.value })}
              className="min-h-24 text-xs"
              placeholder="Instructions for this step..."
            />
          </div>
        </motion.div>
      ) : (
        <motion.div
          key="empty"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex w-44 shrink-0 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border/60 p-4 text-center"
        >
          <Settings2 className="h-5 w-5 text-muted-foreground/40" />
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Select a node to edit its connector, action, and prompt
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
