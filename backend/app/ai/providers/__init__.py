"""AutoFlow AI - LLM provider package (generated from metadata).

The planner depends only on BaseLLMProvider; concrete SDKs are never
imported directly by the planner.
"""

from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.factory import (
    create_default, provider_factory, provider_names, register_provider,
)

# Register all providers so the factory can resolve them by name.
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.providers.vllm import VLLMProvider

for _name, _cls in [
    ("openai", OpenAIProvider),
    ("anthropic", AnthropicProvider),
    ("gemini", GeminiProvider),
    ("openrouter", OpenRouterProvider),
    ("ollama", OllamaProvider),
    ("vllm", VLLMProvider),
]:
    register_provider(_name, _cls)

__all__ = [
    "AnthropicProvider", "BaseLLMProvider", "GeminiProvider",
    "OllamaProvider", "OpenAIProvider", "OpenRouterProvider",
    "VLLMProvider", "create_default", "provider_factory",
    "provider_names", "register_provider",
]
