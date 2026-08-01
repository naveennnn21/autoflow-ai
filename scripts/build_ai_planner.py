"""Programmatic builder for scripts/generators/backend/ai_planner_generator.py.

The AI Planner Generator is large; anchor-based patching is unreliable due
to escaped-newline differences. This script instead:

1. Parses the generator file and imports it.
2. Detects which provider modules are already registered in MODULE_SOURCES.
3. Appends ONLY the missing provider sources (ollama, vllm, providers/__init__)
   to the end of the file, rewriting the file as a whole.
4. Appends the AIPlannerGenerator class + test/docs builders (once), read from
   scripts/generators/backend/ai_planner_class_source.py.
5. Applies one verified in-registry fix to planner.py's _from_cache.
6. Verifies: AST parse, import, per-source compile, and registry count.

Run: python scripts/build_ai_planner.py
"""

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "scripts/generators/backend/ai_planner_generator.py"
CLASS_SRC_FILE = ROOT / "scripts/generators/backend/ai_planner_class_source.py"


def _load_generator():
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("ai_planner_generator", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Missing provider sources
# ---------------------------------------------------------------------------

OLLAMA_SOURCE = '''"""AutoFlow AI - Ollama provider (generated from metadata).

Local provider; requires no API key.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError
from app.ai.providers.base import BaseLLMProvider

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class OllamaProvider(BaseLLMProvider):
    """Ollama local chat provider."""

    name = "ollama"
    env_key = ""  # no key required
    default_model = "llama3.1"
    capabilities = ["chat"]
    streaming = True

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=120):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "http://localhost:11434",
                         timeout_seconds=timeout_seconds)

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        if not _HAS_HTTPX:
            raise ProviderError("ollama requires httpx", provider=self.name)
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            resp = _httpx.post(self.base_url + "/api/chat", json=payload,
                               timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message", {}).get("content") or "").strip()
        except Exception as exc:
            raise ProviderError(f"ollama: {exc}", provider=self.name) from exc
'''


VLLM_SOURCE = '''"""AutoFlow AI - vLLM provider (generated from metadata).

vLLM serves an OpenAI-compatible REST API; requires no SDK beyond httpx.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class VLLMProvider(BaseLLMProvider):
    """vLLM OpenAI-compatible chat provider."""

    name = "vllm"
    env_key = "VLLM_API_KEY"
    default_model = ""
    capabilities = ["chat", "json_mode"]
    streaming = True

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=60):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "http://localhost:8000/v1",
                         timeout_seconds=timeout_seconds)

    def is_configured(self) -> bool:
        return True  # local deployments need no key

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        if not _HAS_HTTPX:
            raise ProviderNotConfiguredError(provider=self.name)
        try:
            payload = {
                "model": self.model,
                "messages": self._messages(system, prompt),
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            resp = _httpx.post(self.base_url + "/chat/completions",
                               json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            return (choices[0].get("message", {}).get("content") or "").strip()
        except Exception as exc:
            raise ProviderError(f"vllm: {exc}", provider=self.name) from exc
'''


PROVIDERS_INIT_SOURCE = '''"""AutoFlow AI - LLM provider package (generated from metadata).

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
'''


# ---------------------------------------------------------------------------
# Registry fix for planner.py _from_cache (verified, count==1)
# ---------------------------------------------------------------------------

_EXCEPTIONS_IMPORT_OLD = (
    'A single exception hierarchy for the planning pipeline so callers can\n'
    'catch one base type and inspect ``stage`` for granular handling.\n"""\n\n\nclass PlannerError'
)

_EXCEPTIONS_IMPORT_NEW = (
    'A single exception hierarchy for the planning pipeline so callers can\n'
    'catch one base type and inspect ``stage`` for granular handling.\n"""\n\n'
    'from typing import Optional\n\n\nclass PlannerError'
)


_FROM_CACHE_OLD = """    @staticmethod
    def _from_cache(cached: Dict[str, Any]) -> Optional[PlanResult]:
        try:
            return PlanResult(**cached)
        except Exception:
            return None
"""

_FROM_CACHE_NEW = """    @staticmethod
    def _from_cache(cached: Dict[str, Any]) -> Optional[PlanResult]:
        try:
            plan_data = cached.get("plan")
            plan = None
            if isinstance(plan_data, dict):
                plan = WorkflowPlan(**plan_data)
            result = PlanResult(**{k: v for k, v in cached.items()
                                   if k != "plan"})
            result.plan = plan
            return result
        except Exception:
            return None
"""


_CATALOG_ALIAS_OLD = (
    '        for cname, cdef in found.items():\n'
    '            meta = getattr(cdef, "metadata", {}) or {}\n'
    '            catalog[cname] = {\n'
    '                "name": cname,\n'
    '                "version": meta.get("version", "1.0.0"),\n'
    '                "authentication": meta.get("authentication") or meta.get("auth", {}),\n'
    '                "actions": list((meta.get("actions") or {}).keys()),\n'
    '                "triggers": list((meta.get("triggers") or {}).keys()),\n'
    '                "capabilities": meta.get("capabilities", {}) or {},\n'
    '            }'
)

_CATALOG_ALIAS_NEW = (
    '        for cname, cdef in found.items():\n'
    '            meta = getattr(cdef, "metadata", {}) or {}\n'
    '            entry = {\n'
    '                "name": cname,\n'
    '                "version": meta.get("version", "1.0.0"),\n'
    '                "authentication": meta.get("authentication") or meta.get("auth", {}),\n'
    '                "actions": list((meta.get("actions") or {}).keys()),\n'
    '                "triggers": list((meta.get("triggers") or {}).keys()),\n'
    '                "capabilities": meta.get("capabilities", {}) or {},\n'
    '            }\n'
    '            catalog[cname] = entry\n'
    '            # Index by module slug too so planner lookups by module name work.\n'
    '            slug = meta.get("module_name") or str(cname).lower().replace(" ", "_")\n'
    '            if slug and slug != cname and slug not in catalog:\n'
    '                catalog[slug] = entry'
)


_PIPELINE_SELECT_OLD = (
    '            if not connector:\n'
    '                # Infer from the first candidate.\n'
    '                try:\n'
    '                    connector = self.selector.select(entities, task.get("target", ""))\n'
    '                except Exception:\n'
    '                    connector = ""'
)

_PIPELINE_SELECT_NEW = (
    '            if not connector:\n'
    '                # Infer from the first candidate.\n'
    '                try:\n'
    '                    selected = self.selector.select(entities, task.get("target", ""))\n'
    '                    connector = selected.get("connector", "") if isinstance(selected, dict) else str(selected)\n'
    '                except Exception:\n'
    '                    connector = ""'
)


_NORMALIZER_IMPORT_OLD = (
    'import re\nimport unicodedata\n\nfrom app.ai.planner.exceptions import NormalizationError'
)

_NORMALIZER_IMPORT_NEW = (
    'import re\nimport unicodedata\nfrom dataclasses import dataclass\n'
    'from typing import List\n\nfrom app.ai.planner.exceptions import NormalizationError'
)


_PIPELINE_DEAD_CODE_OLD = (
    "        cap_scores = [\n"
    "            getattr(s, \"score\", 0.5) for s in []\n"
    "        ]\n"
    "        matches_scores: List[float] = []\n"
)

_PIPELINE_DEAD_CODE_NEW = (
    "        matches_scores: List[float] = []\n"
)

_PIPELINE_SETPROVIDER_OLD = (
    "        self.confidence = ConfidenceScorer()\n"
    "\n"
    "    # -- stage runners"
)

_PIPELINE_SETPROVIDER_NEW = (
    "        self.confidence = ConfidenceScorer()\n"
    "\n"
    "    def set_provider(self, provider: Optional[Any]) -> None:\n"
    "        \"\"\"Re-bind the LLM provider across LLM-capable stages.\"\"\"\n"
    "        self.provider = provider\n"
    "        self.intent.provider = provider\n"
    "        self.entities.provider = provider\n"
    "        self.tasks.provider = provider\n"
    "\n"
    "    # -- stage runners"
)

_PLANNER_PROVIDER_OLD = (
    "        if active_provider is not self.pipeline.provider:\n"
    "            self.pipeline.provider = active_provider\n"
)

_PLANNER_PROVIDER_NEW = (
    "        if active_provider is not self.pipeline.provider:\n"
    "            self.pipeline.set_provider(active_provider)\n"
)


def _apply_registry_fixes(mod) -> dict:
    """Apply verified in-registry fixes; returns {name: applied_count}."""
    fixes = {}

    src = mod.MODULE_SOURCES.get("planner", "")
    count = src.count(_FROM_CACHE_OLD)
    if count == 1:
        mod.MODULE_SOURCES["planner"] = src.replace(_FROM_CACHE_OLD,
                                                    _FROM_CACHE_NEW)
    fixes["planner._from_cache"] = count

    exc = mod.MODULE_SOURCES.get("exceptions", "")
    count = exc.count(_EXCEPTIONS_IMPORT_OLD)
    if count == 1:
        mod.MODULE_SOURCES["exceptions"] = exc.replace(
            _EXCEPTIONS_IMPORT_OLD, _EXCEPTIONS_IMPORT_NEW)
    fixes["exceptions.Optional_import"] = count

    norm = mod.MODULE_SOURCES.get("normalizer", "")
    count = norm.count(_NORMALIZER_IMPORT_OLD)
    if count == 1:
        mod.MODULE_SOURCES["normalizer"] = norm.replace(
            _NORMALIZER_IMPORT_OLD, _NORMALIZER_IMPORT_NEW)
    fixes["normalizer.List_import"] = count

    pipe = mod.MODULE_SOURCES.get("pipeline", "")
    count = pipe.count(_PIPELINE_SELECT_OLD)
    if count == 1:
        mod.MODULE_SOURCES["pipeline"] = pipe.replace(
            _PIPELINE_SELECT_OLD, _PIPELINE_SELECT_NEW)
    fixes["pipeline.selector_dict_bug"] = count

    cs = mod.MODULE_SOURCES.get("connector_selector", "")
    count = cs.count(_CATALOG_ALIAS_OLD)
    if count == 1:
        mod.MODULE_SOURCES["connector_selector"] = cs.replace(
            _CATALOG_ALIAS_OLD, _CATALOG_ALIAS_NEW)
    fixes["connector_selector.slug_aliases"] = count

    pipe = mod.MODULE_SOURCES.get("pipeline", "")
    count = pipe.count(_PIPELINE_DEAD_CODE_OLD)
    if count == 1:
        mod.MODULE_SOURCES["pipeline"] = pipe.replace(
            _PIPELINE_DEAD_CODE_OLD, _PIPELINE_DEAD_CODE_NEW)
    fixes["pipeline.dead_code_removed"] = count
    count = pipe.count(_PIPELINE_SETPROVIDER_OLD)
    if count == 1:
        mod.MODULE_SOURCES["pipeline"] = mod.MODULE_SOURCES["pipeline"].replace(
            _PIPELINE_SETPROVIDER_OLD, _PIPELINE_SETPROVIDER_NEW)
    fixes["pipeline.set_provider_added"] = count

    plan = mod.MODULE_SOURCES.get("planner", "")
    count = plan.count(_PLANNER_PROVIDER_OLD)
    if count == 1:
        mod.MODULE_SOURCES["planner"] = plan.replace(
            _PLANNER_PROVIDER_OLD, _PLANNER_PROVIDER_NEW)
    fixes["planner.provider_propagation"] = count
    return fixes


# Pairs persisted back into the generator file after a successful build.
_PERSIST_FIXES = [
    ("planner", _FROM_CACHE_OLD, _FROM_CACHE_NEW),
    ("exceptions", _EXCEPTIONS_IMPORT_OLD, _EXCEPTIONS_IMPORT_NEW),
    ("normalizer", _NORMALIZER_IMPORT_OLD, _NORMALIZER_IMPORT_NEW),
    ("pipeline", _PIPELINE_SELECT_OLD, _PIPELINE_SELECT_NEW),
    ("connector_selector", _CATALOG_ALIAS_OLD, _CATALOG_ALIAS_NEW),
    ("pipeline", _PIPELINE_DEAD_CODE_OLD, _PIPELINE_DEAD_CODE_NEW),
    ("pipeline", _PIPELINE_SETPROVIDER_OLD, _PIPELINE_SETPROVIDER_NEW),
    ("planner", _PLANNER_PROVIDER_OLD, _PLANNER_PROVIDER_NEW),
]


def _provider_blocks() -> str:
    """Append blocks for the three provider modules (caller decides)."""
    return (
        "\n\n# ---------------------------------------------------------------------------\n"
        "# providers/ollama.py\n"
        "# ---------------------------------------------------------------------------\n\n"
        f'_register_source("providers/ollama", \'\'\'{OLLAMA_SOURCE}\'\'\')\n'
        "\n\n# ---------------------------------------------------------------------------\n"
        "# providers/vllm.py\n"
        "# ---------------------------------------------------------------------------\n\n"
        f'_register_source("providers/vllm", \'\'\'{VLLM_SOURCE}\'\'\')\n'
        "\n\n# ---------------------------------------------------------------------------\n"
        "# providers/__init__.py\n"
        "# ---------------------------------------------------------------------------\n\n"
        f'_register_source("providers/__init__", \'\'\'{PROVIDERS_INIT_SOURCE}\'\'\')\n'
    )


CLASS_BEGIN = "# --- AI_PLANNER_CLASS_SOURCE_BEGIN ---"
CLASS_END = "# --- AI_PLANNER_CLASS_SOURCE_END ---"


def _class_source() -> str:
    """Read the AIPlannerGenerator class + builders source (wrapped markers)."""
    body = CLASS_SRC_FILE.read_text(encoding="utf-8").strip()
    return ("\n\n# ---------------------------------------------------------------------------\n"
            "# AIPlannerGenerator class + builders (from ai_planner_class_source.py)\n"
            "# ---------------------------------------------------------------------------\n"
            + CLASS_BEGIN + "\n" + body + "\n" + CLASS_END + "\n")


def main() -> int:
    src = GEN.read_text(encoding="utf-8")

    # 1) Detect already-registered provider modules.
    existing = set(re.findall(r'_register_source\("providers/([^"]+)"', src))
    print("existing provider modules:", sorted(existing))

    # 2) Append ONLY missing providers.
    missing = []
    if "ollama" not in existing:
        missing.append("ollama")
    if "vllm" not in existing:
        missing.append("vllm")
    if "__init__" not in existing:
        missing.append("__init__")

    out = src.rstrip() + "\n"
    if missing:
        print("appending missing providers:", missing)
        out += _provider_blocks()
    else:
        print("all providers already registered")

    # 3) Sync the generator class + builders from the source-of-truth module.
    #    Replace the marked block when present; otherwise append it.
    if CLASS_BEGIN in out and CLASS_END in out:
        start = out.index(CLASS_BEGIN)
        end = out.index(CLASS_END) + len(CLASS_END)
        out = out[:start] + _class_source().strip() + "\n" + out[end:]
        print("re-synced AIPlannerGenerator class block")
    else:
        print("appending AIPlannerGenerator class + builders")
        out += _class_source()

    # 4) Rewrite the file as a whole.
    GEN.write_text(out + "\n", encoding="utf-8")
    print(f"rewrote {GEN} ({out.count(chr(10))} lines)")

    # 5) Verify: AST + import + registry count + per-source compile.
    import ast
    ast.parse(out)
    print("AST OK")

    mod = _load_generator()
    names = sorted(mod.MODULE_SOURCES.keys())
    print("registry count:", len(names))
    for n in names:
        print("  -", n)

    fixes = _apply_registry_fixes(mod)
    for name, applied in fixes.items():
        print(f"registry fix {name}: {applied}")
    if any(fixes.values()):
        # Persist registry fixes into the file.
        fixed_src = GEN.read_text(encoding="utf-8")
        for _tag, _old, _new in _PERSIST_FIXES:
            if _old in fixed_src:
                fixed_src = fixed_src.replace(_old, _new)
        GEN.write_text(fixed_src, encoding="utf-8")
        print("persisted registry fixes")

    # End-to-end persist verification: reload from the file and confirm every
    # fix's OLD string is gone from the registry sources (would catch silent
    # escape-mismatch no-ops where the in-memory fix passed but the file was
    # not actually updated).
    reloaded = _load_generator()
    leftovers = []
    for _tag, _old, _new in _PERSIST_FIXES:
        _src = reloaded.MODULE_SOURCES.get(_tag, "")
        if _old in _src:
            leftovers.append(f"{_tag}: old string still present")
    if leftovers:
        print("PERSIST VERIFY FAIL:", leftovers)
        return 1
    print("persist verify: all registry fixes durable in file")

    bad = []
    for n, s in mod.MODULE_SOURCES.items():
        try:
            compile(s, n + ".py", "exec")
        except SyntaxError as exc:
            bad.append((n, str(exc)))
    print("sources that fail to compile:", len(bad))
    for n, e in bad:
        print("  BAD", n, e)

    expected = {"ollama", "vllm", "__init__"}
    after = set(re.findall(r'_register_source\("providers/([^"]+)"',
                           GEN.read_text(encoding="utf-8")))
    missing_after = expected - after
    print("missing providers after build:", sorted(missing_after))

    ok = not bad and not missing_after
    print("BUILD", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
