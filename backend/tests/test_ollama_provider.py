import unittest
from unittest.mock import patch

from app.providers.llm.factory import get_llm_provider
from app.providers.llm.ollama_provider import OllamaProvider


class TestOllamaProvider(unittest.TestCase):
    def tearDown(self):
        get_llm_provider.cache_clear()

    def test_provider_name_uses_configured_model(self):
        with patch("app.providers.llm.ollama_provider.settings.OLLAMA_LLM_MODEL", "qwen2.5-coder"):
            self.assertEqual(OllamaProvider().get_provider_name(), "ollama/qwen2.5-coder")

    def test_factory_selects_ollama_without_api_key(self):
        with patch("app.providers.llm.factory.settings.LLM_PROVIDER", "ollama"):
            provider = get_llm_provider()
        self.assertIsInstance(provider, OllamaProvider)
