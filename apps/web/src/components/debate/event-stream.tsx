"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Badge } from "@/components/ui/badge";

export function EventStream() {
  const events = useDebateStore((s) => s.events);

  if (!events.length) {
    return (
      <p className="text-sm text-zinc-500 py-8 text-center">
        Waiting for debate events...
      </p>
    );
  }

  const recentEvents = events.slice(-50);

  return (
    <div className="space-y-1 max-h-[400px] overflow-y-auto">
      {recentEvents.map((event, i) => (
        <div
          key={i}
          className="flex items-start gap-2 py-1 border-b border-zinc-100 dark:border-zinc-800 text-sm"
        >
          <Badge variant="outline" className="text-xs shrink-0 mt-0.5">
            {event.event_type.replace(/_/g, " ")}
          </Badge>
          {event.actor && (
            <span className="text-zinc-500 text-xs shrink-0">{event.actor}</span>
          )}
          <span className="text-zinc-600 dark:text-zinc-400 truncate">
            {JSON.stringify(event.payload).slice(0, 80)}
          </span>
        </div>
      ))}
    </div>
  );
}
