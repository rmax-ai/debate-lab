"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Badge } from "@/components/ui/badge";

export function AgentPanel() {
  const agents = useDebateStore((s) => s.agents);
  const run = useDebateStore((s) => s.run);

  if (!run) return null;

  const presetAgents = run.selected_agents;

  const displayAgents = presetAgents || Object.entries(agents).map(([id]) => ({
    id,
    name: id,
    role: "",
  }));

  if (!displayAgents?.length) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Agents</h3>
      {displayAgents.map((agent) => {
        const status = agents[agent.id];
        return (
          <div key={agent.id} className="border rounded-lg p-3 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm">{agent.name}</span>
              <Badge variant="outline" className="text-xs">
                {agent.role.slice(0, 30)}
                {agent.role.length > 30 ? "..." : ""}
              </Badge>
            </div>
            {status && (
              <div className="text-xs text-zinc-500 space-x-3">
                <span>Claims: {status.claims_made}</span>
                <span>Challenged: {status.claims_challenged}</span>
                <span>Evidence: {status.evidence_gathered}</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
