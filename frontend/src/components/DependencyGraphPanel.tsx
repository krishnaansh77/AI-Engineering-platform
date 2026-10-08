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
  const [fileFilter, setFileFilter] = useState<"all" | "connected" | "isolated">("all");
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

  const connectionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    graph?.nodes.forEach((node) => counts.set(node.id, 0));
    graph?.edges.forEach((edge) => {
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
    });
    return counts;
  }, [graph]);

  const connectedFileCount = useMemo(
    () => Array.from(connectionCounts.values()).filter((count) => count > 0).length,
    [connectionCounts]
  );

  const filteredNodes = useMemo(() => {
    if (!graph) return [];
    const query = search.trim().toLowerCase();
    return graph.nodes
      .filter((node) => !query || node.file_path.toLowerCase().includes(query))
      .filter((node) => fileFilter === "all" || (fileFilter === "connected" ? (connectionCounts.get(node.id) ?? 0) > 0 : (connectionCounts.get(node.id) ?? 0) === 0))
      .sort((left, right) => (connectionCounts.get(right.id) ?? 0) - (connectionCounts.get(left.id) ?? 0));
  }, [connectionCounts, fileFilter, graph, search]);

  const selected = graph?.nodes.find((node) => node.id === selectedFile);
  const imports = graph?.edges.filter((edge) => edge.source === selectedFile) ?? [];
  const importedBy = graph?.edges.filter((edge) => edge.target === selectedFile) ?? [];
  const impact = useMemo(() => {
    if (!graph || !selectedFile) return { dependencies: new Set<string>(), dependents: new Set<string>() };
    const walk = (direction: "dependencies" | "dependents") => {
      const visited = new Set<string>();
      let frontier = new Set([selectedFile]);
      for (let depth = 0; depth < 3; depth += 1) {
        const next = new Set<string>();
        graph.edges.forEach((edge) => {
          const matches = direction === "dependencies" ? frontier.has(edge.source) : frontier.has(edge.target);
          const neighbor = direction === "dependencies" ? edge.target : edge.source;
          if (matches && neighbor !== selectedFile && !visited.has(neighbor)) next.add(neighbor);
        });
        next.forEach((node) => visited.add(node));
        frontier = next;
      }
      return visited;
    };
    return { dependencies: walk("dependencies"), dependents: walk("dependents") };
  }, [graph, selectedFile]);

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

      <div className="grid grid-cols-3 gap-2 mb-4">
        <GraphMetric label="Connected" value={connectedFileCount} />
        <GraphMetric label="Isolated" value={graph.node_count - connectedFileCount} />
        <GraphMetric label="Avg links/file" value={graph.node_count ? (graph.edge_count * 2 / graph.node_count).toFixed(1) : "0"} />
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4">
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search files..."
              className="w-full text-sm text-slate-700 outline-none placeholder:text-slate-400"
            />
          </div>
          <div className="flex gap-1 p-2 border-b border-slate-100 bg-slate-50">
            {(["all", "connected", "isolated"] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setFileFilter(filter)}
                className={`px-2 py-1 rounded text-[11px] capitalize ${fileFilter === filter ? "bg-white text-sky-700 shadow-sm font-medium" : "text-slate-500 hover:text-slate-700"}`}
              >
                {filter}
              </button>
            ))}
          </div>
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
                <span className="block truncate">{node.file_path}</span>
                <span className="block text-[10px] text-slate-400 mt-0.5">{connectionCounts.get(node.id) ?? 0} connections</span>
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
          <div className="border border-slate-200 rounded-lg p-3 mt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-600">Symbols in file</p>
              <span className="text-[11px] text-slate-400">{selected?.symbols.length ?? 0}</span>
            </div>
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {selected?.symbols.map((symbol) => (
                <div key={`${symbol.name}-${symbol.start_line}`} className="flex items-center justify-between gap-2 text-xs">
                  <span className="text-slate-700 truncate" title={symbol.parent ? `${symbol.parent}.${symbol.name}` : symbol.name}>
                    {symbol.parent ? `${symbol.parent}.${symbol.name}` : symbol.name}
                  </span>
                  <span className="text-slate-400 whitespace-nowrap">{symbol.type} · L{symbol.start_line}</span>
                </div>
              ))}
              {selected?.symbols.length === 0 && <p className="text-xs text-slate-400">No named symbols detected.</p>}
            </div>
          </div>
          <div className="border border-sky-100 bg-sky-50/50 rounded-lg p-3 mt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-600">Change impact · 3 hops</p>
              <span className="text-[11px] text-slate-400">{impact.dependencies.size + impact.dependents.size} files</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><p className="font-semibold text-sky-700">{impact.dependencies.size}</p><p className="text-slate-500">dependencies</p></div>
              <div><p className="font-semibold text-sky-700">{impact.dependents.size}</p><p className="text-slate-500">possible dependents</p></div>
            </div>
            <p className="text-[11px] text-slate-400 mt-2">Includes direct and transitive file links.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function GraphMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
      <p className="text-base font-semibold text-slate-800">{value}</p>
      <p className="text-[11px] text-slate-500">{label}</p>
    </div>
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
