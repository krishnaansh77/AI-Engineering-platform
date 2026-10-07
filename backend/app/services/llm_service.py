"""LLM service for answering codebase questions with verified source code citations."""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.providers.llm.base import LLMMessage, LLMProvider
from app.providers.llm.factory import get_llm_provider
from app.services.retrieval_service import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Source code citation referencing exact file location."""

    file_path: str
    symbol_name: Optional[str]
    chunk_type: str
    start_line: int
    end_line: int


@dataclass
class QueryAnswer:
    """Complete answer to a developer query with source citations."""

    answer: str
    citations: List[Citation]
    model: str
    prompt_tokens: int
    completion_tokens: int


SYSTEM_PROMPT = """You are an expert AI software engineering intelligence assistant.
Your goal is to help developers deeply understand, navigate, and analyze a codebase.

Instructions:
1. Answer the developer's question directly, accurately, and concisely based on the provided Code Context.
2. When referencing components, always reference the specific files, classes, functions, and line ranges provided.
3. If the provided code snippets only partially answer the question, answer what you can and note what additional parts might be needed.
4. If the code context does not contain enough information to answer the question, state that clearly and suggest where or what to search for.
5. Format your response cleanly using GitHub-flavored markdown with code blocks when helpful.
"""


class LLMService:
    """Orchestrates prompt assembly and LLM generation for codebase Q&A."""

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        self.provider = provider or get_llm_provider()

    def _build_context_prompt(
        self, retrieved_chunks: List[RetrievedChunk], repo_name: str
    ) -> str:
        """Format retrieved code chunks into a structured context block for the LLM."""
        if not retrieved_chunks:
            return "No relevant code chunks were found in the index for this query."

        sections = [f"Repository: {repo_name}\nRelevant Code Context:"]
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            symbol_info = f" | Symbol: {chunk.symbol_name}" if chunk.symbol_name else ""
            header = (
                f"--- [Snippet {idx}] {chunk.file_path}{symbol_info} "
                f"({chunk.chunk_type}, Lines {chunk.start_line}–{chunk.end_line}) ---"
            )
            code_block = f"```{chunk.language}\n{chunk.content}\n```"
            sections.append(f"{header}\n{code_block}")

        return "\n\n".join(sections)

    async def answer_query(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
        repo_name: str,
    ) -> QueryAnswer:
        """Generate an answer with citations for a query using retrieved code chunks."""
        context_text = self._build_context_prompt(retrieved_chunks, repo_name)

        user_content = (
            f"Question:\n{query}\n\n"
            f"{context_text}\n\n"
            "Please provide a comprehensive answer and cite relevant files and line numbers."
        )

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_content),
        ]

        logger.info("Calling LLM provider %s for query", self.provider.get_provider_name())
        response = await self.provider.complete(messages)

        # Assemble citations from retrieved chunks
        citations: List[Citation] = []
        seen_citations = set()

        for chunk in retrieved_chunks:
            key = (chunk.file_path, chunk.symbol_name, chunk.start_line, chunk.end_line)
            if key not in seen_citations:
                seen_citations.add(key)
                citations.append(
                    Citation(
                        file_path=chunk.file_path,
                        symbol_name=chunk.symbol_name,
                        chunk_type=chunk.chunk_type,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                    )
                )

        return QueryAnswer(
            answer=response.content,
            citations=citations,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
