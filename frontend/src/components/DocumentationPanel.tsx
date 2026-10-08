"use client";

import { useEffect, useState } from "react";
import { BookOpen, Download, FileText } from "lucide-react";
import { api, DocumentationInventory, DocumentationPreview, getErrorMessage } from "@/lib/api";

export default function DocumentationPanel({ repoId }: { repoId: string }) {
  const [inventory, setInventory] = useState<DocumentationInventory | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourcePath, setSourcePath] = useState("");
  const [audience, setAudience] = useState("developers");
  const [preview, setPreview] = useState<DocumentationPreview | null>(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    api.getDocumentation(repoId).then((data) => {
      setInventory(data);
      setSelectedPath(data.documents[0]?.file_path ?? null);
    }).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!inventory || inventory.documents.length === 0) return null;
  const selected = inventory.documents.find((document) => document.file_path === selectedPath) ?? inventory.documents[0];

  const downloadPreview = () => {
    if (!preview) return;
    const safeName = preview.file_path.split("/").pop()?.replace(/[^a-zA-Z0-9._-]/g, "-") || "documentation";
    const blob = new Blob([preview.preview], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeName}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1">
        <BookOpen className="w-4 h-4 text-amber-600" />
        <h2 className="text-sm font-semibold text-slate-700">Documentation</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">README and documentation files discovered in the repository.</p>
      <div className="mb-4 border border-amber-100 bg-amber-50/40 rounded-lg p-3"><p className="text-xs font-semibold text-amber-900">Generate documentation preview</p><p className="text-[11px] text-amber-800 mt-1">Uses one source file, shows citations, and never saves automatically.</p><div className="flex flex-col sm:flex-row gap-2 mt-2"><input aria-label="Source file path" value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} placeholder="backend/app/services/example.py" className="flex-1 px-2 py-1.5 border border-slate-300 rounded text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500" /><input aria-label="Documentation audience" value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Audience" className="w-32 px-2 py-1.5 border border-slate-300 rounded text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500" /><button aria-label="Generate documentation preview" disabled={generating || !sourcePath.trim()} onClick={async () => { setGenerating(true); setError(null); try { setPreview(await api.generateDocumentationPreview(repoId, sourcePath.trim(), audience.trim() || "developers")); } catch (reason) { setError(getErrorMessage(reason)); } finally { setGenerating(false); } }} className="px-3 py-1.5 rounded bg-amber-600 text-white text-xs disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-700">{generating ? "Generating…" : "Preview"}</button></div></div>
      {error && <p role="alert" className="text-xs text-red-600 mb-3">{error}</p>}
      {preview && <div role="status" className="mb-4 border border-sky-100 bg-sky-50/40 rounded-lg p-3"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold text-slate-700">Preview for {preview.file_path}</p><p className="text-[11px] text-slate-500 mt-1">Citation: {preview.citation.file_path} · lines {preview.citation.start_line}–{preview.citation.end_line} · {preview.model}</p></div><button type="button" aria-label="Download documentation preview" onClick={downloadPreview} className="inline-flex items-center gap-1 px-2 py-1 rounded border border-sky-200 text-sky-700 text-[11px] hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"><Download className="w-3 h-3" />Download</button></div><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-700">{preview.preview}</pre></div>}
      <div className="grid lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.4fr)] gap-3">
        <div className="border border-slate-200 rounded-lg overflow-hidden max-h-56 overflow-y-auto">
          {inventory.documents.map((document) => (
            <button type="button" aria-pressed={selected.file_path === document.file_path} key={document.file_path} onClick={() => setSelectedPath(document.file_path)} className={`block w-full text-left px-3 py-2 border-b border-slate-100 last:border-0 ${selected.file_path === document.file_path ? "bg-amber-50 text-amber-800" : "text-slate-600 hover:bg-slate-50"}`}>
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
