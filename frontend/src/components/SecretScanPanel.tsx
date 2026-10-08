"use client";

import { useState } from "react";
import { ShieldCheck, Loader2 } from "lucide-react";
import { api, SecretScanResult, getErrorMessage } from "@/lib/api";

export default function SecretScanPanel({ repoId }: { repoId: string }) {
  const [result, setResult] = useState<SecretScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scan = async () => {
    setLoading(true); setError(null);
    try { setResult(await api.scanSecrets(repoId)); } catch (reason) { setError(getErrorMessage(reason)); } finally { setLoading(false); }
  };
  return <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5"><div className="flex items-center gap-2 mb-1"><ShieldCheck className="w-4 h-4 text-emerald-600" /><h2 className="text-sm font-semibold text-slate-700">Secret Pattern Scan</h2></div><p className="text-xs text-slate-500 mb-3">Optional heuristic scan. Values are never returned and findings are not proof of a real secret.</p><button aria-label="Run secret pattern scan" onClick={scan} disabled={loading} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 text-white text-xs font-medium disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700">{loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}{loading ? "Scanning…" : "Run scan"}</button>{error && <p role="alert" className="text-xs text-red-600 mt-3">{error}</p>}{result && <div role="status" className="mt-3"><p className="text-xs text-slate-600">Scanned {result.scanned_files} files · {result.finding_count} possible finding{result.finding_count === 1 ? "" : "s"}</p>{result.findings.map((finding) => <p key={`${finding.file_path}-${finding.line}-${finding.pattern}`} className="text-[11px] text-amber-800 mt-1">{finding.file_path}:L{finding.line} · {finding.pattern} · {finding.confidence}</p>)}</div>}</section>;
}
