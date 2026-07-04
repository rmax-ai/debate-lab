"use client";

import { useDebateStore } from "@/stores/debate-store";

export function TranscriptView() {
  const events = useDebateStore((s) => s.events);

  if (!events.length) {
    return <p className="text-sm text-zinc-500 py-8 text-center">No events yet.</p>;
  }

  const displayEvents = ["run_created", "agents_selected", "research_plan_created",
    "opening_position", "claim_extracted", "claim_challenged", "position_revised",
    "final_report", "run_completed", "run_failed"];

  const filtered = events.filter((e) => displayEvents.includes(e.event_type));

  return (
    <div className="space-y-3 max-h-[600px] overflow-y-auto">
      {filtered.map((event, i) => (
        <div key={i} className="border-l-2 border-zinc-200 dark:border-zinc-700 pl-3 py-1">
          <div className="text-xs text-zinc-500 font-medium uppercase">
            {event.event_type.replace(/_/g, " ")}
            {event.actor && <span className="ml-2 font-normal">— {event.actor}</span>}
          </div>
          <div className="text-sm text-zinc-700 dark:text-zinc-300 mt-1">
            <pre className="whitespace-pre-wrap font-sans text-sm">
              {JSON.stringify(event.payload, null, 0).slice(0, 200)}
            </pre>
          </div>
        </div>
      ))}
    </div>
  );
}
