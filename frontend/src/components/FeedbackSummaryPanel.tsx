"use client";

import { useEffect, useState } from "react";
import { BarChart3, MessageCircle, ThumbsUp } from "lucide-react";
import { api, FeedbackSummary, getErrorMessage } from "@/lib/api";

export default function FeedbackSummaryPanel({ repoId }: { repoId: string }) {
  const [summary, setSummary] = useState<FeedbackSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getFeedbackSummary(repoId).then(setSummary).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (error || !summary || summary.total === 0) return null;
  const helpfulPercent = Math.round(summary.helpful_rate * 100);

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <BarChart3 className="w-4 h-4 text-sky-600" />
        <h2 className="text-sm font-semibold text-slate-700">Answer Quality Signals</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">Based on {summary.total} explicit answer rating{summary.total === 1 ? "" : "s"}.</p>
      <div className="grid grid-cols-3 gap-2">
        <Metric icon={<ThumbsUp className="w-3.5 h-3.5" />} label="Helpful rate" value={`${helpfulPercent}%`} />
        <Metric icon={<MessageCircle className="w-3.5 h-3.5" />} label="Helpful" value={summary.helpful} />
        <Metric icon={<BarChart3 className="w-3.5 h-3.5" />} label="Avg. sources" value={summary.average_retrieval_count} />
      </div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2"><div className="flex items-center gap-1 text-slate-500">{icon}<span className="text-[11px]">{label}</span></div><p className="text-base font-semibold text-slate-800 mt-1">{value}</p></div>;
}
