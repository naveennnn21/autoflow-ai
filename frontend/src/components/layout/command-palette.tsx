"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Command as CommandPrimitive } from "cmdk";
import { Search, CornerDownLeft } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useCommand } from "@/stores/command";
import { navGroups } from "@/lib/navigation";
import { Icon } from "@/components/shared/icons";
import { workflows } from "@/lib/mock-workflows";
import { connectors } from "@/lib/mock-connectors";

const Command = CommandPrimitive;

export function CommandPalette() {
  const router = useRouter();
  const { open, setOpen } = useCommand();

  const run = (fn: () => void) => {
    setOpen(false);
    setTimeout(fn, 80);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="top-[18%] translate-y-0 gap-0 overflow-hidden p-0 sm:top-[18%]">
        <Command className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground">
          <div className="flex items-center gap-2 border-b border-border px-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <Command.Input
              placeholder="Search workflows, connectors, pages..."
              className="flex h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">ESC</kbd>
          </div>
          <Command.List className="max-h-[300px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>
            {navGroups.map((group) => (
              <Command.Group key={group.group} heading={group.group}>
                {group.items.map((item) => (
                  <Command.Item
                    key={item.href}
                    value={`nav ${item.label}`}
                    onSelect={() => run(() => router.push(item.href))}
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm outline-none data-[selected=true]:bg-accent/10"
                  >
                    <Icon name={item.icon} className="h-4 w-4 text-muted-foreground" />
                    <span>{item.label}</span>
                    {item.badge ? (
                      <span className="ml-auto rounded-full bg-primary/20 px-2 py-0.5 text-[10px] text-primary">{item.badge}</span>
                    ) : null}
                  </Command.Item>
                ))}
              </Command.Group>
            ))}
            <Command.Group heading="Workflows">
              {workflows.slice(0, 5).map((wf) => (
                <Command.Item
                  key={wf.id}
                  value={`workflow ${wf.name}`}
                  onSelect={() => run(() => router.push(`/workflows/${wf.id}/builder`))}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm outline-none data-[selected=true]:bg-accent/10"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-success glow-dot" />
                  <span>{wf.name}</span>
                </Command.Item>
              ))}
            </Command.Group>
            <Command.Group heading="Connectors">
              {connectors.slice(0, 5).map((c) => (
                <Command.Item
                  key={c.id}
                  value={`connector ${c.name}`}
                  onSelect={() => run(() => router.push(`/marketplace/${c.slug}`))}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm outline-none data-[selected=true]:bg-accent/10"
                >
                  <Icon name={c.logo} className="h-4 w-4" style={{ color: c.color }} />
                  <span>{c.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{c.category}</span>
                </Command.Item>
              ))}
            </Command.Group>
            <div className="mt-2 flex items-center gap-2 border-t border-border px-3 py-2 text-xs text-muted-foreground">
              <kbd className="rounded border border-border px-1"><CornerDownLeft className="h-3 w-3" /></kbd>
              <span>to select · arrows to navigate</span>
            </div>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
