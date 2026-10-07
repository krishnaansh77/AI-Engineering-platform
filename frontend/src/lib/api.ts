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
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  timestamp: Date;
  isLoading?: boolean;
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
