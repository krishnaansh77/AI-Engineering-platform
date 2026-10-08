"use client";

import { useEffect, useState } from "react";
import { Compass, Link2 } from "lucide-react";
import { api, getErrorMessage, RepositoryTour } from "@/lib/api";

export default function RepositoryTourPanel({ repoId }: { repoId: string }) {
  const [tour, setTour] = useState<RepositoryTour | null>(null);
  const [, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRepositoryTour(repoId).then(setTour).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!tour) return null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <Compass className="w-4 h-4 text-sky-600" />
        <h2 className="text-sm font-semibold text-slate-700">Repository Tour</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">Start with the files most connected to the rest of this codebase.</p>
      <div className="grid sm:grid-cols-2 gap-3">
        {tour.key_files.map((file, index) => (
          <div key={file.file_path} className="border border-slate-100 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <span className="text-xs text-slate-400 font-mono">{String(index + 1).padStart(2, "0")}</span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-slate-700 truncate" title={file.file_path}>{file.file_path}</p>
                <p className="text-[11px] text-slate-400 mt-1 capitalize">{file.layer} · {file.connections} connections</p>
                {file.symbols.length > 0 && <p className="text-[11px] text-sky-700 truncate mt-2" title={file.symbols.join(", ")}><Link2 className="inline w-3 h-3 mr-1" />{file.symbols.join(", ")}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-slate-400 mt-4">{tour.file_count} files · {tour.relationship_count} discovered relationships</p>
    </section>
  );
}
