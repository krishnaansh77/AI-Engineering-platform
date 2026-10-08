import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Repository {
  id: string;
  name: string;
  full_name: string;
  github_url: string;
  description: string | null;
  default_branch: string;
  status: "pending" | "indexing" | "ready" | "error";
  error_message: string | null;
  languages: string[];
  frameworks: string[];
  file_count: number;
  chunk_count: number;
  last_indexed_at: string | null;
  created_at: string;
}

export interface RepoStats {
  file_count: number;
  chunk_count: number;
  languages: string[];
  frameworks: string[];
  last_indexed_at: string | null;
}

export interface Citation {
  file_path: string;
  symbol_name: string | null;
  chunk_type: string;
  start_line: number;
  end_line: number;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  model: string;
  retrieval_count: number;
  cached?: boolean;
}

export type FeedbackRating = "helpful" | "not_helpful";

export interface GitCommit {
  sha: string;
  short_sha: string;
  message: string;
  author: string;
  committed_at: string;
  files: string[];
  files_changed: number;
  insertions: number;
  deletions: number;
  impact_count?: number;
}

export interface GitHistory {
  commits: GitCommit[];
  count: number;
}

export interface ArchitectureLayer {
  name: string;
  file_count: number;
  files: string[];
}

export interface ArchitectureLink {
  source: string;
  target: string;
  edge_count: number;
}

export interface ArchitectureSummary {
  layers: ArchitectureLayer[];
  cross_layer_links: ArchitectureLink[];
}

export interface TestIntelligence {
  test_file_count: number;
  source_file_count: number;
  tested_file_count: number;
  untested_file_count: number;
  tested_files: string[];
  untested_files: string[];
}

export interface FeedbackSummary {
  total: number;
  helpful: number;
  not_helpful: number;
  helpful_rate: number;
  average_retrieval_count: number;
}

export interface QueryMetrics {
  total_queries: number;
  average_retrieval_latency_ms: number;
  average_llm_latency_ms: number;
  average_total_latency_ms: number;
  average_retrieval_count: number;
}

export interface SourceFilePreview {
  file_path: string;
  language: string;
  content: string;
}

export interface SearchResult {
  file_path: string;
  symbol_name: string | null;
  chunk_type: string;
  start_line: number;
  end_line: number;
  snippet: string;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
}

export interface RepositoryTourFile {
  file_path: string;
  connections: number;
  symbols: string[];
  layer: string;
}

export interface RepositoryTour {
  file_count: number;
  relationship_count: number;
  key_files: RepositoryTourFile[];
}

export interface DocumentationFile {
  file_path: string;
  title: string;
  size_bytes: number;
  content: string;
}

export interface DocumentationInventory {
  documents: DocumentationFile[];
}

export interface DocumentationGap {
  file_path: string;
  undocumented_symbols: number;
}

export interface DocumentationQuality {
  symbol_count: number;
  documented_symbol_count: number;
  undocumented_symbol_count: number;
  coverage: number;
  gaps: DocumentationGap[];
}

export interface LatestChangeAnalysis {
  sha: string;
  short_sha: string;
  message: string;
  author: string;
  changed_files: string[];
  source_files: string[];
  test_files: string[];
  documentation_files: string[];
  insertions: number;
  deletions: number;
  recommendations: string[];
}

export interface DebtSignal {
  file_path: string;
  signal: string;
  value: number;
  unit: string;
}

export interface TechnicalDebtSummary {
  signals: DebtSignal[];
  files_analyzed: number;
  chunks_analyzed: number;
}

export interface RepositoryIssue {
  number: number;
  title: string;
  body: string;
  html_url: string;
  labels: string[];
  created_at: string;
}

export interface IssueAnalysis {
  issue: RepositoryIssue;
  relevant_files: Array<{ file_path: string; symbol_name: string | null; start_line: number; end_line: number; score: number }>;
}

export interface EvaluationRun {
  summary: { recall_at_k: number; mrr: number; case_count: number };
  cases: Array<{ question: string; expected_files: string[]; retrieved_files: string[]; recall: number; reciprocal_rank: number; matched_files: string[] }>;
}

export interface DependencyGraphNode {
  id: string;
  file_path: string;
  symbols: DependencyGraphSymbol[];
}

export interface DependencyGraphSymbol {
  name: string;
  type: string;
  parent: string | null;
  start_line: number;
  end_line: number;
}

export interface DependencyGraphEdge {
  source: string;
  target: string;
  import: string;
}

export interface DependencyGraph {
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  timestamp: Date;
  isLoading?: boolean;
  question?: string;
  model?: string;
  retrievalCount?: number;
  feedback?: FeedbackRating;
  cached?: boolean;
}

export interface ConnectRepoRequest {
  github_url: string;
  name?: string;
}

// ─── API Client ───────────────────────────────────────────────────────────────

