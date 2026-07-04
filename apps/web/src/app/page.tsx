import { DebateInputForm } from "@/components/debate/input-form";

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="max-w-4xl mx-auto py-16 px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight">DebateLab</h1>
          <p className="text-zinc-500 mt-2">
            Traceable multi-agent deliberation for research and technical decisions
          </p>
        </div>
        <DebateInputForm />
      </div>
    </div>
  );
}
