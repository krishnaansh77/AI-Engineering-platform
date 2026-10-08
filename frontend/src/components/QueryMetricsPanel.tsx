"use client";

import { useEffect, useState } from "react";
import { Gauge, Timer, Zap } from "lucide-react";
import { api, getErrorMessage, QueryMetrics } from "@/lib/api";

export default function QueryMetricsPanel({ repoId }: { repoId: string }) {
  const [metrics, setMetrics] = useState<QueryMetrics | null>(null);
  const [, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getQueryMetrics(repoId).then(setMetrics).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!metrics || metrics.total_queries === 0) return null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <Gauge className="w-4 h-4 text-violet-600" />
        <h2 className="text-sm font-semibold text-slate-700">Query Performance</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">Average timings from {metrics.total_queries} successful question{metrics.total_queries === 1 ? "" : "s"}.</p>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        <Metric icon={<Timer className="w-3.5 h-3.5" />} label="Total" value={`${Math.round(metrics.average_total_latency_ms)} ms`} />
        <Metric icon={<Zap className="w-3.5 h-3.5" />} label="Retrieval" value={`${Math.round(metrics.average_retrieval_latency_ms)} ms`} />
        <Metric icon={<Gauge className="w-3.5 h-3.5" />} label="LLM" value={`${Math.round(metrics.average_llm_latency_ms)} ms`} />
        <Metric icon={<Gauge className="w-3.5 h-3.5" />} label="Prompt tokens" value={metrics.prompt_tokens.toLocaleString()} />
        <Metric icon={<Gauge className="w-3.5 h-3.5" />} label="Output tokens" value={metrics.completion_tokens.toLocaleString()} />
      </div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2"><div className="flex items-center gap-1 text-slate-500">{icon}<span className="text-[11px]">{label}</span></div><p className="text-base font-semibold text-slate-800 mt-1">{value}</p></div>;
}