export const api = {
  // Repositories
  connectRepo: async (payload: ConnectRepoRequest): Promise<Repository> => {
    const { data } = await client.post<Repository>("/repos/connect", payload);
    return data;
  },

  listRepos: async (): Promise<Repository[]> => {
    const { data } = await client.get<Repository[]>("/repos");
    return data;
  },

  getRepo: async (id: string): Promise<Repository> => {
    const { data } = await client.get<Repository>(`/repos/${id}`);
    return data;
  },

  reindexRepo: async (id: string): Promise<void> => {
    await client.post(`/repos/${id}/reindex`);
  },

  deleteRepo: async (id: string): Promise<void> => {
    await client.delete(`/repos/${id}`);
  },

  getRepoStats: async (id: string): Promise<RepoStats> => {
    const { data } = await client.get<RepoStats>(`/repos/${id}/stats`);
    return data;
  },

  getFileDependencyGraph: async (id: string): Promise<DependencyGraph> => {
    const { data } = await client.get<DependencyGraph>(`/repos/${id}/graph/files`);
    return data;
  },

  getHistory: async (id: string, limit = 20): Promise<GitHistory> => {
    const { data } = await client.get<GitHistory>(`/repos/${id}/history`, { params: { limit } });
    return data;
  },

  getArchitecture: async (id: string): Promise<ArchitectureSummary> => {
    const { data } = await client.get<ArchitectureSummary>(`/repos/${id}/architecture`);
    return data;
  },

  getTestIntelligence: async (id: string): Promise<TestIntelligence> => {
    const { data } = await client.get<TestIntelligence>(`/repos/${id}/test-intelligence`);
    return data;
  },

  // Q&A
  queryRepo: async (
    repoId: string,
    question: string,
    topK = 5
  ): Promise<QueryResponse> => {
    const { data } = await client.post<QueryResponse>(
      `/repos/${repoId}/query`,
      { question, top_k: topK }
    );
    return data;
  },

  submitFeedback: async (
    repoId: string,
    payload: { question: string; rating: FeedbackRating; model: string; retrieval_count: number }
  ): Promise<void> => {
    await client.post(`/repos/${repoId}/feedback`, payload);
  },

  getFeedbackSummary: async (repoId: string): Promise<FeedbackSummary> => {
    const { data } = await client.get<FeedbackSummary>(`/repos/${repoId}/feedback/summary`);
    return data;
  },

  getQueryMetrics: async (repoId: string): Promise<QueryMetrics> => {
    const { data } = await client.get<QueryMetrics>(`/repos/${repoId}/query-metrics`);
    return data;
  },

  getSourceFile: async (repoId: string, filePath: string): Promise<SourceFilePreview> => {
    const { data } = await client.get<SourceFilePreview>(
      `/repos/${repoId}/source/${filePath.split("/").map(encodeURIComponent).join("/")}`
    );
    return data;
  },

  getRepositoryTour: async (repoId: string): Promise<RepositoryTour> => {
    const { data } = await client.get<RepositoryTour>(`/repos/${repoId}/tour`);
    return data;
  },

  getDocumentation: async (repoId: string): Promise<DocumentationInventory> => {
    const { data } = await client.get<DocumentationInventory>(`/repos/${repoId}/documentation`);
    return data;
  },

  getDocumentationQuality: async (repoId: string): Promise<DocumentationQuality> => {
    const { data } = await client.get<DocumentationQuality>(`/repos/${repoId}/documentation/quality`);
    return data;
  },

  searchRepo: async (repoId: string, query: string, topK = 8): Promise<SearchResponse> => {
    const { data } = await client.get<SearchResponse>(`/repos/${repoId}/search`, { params: { q: query, top_k: topK } });
    return data;
  },

  getLatestChangeAnalysis: async (repoId: string): Promise<LatestChangeAnalysis> => {
    const { data } = await client.get<LatestChangeAnalysis>(`/repos/${repoId}/pr-analysis/latest`);
    return data;
  },

  getCommitAnalysis: async (repoId: string, sha: string): Promise<LatestChangeAnalysis> => {
    const { data } = await client.get<LatestChangeAnalysis>(`/repos/${repoId}/pr-analysis/commit/${sha}`);
    return data;
  },

  getTechnicalDebt: async (repoId: string): Promise<TechnicalDebtSummary> => {
    const { data } = await client.get<TechnicalDebtSummary>(`/repos/${repoId}/technical-debt`);
    return data;
  },

  listIssues: async (repoId: string): Promise<{ issues: RepositoryIssue[] }> => {
    const { data } = await client.get<{ issues: RepositoryIssue[] }>(`/repos/${repoId}/issues`);
    return data;
  },

  analyzeIssue: async (repoId: string, issueNumber: number): Promise<IssueAnalysis> => {
    const { data } = await client.get<IssueAnalysis>(`/repos/${repoId}/issues/${issueNumber}/analysis`);
    return data;
  },

  evaluateRepo: async (repoId: string, question: string, expectedFiles: string[], topK = 5): Promise<EvaluationRun> => {
    const { data } = await client.post<EvaluationRun>(`/repos/${repoId}/evaluate`, { cases: [{ question, expected_files: expectedFiles }], top_k: topK });
    return data;
  },
};

// ─── Error helpers ────────────────────────────────────────────────────────────

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message
    );
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred";
}
