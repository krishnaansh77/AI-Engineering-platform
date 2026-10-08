"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, FlaskConical, TriangleAlert } from "lucide-react";
import { api, getErrorMessage, TestIntelligence } from "@/lib/api";

export default function TestIntelligencePanel({ repoId }: { repoId: string }) {
  const [summary, setSummary] = useState<TestIntelligence | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTestIntelligence(repoId).then(setSummary).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  const testedPercent = useMemo(() => {
    if (!summary || summary.source_file_count === 0) return 0;
    return Math.round((summary.tested_file_count / summary.source_file_count) * 100);
  }, [summary]);

  if (error) return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5 text-sm text-slate-500">Test intelligence unavailable: {error}</div>;
  if (!summary) return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5 animate-pulse h-48" />;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-emerald-600" />
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Test Intelligence</h2>
            <p className="text-xs text-slate-500 mt-1">Heuristic links between tests and source files, not runtime coverage.</p>
          </div>
        </div>
        <span className="text-lg font-bold text-slate-800">{testedPercent}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden mb-3">
        <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${testedPercent}%` }} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs mb-4">
        <Metric label="Test files" value={summary.test_file_count} />
        <Metric label="Linked source" value={summary.tested_file_count} />
        <Metric label="Unlinked source" value={summary.untested_file_count} />
      </div>
      {summary.untested_files.length > 0 && (
        <div className="border border-amber-100 bg-amber-50/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 mb-2"><TriangleAlert className="w-3.5 h-3.5" />Candidate areas for tests</div>
          <div className="grid sm:grid-cols-2 gap-x-4 gap-y-1">
            {summary.untested_files.slice(0, 8).map((file) => <p key={file} className="text-[11px] text-amber-900 truncate" title={file}>{file}</p>)}
          </div>
        </div>
      )}
      {summary.untested_files.length === 0 && <p className="text-xs text-emerald-700 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" />Every indexed source file has a detected test relationship.</p>}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2"><p className="font-semibold text-slate-800">{value}</p><p className="text-[11px] text-slate-500">{label}</p></div>;
}
