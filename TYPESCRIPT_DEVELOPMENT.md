# TypeScript Development Guidelines — DebateLab

Day-to-day TypeScript engineering for the DebateLab Next.js frontend.

---

## Tech Stack

- **Next.js 14+** with App Router
- **React 18+** with Server Components
- **TypeScript 5+** strict mode
- **Tailwind CSS** for styling
- **shadcn/ui** for component library
- **Zustand** for client state
- **TanStack Query** for server state
- **SSE** via native EventSource for live events

---

## Project Structure

```
apps/web/
├── src/
│   ├── app/                  # Next.js App Router
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Home — debate input form
│   │   └── runs/
│   │       └── [id]/
│   │           └── page.tsx  # Live debate run viewer
│   ├── components/
│   │   ├── ui/               # shadcn/ui components
│   │   ├── debate/
│   │   │   ├── input-form.tsx         # Topic/goal/constraints form
│   │   │   ├── timeline.tsx           # Phase progress indicator
│   │   │   ├── agent-panel.tsx        # Active agent status
│   │   │   ├── event-stream.tsx       # Live event feed
│   │   │   ├── claim-card.tsx         # Claim display
│   │   │   ├── evidence-table.tsx     # Evidence list
│   │   │   ├── tool-calls-log.tsx     # Tool invocation log
│   │   │   ├── transcript-view.tsx    # Transcript tab
│   │   │   └── report-view.tsx        # Final report viewer
│   │   └── layout/
│   │       ├── header.tsx
│   │       └── sidebar.tsx
│   ├── stores/
│   │   ├── debate-store.ts    # Zustand — current run state
│   │   └── ui-store.ts        # Zustand — UI state (active tab, etc.)
│   ├── hooks/
│   │   ├── use-debate-run.ts  # TanStack Query — fetch run data
│   │   ├── use-sse.ts         # SSE event subscription
│   │   └── use-claims.ts      # Claim graph data
│   ├── lib/
│   │   ├── api.ts             # Typed API client
│   │   └── types.ts           # Shared TypeScript types
│   └── styles/
│       └── globals.css
├── tailwind.config.ts
├── tsconfig.json
├── next.config.js
└── package.json
```

---

## Server vs Client Components

Default to Server Components. Only use `"use client"` when you need:
- Event listeners (`onClick`, `onChange`)
- State (`useState`, `useReducer`)
- Effects (`useEffect`)
- Browser APIs
- Custom hooks that depend on the above

```tsx
// Server Component (default) — data fetching, no interactivity
// app/runs/[id]/page.tsx
import { DebateTimeline } from "@/components/debate/timeline";
import { LiveEvents } from "@/components/debate/live-events"; // This is a Client Component

export default async function RunPage({ params }: { params: { id: string } }) {
  const run = await fetchRun(params.id);
  return (
    <div className="grid grid-cols-12 gap-4">
      <DebateTimeline run={run} />
      <LiveEvents runId={params.id} />
    </div>
  );
}
```

```tsx
// Client Component — interactive, uses hooks
"use client";

import { useEffect } from "react";
import { useDebateStore } from "@/stores/debate-store";

export function LiveEvents({ runId }: { runId: string }) {
  const events = useDebateStore((s) => s.events);
  const appendEvent = useDebateStore((s) => s.appendEvent);

  useEffect(() => {
    const source = new EventSource(`/api/v1/runs/${runId}/events`);
    source.addEventListener("message", (e) => {
      appendEvent(JSON.parse(e.data));
    });
    return () => source.close();
  }, [runId, appendEvent]);

  return (
    <div className="col-span-8 space-y-2">
      {events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </div>
  );
}
```

---

## State Management: Zustand

```typescript
// stores/debate-store.ts
import { create } from "zustand";
import type { DebateRun, DebateEvent, Claim, AgentStatus } from "@/lib/types";

interface DebateState {
  // Run state
  run: DebateRun | null;
  setRun: (run: DebateRun) => void;

  // Event stream
  events: DebateEvent[];
  appendEvent: (event: DebateEvent) => void;

  // Claims
  claims: Claim[];
  updateClaim: (claimId: string, updates: Partial<Claim>) => void;

  // Agent statuses
  agents: Record<string, AgentStatus>;
  updateAgent: (agentId: string, status: Partial<AgentStatus>) => void;

  // UI
  activeTab: "live" | "agents" | "claims" | "evidence" | "tools" | "transcript" | "report";
  setActiveTab: (tab: string) => void;
  phase: string;
  setPhase: (phase: string) => void;
}

export const useDebateStore = create<DebateState>((set) => ({
  run: null,
  setRun: (run) => set({ run, phase: run.status }),

  events: [],
  appendEvent: (event) =>
    set((state) => ({ events: [...state.events, event] })),

  claims: [],
  updateClaim: (claimId, updates) =>
    set((state) => ({
      claims: state.claims.map((c) =>
        c.id === claimId ? { ...c, ...updates } : c
      ),
    })),

  agents: {},
  updateAgent: (agentId, status) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [agentId]: { ...state.agents[agentId], ...status },
      },
    })),

  activeTab: "live",
  setActiveTab: (tab) => set({ activeTab: tab as DebateState["activeTab"] }),
  phase: "pending",
  setPhase: (phase) => set({ phase }),
}));
```

---

## Server State: TanStack Query

```typescript
// hooks/use-debate-run.ts
import { useQuery } from "@tanstack/react-query";
import type { DebateRun } from "@/lib/types";

async function fetchRun(id: string): Promise<DebateRun> {
  const res = await fetch(`/api/v1/runs/${id}`);
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

export function useDebateRun(id: string) {
  return useQuery({
    queryKey: ["debate-run", id],
    queryFn: () => fetchRun(id),
    refetchInterval: (query) => {
      // Stop polling when run is complete or failed
      const run = query.state.data;
      if (run && (run.status === "complete" || run.status === "failed")) {
        return false;
      }
      return 2000;
    },
  });
}
```

