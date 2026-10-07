"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, GitBranch, Search } from "lucide-react";
import { api, DependencyGraph, getErrorMessage } from "@/lib/api";

interface DependencyGraphPanelProps {
  repoId: string;
}

export default function DependencyGraphPanel({ repoId }: DependencyGraphPanelProps) {
  const [graph, setGraph] = useState<DependencyGraph | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.getFileDependencyGraph(repoId)
      .then((data) => {
        if (!active) return;
        setGraph(data);
        setSelectedFile(data.nodes[0]?.id ?? null);
      })
      .catch((reason) => active && setError(getErrorMessage(reason)))
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [repoId]);

  const filteredNodes = useMemo(() => {
    if (!graph) return [];
    const query = search.trim().toLowerCase();
    return graph.nodes.filter((node) => !query || node.file_path.toLowerCase().includes(query));
  }, [graph, search]);

  const selected = graph?.nodes.find((node) => node.id === selectedFile);
  const imports = graph?.edges.filter((edge) => edge.source === selectedFile) ?? [];
  const importedBy = graph?.edges.filter((edge) => edge.target === selectedFile) ?? [];

  if (loading) {
    return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 animate-pulse h-72" />;
  }

  if (error) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
        <p className="text-sm text-slate-500">Dependency graph unavailable: {error}</p>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) return null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-sky-600" />
            <h2 className="text-sm font-semibold text-slate-700">File Dependency Graph</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">Browse imports and references discovered during indexing.</p>
        </div>
        <div className="text-right text-xs text-slate-500 whitespace-nowrap">
          <span className="font-semibold text-slate-700">{graph.node_count}</span> files · {graph.edge_count} links
        </div>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4">
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <label className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 text-slate-400">
            <Search className="w-4 h-4" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search files..."
              className="w-full text-sm text-slate-700 outline-none placeholder:text-slate-400"
            />
          </label>
          <div className="max-h-64 overflow-y-auto">
            {filteredNodes.map((node) => (
              <button
                key={node.id}
                onClick={() => setSelectedFile(node.id)}
                className={`block w-full text-left px-3 py-2 text-xs truncate border-b border-slate-100 last:border-0 ${
                  node.id === selectedFile ? "bg-sky-50 text-sky-700 font-medium" : "text-slate-600 hover:bg-slate-50"
                }`}
                title={node.file_path}
              >
                {node.file_path}
              </button>
            ))}
            {filteredNodes.length === 0 && <p className="p-3 text-xs text-slate-500">No matching files.</p>}
          </div>
        </div>

        <div className="min-w-0">
          <p className="text-xs font-semibold text-slate-700 truncate mb-3" title={selected?.file_path}>
            {selected?.file_path ?? "Select a file"}
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <DependencyList icon={<ArrowDown className="w-3.5 h-3.5" />} title="Imports" edges={imports} direction="target" graph={graph} />
            <DependencyList icon={<ArrowUp className="w-3.5 h-3.5" />} title="Imported by" edges={importedBy} direction="source" graph={graph} />
          </div>
        </div>
      </div>
    </section>
  );
}

function DependencyList({
  icon,
  title,
  edges,
  direction,
  graph,
}: {
  icon: React.ReactNode;
  title: string;
  edges: DependencyGraph["edges"];
  direction: "source" | "target";
  graph: DependencyGraph;
}) {
  return (
    <div className="border border-slate-200 rounded-lg p-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 mb-2">
        {icon}{title}<span className="text-slate-400">({edges.length})</span>
      </div>
      <div className="space-y-2 max-h-40 overflow-y-auto">
        {edges.map((edge) => {
          const nodeId = direction === "target" ? edge.target : edge.source;
          const file = graph.nodes.find((node) => node.id === nodeId)?.file_path ?? nodeId;
          return <div key={`${edge.source}-${edge.target}-${edge.import}`} className="text-xs" title={edge.import}>
            <p className="text-slate-700 truncate">{file}</p>
            <p className="text-slate-400 truncate">{edge.import}</p>
          </div>;
        })}
        {edges.length === 0 && <p className="text-xs text-slate-400">None detected.</p>}
      </div>
    </div>
  );
}
