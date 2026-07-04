"use client";

import { useEffect, useRef } from "react";
import { getEventStreamUrl } from "@/lib/api";
import { useDebateStore } from "@/stores/debate-store";
import type { DebateEvent } from "@/lib/types";

export function useSSE(runId: string | null) {
  const sourceRef = useRef<EventSource | null>(null);
  const appendEvent = useDebateStore((s) => s.appendEvent);

  useEffect(() => {
    if (!runId) return;

    const url = getEventStreamUrl(runId);
    const source = new EventSource(url);

    source.addEventListener("message", (e) => {
      try {
        const event: DebateEvent = JSON.parse(e.data);
        appendEvent(event);
      } catch {
        // skip malformed events
      }
    });

    source.addEventListener("error", () => {
      // EventSource auto-reconnects
    });

    sourceRef.current = source;
    return () => source.close();
  }, [runId, appendEvent]);
}
