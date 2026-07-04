"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createRun } from "@/lib/api";

const PRESETS = [
  { value: "technical_decision", label: "Technical Decision" },
  { value: "research_article", label: "Research Article" },
  { value: "product_strategy", label: "Product Strategy" },
  { value: "security_review", label: "Security Review" },
];

export function DebateInputForm() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const [goal, setGoal] = useState("");
  const [maxRounds, setMaxRounds] = useState(3);
  const [preset, setPreset] = useState("technical_decision");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!topic || !goal) return;
    setLoading(true);
    try {
      const run = await createRun({
        topic,
        context,
        goal,
        max_rounds: maxRounds,
        preset,
      });
      router.push(`/runs/${run.id}`);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="text-2xl">New Debate Run</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Topic</label>
          <Input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Should we use an event bus or Slack for operational signals?"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Context (optional)</label>
          <Textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Background information..."
            rows={3}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Goal</label>
          <Input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g., Produce an architectural recommendation"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Max Rounds</label>
            <Input
              type="number"
              min={1}
              max={5}
              value={maxRounds}
              onChange={(e) => setMaxRounds(parseInt(e.target.value) || 3)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Agent Preset</label>
            <Select value={preset} onValueChange={(v) => setPreset(v || "technical_decision")}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRESETS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button
          onClick={handleSubmit}
          disabled={loading || !topic || !goal}
          className="w-full"
        >
          {loading ? "Starting debate..." : "Start Debate"}
        </Button>
      </CardContent>
    </Card>
  );
}
