"use client";

import { use, useEffect } from "react";
import { useDebateStore } from "@/stores/debate-store";
import { useSSE } from "@/hooks/use-sse";
import { getRun } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Timeline } from "@/components/debate/timeline";
import { AgentPanel } from "@/components/debate/agent-panel";
import { EventStream } from "@/components/debate/event-stream";
import { ClaimsView } from "@/components/debate/claim-card";
import { EvidenceView } from "@/components/debate/evidence-table";
import { ToolCallsLog } from "@/components/debate/tool-calls-log";
import { TranscriptView } from "@/components/debate/transcript-view";
import { ReportView } from "@/components/debate/report-view";
import { Badge } from "@/components/ui/badge";

const PHASE_LABELS: Record<string, string> = {
  pending: "Intake",
  planning: "Agents Selected",
  researching: "Researching",
  arguing: "Positions",
  challenging: "Cross-Exam",
  revising: "Revision",
  synthesizing: "Synthesis",
  auditing: "Audit",
  complete: "Complete",
  failed: "Failed",
};

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const store = useDebateStore();
  const activeTab = store.activeTab;

  // Connect SSE
  useSSE(id);

  // Fetch initial run data
  useEffect(() => {
    getRun(id).then((run) => store.setRun(run)).catch(console.error);
  }, [id]);

  const run = store.run;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="max-w-7xl mx-auto py-4 px-4">
        {/* Header */}
        <div className="mb-4">
          <a href="/" className="text-sm text-zinc-500 hover:underline mb-2 inline-block">
            ← New Debate
          </a>
          {run && (
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold truncate">{run.topic}</h1>
              <Badge variant={store.phase === "failed" ? "destructive" : "default"}>
                {PHASE_LABELS[store.phase] || store.phase}
              </Badge>
            </div>
          )}
          {run && (
            <p className="text-sm text-zinc-500 mt-1">Goal: {run.user_goal}</p>
          )}
        </div>

        {/* Main grid: Timeline + Content */}
        <div className="grid grid-cols-12 gap-4">
          {/* Left sidebar */}
          <div className="col-span-3 space-y-4">
            <Timeline />
            <AgentPanel />
          </div>

          {/* Main content */}
          <div className="col-span-9">
            <Tabs value={activeTab} onValueChange={store.setActiveTab}>
              <TabsList className="w-full justify-start overflow-x-auto">
                <TabsTrigger value="live">Live</TabsTrigger>
                <TabsTrigger value="agents">Agents</TabsTrigger>
                <TabsTrigger value="claims">Claims</TabsTrigger>
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
                <TabsTrigger value="tools">Tool Calls</TabsTrigger>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
                <TabsTrigger value="report">Report</TabsTrigger>
              </TabsList>
              <TabsContent value="live" className="mt-4">
                <EventStream />
              </TabsContent>
              <TabsContent value="agents" className="mt-4">
                <AgentPanel />
              </TabsContent>
              <TabsContent value="claims" className="mt-4">
                <ClaimsView />
              </TabsContent>
              <TabsContent value="evidence" className="mt-4">
                <EvidenceView />
              </TabsContent>
              <TabsContent value="tools" className="mt-4">
                <ToolCallsLog />
              </TabsContent>
              <TabsContent value="transcript" className="mt-4">
                <TranscriptView />
              </TabsContent>
              <TabsContent value="report" className="mt-4">
                <ReportView />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}
