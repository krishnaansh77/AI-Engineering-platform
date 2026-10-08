"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Boxes, FileCode2 } from "lucide-react";
import { api, ArchitectureSummary, getErrorMessage } from "@/lib/api";

const layerColors: Record<string, string> = {
  frontend: "bg-sky-50 border-sky-200 text-sky-700",
  backend: "bg-violet-50 border-violet-200 text-violet-700",
  tests: "bg-emerald-50 border-emerald-200 text-emerald-700",
  documentation: "bg-amber-50 border-amber-200 text-amber-700",
  configuration: "bg-slate-50 border-slate-200 text-slate-700",
  other: "bg-slate-50 border-slate-200 text-slate-600",
};

export default function ArchitecturePanel({ repoId }: { repoId: string }) {
  const [summary, setSummary] = useState<ArchitectureSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getArchitecture(repoId).then(setSummary).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (error) return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5 text-sm text-slate-500">Architecture unavailable: {error}</div>;
  if (!summary) return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5 animate-pulse h-48" />;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <Boxes className="w-4 h-4 text-sky-600" />
        <h2 className="text-sm font-semibold text-slate-700">Architecture Explorer</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">Inferred layers from repository paths and import relationships.</p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {summary.layers.map((layer) => (
          <div key={layer.name} className={`rounded-lg border p-3 ${layerColors[layer.name] ?? layerColors.other}`}>
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-semibold capitalize">{layer.name}</p>
              <span className="text-lg font-bold">{layer.file_count}</span>
            </div>
            <p className="text-[11px] opacity-75">indexed files</p>
            <div className="mt-2 space-y-1">
              {layer.files.slice(0, 3).map((file) => <p key={file} className="text-[10px] truncate" title={file}><FileCode2 className="inline w-3 h-3 mr-1" />{file}</p>)}
            </div>
          </div>
        ))}
      </div>
      {summary.cross_layer_links.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-100">
          <p className="text-xs font-semibold text-slate-600 mb-2">Cross-layer relationships</p>
          <div className="flex flex-wrap gap-2">
            {summary.cross_layer_links.map((link) => (
              <span key={`${link.source}-${link.target}`} className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] text-slate-600">
                <span className="capitalize">{link.source}</span><ArrowRight className="w-3 h-3" /><span className="capitalize">{link.target}</span><span className="text-slate-400">({link.edge_count})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
