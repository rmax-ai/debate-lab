import type { DebateRun } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function createRun(data: {
  topic: string;
  context?: string;
  goal: string;
  constraints?: string;
  max_rounds?: number;
  preset?: string;
}): Promise<DebateRun> {
  const res = await fetch(`${API_BASE}/api/v1/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create run: ${res.statusText}`);
  return res.json();
}

export async function getRun(id: string): Promise<DebateRun> {
  const res = await fetch(`${API_BASE}/api/v1/runs/${id}`);
  if (!res.ok) throw new Error(`Run not found: ${id}`);
  return res.json();
}

export async function listRuns(): Promise<DebateRun[]> {
  const res = await fetch(`${API_BASE}/api/v1/runs`);
  if (!res.ok) throw new Error("Failed to list runs");
  return res.json();
}

export async function getReport(id: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/v1/runs/${id}/report`);
  if (!res.ok) throw new Error("Report not available");
  return res.json();
}

export function getEventStreamUrl(runId: string): string {
  return `${API_BASE}/api/v1/runs/${runId}/events`;
}