---

## SSE Hook

```typescript
// hooks/use-sse.ts
import { useEffect, useRef } from "react";
import { useDebateStore } from "@/stores/debate-store";
import type { DebateEvent } from "@/lib/types";

export function useSSE(runId: string | null) {
  const sourceRef = useRef<EventSource | null>(null);
  const appendEvent = useDebateStore((s) => s.appendEvent);
  const setPhase = useDebateStore((s) => s.setPhase);

  useEffect(() => {
    if (!runId) return;

    const source = new EventSource(`/api/v1/runs/${runId}/events`);

    source.addEventListener("message", (e) => {
      const event: DebateEvent = JSON.parse(e.data);
      appendEvent(event);

      // Update phase on phase transitions
      if (event.event_type === "run_created") {
        setPhase("pending");
      } else if (event.event_type === "phase_transition") {
        setPhase(event.payload.to_phase);
      }
    });

    source.addEventListener("error", () => {
      // SSE auto-reconnects
    });

    sourceRef.current = source;
    return () => source.close();
  }, [runId, appendEvent, setPhase]);

  return sourceRef;
}
```

---

## shadcn/ui Components

```tsx
// components/debate/input-form.tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DebateInputForm() {
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const [goal, setGoal] = useState("");
  const [maxRounds, setMaxRounds] = useState(3);
  const [preset, setPreset] = useState("technical_decision");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    const res = await fetch("/api/v1/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, context, goal, max_rounds: maxRounds, preset }),
    });
    const run = await res.json();
    // Navigate to run page
    window.location.href = `/runs/${run.id}`;
  };

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>New Debate Run</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">Topic</label>
          <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g., Should we use an event bus or Slack for operational signals?" />
        </div>
        <div>
          <label className="text-sm font-medium">Context</label>
          <Textarea value={context} onChange={(e) => setContext(e.target.value)} placeholder="Background information..." />
        </div>
        <div>
          <label className="text-sm font-medium">Goal</label>
          <Input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="e.g., Produce an architectural recommendation" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Max Rounds</label>
            <Input type="number" min={1} max={5} value={maxRounds} onChange={(e) => setMaxRounds(parseInt(e.target.value))} />
          </div>
          <div>
            <label className="text-sm font-medium">Agent Preset</label>
            <Select value={preset} onValueChange={setPreset}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="technical_decision">Technical Decision</SelectItem>
                <SelectItem value="research_article">Research Article</SelectItem>
                <SelectItem value="product_strategy">Product Strategy</SelectItem>
                <SelectItem value="security_review">Security Review</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={handleSubmit} disabled={loading || !topic || !goal} className="w-full">
          {loading ? "Starting..." : "Start Debate"}
        </Button>
      </CardContent>
    </Card>
  );
}
```

---

## Shared Types

```typescript
// lib/types.ts
export interface DebateRun {
  id: string;
  topic: string;
  context: string;
  user_goal: string;
  status: RunStatus;
  selected_agents: AgentHarness[];
  rounds_count: number;
  created_at: string;
}

export type RunStatus =
  | "pending"
  | "planning"
  | "researching"
  | "arguing"
  | "challenging"
  | "revising"
  | "synthesizing"
  | "auditing"
  | "complete"
  | "failed";

export interface AgentHarness {
  id: string;
  name: string;
  role: string;
  model: string;
  tools_allowed: string[];
  status: AgentStatus;
}

export interface AgentStatus {
  current_task: string;
  claims_made: number;
  claims_challenged: number;
  evidence_gathered: number;
  token_usage: number;
}

export interface DebateEvent {
  id: string;
  run_id: string;
  sequence_number: number;
  event_type: string;
  actor: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Claim {
  id: string;
  text: string;
  agent_id: string;
  status: "proposed" | "challenged" | "supported" | "weakened" | "accepted" | "unresolved";
  evidence_refs: string[];
  challenged_by: string[];
  objections: string[];
  confidence: number | null;
}

export interface EvidenceRef {
  id: string;
  source_type: string;
  title: string;
  quote_or_excerpt: string;
  reliability_score: number;
}

export interface ToolCall {
  agent_id: string;
  tool_name: string;
  params: Record<string, unknown>;
  result: string;
  evidence_extracted: string[];
}
```

---

## Testing

```typescript
// components/debate/__tests__/input-form.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { DebateInputForm } from "../input-form";

describe("DebateInputForm", () => {
  it("renders all form fields", () => {
    render(<DebateInputForm />);
    expect(screen.getByPlaceholderText(/topic/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/context/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/goal/i)).toBeInTheDocument();
  });

  it("disables submit when fields are empty", () => {
    render(<DebateInputForm />);
    expect(screen.getByText("Start Debate")).toBeDisabled();
  });

  it("enables submit when topic and goal are filled", () => {
    render(<DebateInputForm />);
    fireEvent.change(screen.getByPlaceholderText(/topic/i), {
      target: { value: "Test topic" },
    });
    fireEvent.change(screen.getByPlaceholderText(/goal/i), {
      target: { value: "Test goal" },
    });
    expect(screen.getByText("Start Debate")).toBeEnabled();
  });
});
```

---

## Key Gotchas

- Server Components can't use hooks — mark interactive components with `"use client"`
- shadcn/ui components are installed individually via `npx shadcn-ui@latest add`
- Zustand stores must be created outside components (module scope)
- EventSource auto-reconnects on connection loss — handle `error` event for logging only
- TanStack Query `refetchInterval` returns `false` to stop polling
- Tailwind uses `class` not `className` in shadcn components — check generated code
