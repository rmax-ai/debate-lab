"use client";

import { useDebateStore } from "@/stores/debate-store";

export function ToolCallsLog() {
  const toolCalls = useDebateStore((s) => s.toolCalls);

  if (!toolCalls.length) {
    return <p className="text-sm text-zinc-500 py-8 text-center">No tool calls yet.</p>;
  }

  return (
    <div className="space-y-1 max-h-[500px] overflow-y-auto">
      {toolCalls.map((call, i) => (
        <div key={i} className="text-xs border-b border-zinc-100 dark:border-zinc-800 py-1">
          <span className="font-mono text-zinc-500">{call.type.replace(/_/g, " ")}</span>
          {call.agent_id && (
            <span className="text-zinc-400 ml-2">by {call.agent_id}</span>
          )}
          {call.tool_name && (
            <span className="text-blue-500 ml-2">{call.tool_name}</span>
          )}
          {call.result_summary && (
            <span className="text-zinc-600 dark:text-zinc-400 ml-2 truncate block">
              {call.result_summary.slice(0, 100)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
