"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Badge } from "@/components/ui/badge";
import type { RunStatus } from "@/lib/types";

function statusVariant(s: string) {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    proposed: "secondary",
    challenged: "destructive",
    supported: "default",
    weakened: "outline",
    accepted: "default",
    unresolved: "secondary",
  };
  return map[s] || "outline";
}

export function ClaimsView() {
  const claims = useDebateStore((s) => s.claims);

  const claimsList = Object.values(claims);

  if (!claimsList.length) {
    return <p className="text-sm text-zinc-500 py-8 text-center">No claims yet.</p>;
  }

  return (
    <div className="space-y-3">
      {claimsList.map((claim) => (
        <div key={claim.id} className="border rounded-lg p-3 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div>
              <span className="font-mono text-xs text-zinc-500">{claim.id}</span>
              <span className="text-xs text-zinc-400 ml-2">by {claim.agent_id}</span>
            </div>
            <Badge variant={statusVariant(claim.status)} className="text-xs">
              {claim.status}
            </Badge>
          </div>
          <p className="text-sm">{claim.text}</p>
          {claim.evidence_refs.length > 0 && (
            <div className="text-xs text-zinc-500">
              Evidence: {claim.evidence_refs.join(", ")}
            </div>
          )}
          {claim.objections.length > 0 && (
            <div className="text-xs text-red-600">
              Objections: {claim.objections.join("; ")}
            </div>
          )}
          {claim.confidence != null && (
            <div className="text-xs text-zinc-500">
              Confidence: {(claim.confidence * 100).toFixed(0)}%
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
