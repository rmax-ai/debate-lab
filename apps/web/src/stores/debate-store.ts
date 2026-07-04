import { create } from "zustand";
import type { DebateRun, DebateEvent, ClaimData, EvidenceRefData, ToolCallData, AgentStatus, ReportData, RunStatus } from "@/lib/types";

interface DebateState {
  run: DebateRun | null;
  events: DebateEvent[];
  claims: Record<string, ClaimData>;
  evidence: Record<string, EvidenceRefData>;
  toolCalls: ToolCallData[];
  agents: Record<string, AgentStatus>;
  report: ReportData | null;
  activeTab: string;
  phase: RunStatus;

  setRun: (run: DebateRun) => void;
  appendEvent: (event: DebateEvent) => void;
  setActiveTab: (tab: string) => void;
  setPhase: (phase: RunStatus) => void;
  reset: () => void;
}

function processEvent(state: DebateState, event: DebateEvent): void {
  const { event_type, actor, payload } = event;

  switch (event_type) {
    case "agents_selected": {
      const agents = (payload.agents as Array<Record<string, unknown>>) || [];
      for (const a of agents) {
        state.agents[a.id as string] = {
          claims_made: 0,
          claims_challenged: 0,
          evidence_gathered: 0,
        };
      }
      break;
    }
    case "phase_transition": {
      const toPhase = payload.to_phase as RunStatus;
      if (toPhase) state.phase = toPhase;
      break;
    }
    case "claim_extracted": {
      const claim = payload.claim as ClaimData | undefined;
      if (claim) {
        state.claims[claim.id] = claim;
        if (actor && state.agents[actor]) {
          state.agents[actor].claims_made++;
        }
      }
      break;
    }
    case "claim_challenged": {
      const claimId = payload.claim_id as string;
      if (claimId && state.claims[claimId]) {
        state.claims[claimId].status = "challenged";
        if (actor && state.agents[actor]) {
          state.agents[actor].claims_challenged++;
        }
      }
      break;
    }
    case "evidence_extracted": {
      const ref = payload.evidence_ref as EvidenceRefData | undefined;
      if (ref) {
        state.evidence[ref.id] = ref;
        if (ref.retrieved_by && state.agents[ref.retrieved_by]) {
          state.agents[ref.retrieved_by].evidence_gathered++;
        }
      }
      break;
    }
    case "tool_call_requested":
    case "tool_call_completed": {
      state.toolCalls.push({
        type: event_type,
        agent_id: actor || undefined,
        ...(payload as Record<string, unknown>),
      } as ToolCallData);
      break;
    }
    case "final_report": {
      state.report = (payload.report || payload) as ReportData;
      break;
    }
    case "run_completed": {
      state.phase = "complete";
      break;
    }
    case "run_failed": {
      state.phase = "failed";
      break;
    }
  }
}

export const useDebateStore = create<DebateState>((set) => ({
  run: null,
  events: [],
  claims: {},
  evidence: {},
  toolCalls: [],
  agents: {},
  report: null,
  activeTab: "live",
  phase: "pending",

  setRun: (run) => set({ run, phase: run.status as RunStatus }),

  appendEvent: (event) =>
    set((state) => {
      const next = { ...state, events: [...state.events, event] };
      processEvent(next, event);
      return next;
    }),

  setActiveTab: (tab) => set({ activeTab: tab }),
  setPhase: (phase) => set({ phase }),
  reset: () =>
    set({
      run: null,
      events: [],
      claims: {},
      evidence: {},
      toolCalls: [],
      agents: {},
      report: null,
      activeTab: "live",
      phase: "pending",
    }),
}));
