import Link from "next/link";
import { BookOpen, Layers, Cpu, Search, Database, ArrowRight } from "lucide-react";

export default function DocsPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Platform Documentation</h1>
        <p className="text-slate-600 mt-2 text-base">
          Architecture overview and intelligence pipeline for the AI Software Engineering Intelligence Platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-sky-50 flex items-center justify-center mb-4">
            <Cpu className="w-5 h-5 text-sky-600" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 mb-2">AST-Based Parsing</h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Unlike basic naive text chunkers, the platform uses <strong>Tree-sitter</strong> to extract
            functions, classes, methods, and modules. Chunks respect grammatical boundaries and include
            docstrings and imports.
          </p>
        </div>

        <div className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center mb-4">
            <Search className="w-5 h-5 text-indigo-600" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Hybrid RAG Retrieval</h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Combines <strong>dense vector search</strong> (pgvector cosine similarity) with
            <strong>sparse keyword search</strong> (BM25Okapi). Rankings are merged using
            <strong>Reciprocal Rank Fusion (RRF)</strong> for state-of-the-art recall.
          </p>
        </div>

        <div className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center mb-4">
            <Database className="w-5 h-5 text-emerald-600" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Provider Abstraction</h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Clean decoupled provider layers allow switching LLMs (OpenAI GPT-4o, Anthropic Claude,
            or local Ollama) and Embeddings (OpenAI, HuggingFace) by modifying environment variables.
          </p>
        </div>

        <div className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center mb-4">
            <Layers className="w-5 h-5 text-amber-600" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Verifiable Source Citations</h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Every AI answer is tied directly to exact source files, function signatures, and line
            ranges (e.g., <code>src/auth/service.py · authenticate_user · L42-68</code>), eliminating hallucinations.
          </p>
        </div>
      </div>

      <div className="p-6 bg-slate-900 rounded-xl text-white">
        <h3 className="text-lg font-semibold mb-2">API Documentation</h3>
        <p className="text-sm text-slate-300 mb-4">
          The FastAPI backend exposes an interactive OpenAPI specification. When running locally, explore the Swagger UI at:
        </p>
        <code className="block bg-slate-800 p-3 rounded text-sky-400 font-mono text-sm mb-4">
          http://localhost:8000/docs
        </code>
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-sky-400 hover:text-sky-300 font-medium"
        >
          Return to Dashboard <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
