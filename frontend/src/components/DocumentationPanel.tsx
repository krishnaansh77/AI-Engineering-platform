"use client";

import { useEffect, useState } from "react";
import { BookOpen, FileText } from "lucide-react";
import { api, DocumentationInventory, getErrorMessage } from "@/lib/api";

export default function DocumentationPanel({ repoId }: { repoId: string }) {
  const [inventory, setInventory] = useState<DocumentationInventory | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDocumentation(repoId).then((data) => {
      setInventory(data);
      setSelectedPath(data.documents[0]?.file_path ?? null);
    }).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!inventory || inventory.documents.length === 0) return null;
  const selected = inventory.documents.find((document) => document.file_path === selectedPath) ?? inventory.documents[0];

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <BookOpen className="w-4 h-4 text-amber-600" />
        <h2 className="text-sm font-semibold text-slate-700">Documentation</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">README and documentation files discovered in the repository.</p>
      <div className="grid lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.4fr)] gap-3">
        <div className="border border-slate-200 rounded-lg overflow-hidden max-h-56 overflow-y-auto">
          {inventory.documents.map((document) => (
            <button key={document.file_path} onClick={() => setSelectedPath(document.file_path)} className={`block w-full text-left px-3 py-2 border-b border-slate-100 last:border-0 ${selected.file_path === document.file_path ? "bg-amber-50 text-amber-800" : "text-slate-600 hover:bg-slate-50"}`}>
              <span className="flex items-center gap-1.5 text-xs font-medium truncate"><FileText className="w-3.5 h-3.5 flex-shrink-0" />{document.file_path}</span>
              <span className="block text-[10px] text-slate-400 mt-1">{Math.ceil(document.size_bytes / 1024)} KB</span>
            </button>
          ))}
        </div>
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <p className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600">{selected.title}</p>
          <pre className="max-h-56 overflow-auto p-3 text-[11px] leading-5 text-slate-700 whitespace-pre-wrap">{selected.content}</pre>
        </div>
      </div>
    </section>
  );
}
