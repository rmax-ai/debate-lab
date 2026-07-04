export interface DebateRun {
  id: string;
  topic: string;
  context: string;
  user_goal: string;
  constraints: string;
  max_rounds: number;
  preset: string;
  status: RunStatus;
  rounds_count: number;
  selected_agents?: AgentConfig[];
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

export interface AgentConfig {
  id: string;
  name: string;
  role: string;
  model: string;
  tools_allowed: string[];
  max_tool_calls: number;
  max_claims: number;
}

export interface AgentStatus {
  current_task?: string;
  claims_made: number;
  claims_challenged: number;
  evidence_gathered: number;
}

export interface DebateEvent {
  id?: string;
  event_type: string;
  actor: string | null;
  payload: Record<string, unknown>;
  sequence_number?: number;
  created_at?: string;
}

export interface ClaimData {
  id: string;
  text: string;
  agent_id: string;
  status: "proposed" | "challenged" | "supported" | "weakened" | "accepted" | "unresolved";
  evidence_refs: string[];
  challenged_by: string[];
  objections: string[];
  confidence: number | null;
}

export interface EvidenceRefData {
  id: string;
  source_type: string;
  title: string;
  quote_or_excerpt: string;
  reliability_score: number;
  url?: string;
  retrieved_by: string;
}

export interface ToolCallData {
  type: string;
  agent_id?: string;
  tool_name?: string;
  params?: Record<string, unknown>;
  result_summary?: string;
  evidence_extracted?: string[];
}

export interface ReportData {
  executive_synthesis: string;
  topic: string;
  goal: string;
  preset: string;
  agents: { id: string; name: string; role: string }[];
  strongest_claims: ClaimData[];
  challenged_claims: ClaimData[];
  agreements: string[];
  disagreements: string[];
  what_changed: string[];
  final_recommendation: string;
  trade_offs: string[];
  risks: string[];
  open_questions: string[];
  implementation_path: string;
  claim_stats?: { total: number; by_status: Record<string, number> };
}
