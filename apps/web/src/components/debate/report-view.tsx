"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Badge } from "@/components/ui/badge";
import type { ReportData } from "@/lib/types";

export function ReportView() {
  const report = useDebateStore((s) => s.report);

  if (!report) {
    return <p className="text-sm text-zinc-500 py-8 text-center">Report not yet available.</p>;
  }

  return (
    <div className="space-y-6 max-h-[600px] overflow-y-auto">
      <section>
        <h2 className="text-lg font-bold">Executive Synthesis</h2>
        <p className="text-sm text-zinc-700 dark:text-zinc-300 mt-1">
          {report.executive_synthesis}
        </p>
      </section>

      <section>
        <h3 className="text-sm font-semibold mb-2">Agents</h3>
        <div className="flex flex-wrap gap-2">
          {report.agents.map((a) => (
            <Badge key={a.id} variant="outline">
              {a.name}
            </Badge>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold mb-2">Final Recommendation</h3>
        <p className="text-sm">{report.final_recommendation}</p>
      </section>

      {report.agreements.length > 0 && (
        <SectionList title="Agreements" items={report.agreements} />
      )}

      {report.disagreements.length > 0 && (
        <SectionList title="Disagreements" items={report.disagreements} />
      )}

      {report.what_changed.length > 0 && (
        <SectionList title="What Changed" items={report.what_changed} />
      )}

      {report.trade_offs.length > 0 && (
        <SectionList title="Trade-offs" items={report.trade_offs} />
      )}

      {report.risks.length > 0 && (
        <SectionList title="Risks" items={report.risks} />
      )}

      {report.open_questions.length > 0 && (
        <SectionList title="Open Questions" items={report.open_questions} />
      )}

      {report.implementation_path && (
        <section>
          <h3 className="text-sm font-semibold mb-1">Implementation Path</h3>
          <p className="text-sm">{report.implementation_path}</p>
        </section>
      )}
    </div>
  );
}

function SectionList({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h3 className="text-sm font-semibold mb-1">{title}</h3>
      <ul className="list-disc pl-5 text-sm space-y-1">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
