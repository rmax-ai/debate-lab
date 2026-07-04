"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Badge } from "@/components/ui/badge";
import type { RunStatus } from "@/lib/types";

const PHASES: { phase: RunStatus; label: string }[] = [
  { phase: "pending", label: "Intake" },
  { phase: "planning", label: "Agents" },
  { phase: "researching", label: "Research" },
  { phase: "arguing", label: "Positions" },
  { phase: "challenging", label: "Cross-Exam" },
  { phase: "revising", label: "Revision" },
  { phase: "synthesizing", label: "Synthesis" },
  { phase: "auditing", label: "Audit" },
  { phase: "complete", label: "Complete" },
];

function statusBadge(phase: RunStatus) {
  if (phase === "complete") return "default" as const;
  if (phase === "failed") return "destructive" as const;
  if (phase === "pending") return "secondary" as const;
  return "outline";
}

export function Timeline() {
  const phase = useDebateStore((s) => s.phase);

  const currentIdx = PHASES.findIndex((p) => p.phase === phase);

  return (
    <div className="space-y-1">
      <h3 className="text-sm font-semibold mb-2">Debate Timeline</h3>
      {PHASES.map((p, i) => {
        const isDone = i < currentIdx;
        const isCurrent = i === currentIdx;
        const isFuture = i > currentIdx;

        return (
          <div key={p.phase} className="flex items-center gap-2 py-1">
            <div
              className={`w-2 h-2 rounded-full ${
                isDone
                  ? "bg-green-500"
                  : isCurrent
                  ? "bg-blue-500 animate-pulse"
                  : "bg-zinc-300 dark:bg-zinc-600"
              }`}
            />
            <span
              className={`text-sm ${
                isFuture ? "text-zinc-400" : "text-zinc-900 dark:text-zinc-100"
              }`}
            >
              {p.label}
            </span>
            {isCurrent && (
              <Badge variant={statusBadge(phase)} className="ml-auto text-xs">
                active
              </Badge>
            )}
            {phase === "complete" && i === currentIdx && (
              <Badge variant="default" className="ml-auto text-xs">
                done
              </Badge>
            )}
          </div>
        );
      })}
    </div>
  );
}
