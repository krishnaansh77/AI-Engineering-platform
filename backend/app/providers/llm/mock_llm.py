"""Deterministic local pseudo-LLM provider for offline testing."""
import re
from typing import List

from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Local, offline LLM provider that synthesizes grounded answers directly from retrieved code snippets."""

    def get_provider_name(self) -> str:
        return "mock/local-code-synthesizer"

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        user_msg = next((m.content for m in messages if m.role == "user"), "")

        # Extract question
        q_match = re.search(r"Question:\s*(.*?)(?=\n\nRepository:|\n\nRelevant Code|$)", user_msg, re.DOTALL)
        question = q_match.group(1).strip() if q_match else "your question"

        # Extract snippets from context block
        snippets = re.findall(
            r"--- \[Snippet \d+\] (.*?) \((.*?), Lines (\d+)[–-](\d+)\) ---",
            user_msg,
        )

        if not snippets:
            content = (
                f"### Analysis\n\n"
                f"I reviewed the repository index for **\"{question}\"**, but no directly relevant code snippets were found. "
                "Try searching for specific module names, function signatures, or configuration files."
            )
        else:
            found_summary = []
            for file_and_sym, chunk_type, start, end in snippets:
                found_summary.append(
                    f"- **`{file_and_sym}`** ({chunk_type}, Lines {start}–{end})"
                )

            bullets = "\n".join(found_summary)
            content = (
                f"### Summary for \"{question}\"\n\n"
                f"Based on the indexed codebase, the relevant logic is implemented in the following components:\n\n"
                f"{bullets}\n\n"
                f"#### Code Architecture Notes\n"
                f"The components above define the primary control flow and interfaces for this functionality. "
                f"Refer to the source citations below to navigate to the exact definitions."
            )

        return LLMResponse(
            content=content,
            model="mock-synthesizer-v1",
            prompt_tokens=len(user_msg.split()),
            completion_tokens=len(content.split()),
        )
