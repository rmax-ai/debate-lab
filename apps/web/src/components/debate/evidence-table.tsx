"use client";

import { useDebateStore } from "@/stores/debate-store";

export function EvidenceView() {
  const evidence = useDebateStore((s) => s.evidence);

  const items = Object.values(evidence);

  if (!items.length) {
    return <p className="text-sm text-zinc-500 py-8 text-center">No evidence gathered yet.</p>;
  }

  return (
    <div className="space-y-2">
      {items.map((ref) => (
        <div key={ref.id} className="border rounded-lg p-3 space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-zinc-500">{ref.id}</span>
            <span className="text-sm font-medium">{ref.title}</span>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">{ref.quote_or_excerpt}</p>
          <div className="flex items-center gap-3 text-xs text-zinc-500">
            <span>Source: {ref.source_type}</span>
            {ref.url && (
              <a href={ref.url} target="_blank" rel="noopener" className="text-blue-500 hover:underline">
                link
              </a>
            )}
            <span>Reliability: {(ref.reliability_score * 100).toFixed(0)}%</span>
            <span>by {ref.retrieved_by}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
