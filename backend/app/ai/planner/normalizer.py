"""AutoFlow AI - Prompt normalizer (stage 1, generated from metadata).

Deterministic normalization: lowercasing, whitespace collapse, stopword
trimming (preserving connector/action keywords), smart-quote and ligature
normalization, trailing punctuation cleanup, and a canonical structured
dict so downstream stages share a stable prompt fingerprint.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List

from app.ai.planner.exceptions import NormalizationError

# Words that carry no planning signal and can be trimmed from the ends.
STOPWORDS = {
    "a", "an", "the", "please", "kindly", "would", "could", "can", "i",
    "we", "you", "me", "my", "our", "us", "to", "for", "of", "on", "at",
    "in", "with", "and", "or", "so", "that", "this", "these", "those",
    "then", "just", "maybe", "perhaps", "possibly", "let", "lets", "us",
    "need", "want", "like", "wanna", "gonna", "do", "does", "did", "will",
    "would", "should", "could", "might", "automatically", "whenever",
}

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def normalize_text(text: str) -> str:
    """Normalize a single prompt string into canonical form."""
    if not text or not text.strip():
        raise NormalizationError("Prompt is empty")
    # NFC + remove zero-width / control characters
    text = unicodedata.normalize("NFC", text)
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Lowercase but keep things like connector names
    text = text.lower()
    # Normalize curly quotes / dashes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", "\"").replace("\u201d", "\"")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    # Trim trailing punctuation
    text = text.rstrip(".,;:!?")
    return text


def tokens(text: str) -> List[str]:
    """Return lowercase word tokens of a normalized string."""
    return _WORD_RE.findall(text.lower())


def trim_stopwords(text: str) -> str:
    """Trim leading/trailing stopwords from a normalized prompt."""
    toks = tokens(text)
    if not toks:
        return text
    start = 0
    while start < len(toks) and toks[start] in STOPWORDS:
        start += 1
    end = len(toks)
    while end > start and toks[end - 1] in STOPWORDS:
        end -= 1
    return " ".join(toks[start:end]) if start < end else text


def keyword_signature(text: str) -> str:
    """A canonical keyword multiset signature used for cache/identity."""
    return " ".join(sorted(set(tokens(text))))


@dataclass
class NormalizedPrompt:
    """The canonical, structured form of a user prompt."""

    raw: str
    text: str
    signature: str
    word_count: int
    keywords: List[str]

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "text": self.text,
            "signature": self.signature,
            "word_count": self.word_count,
            "keywords": list(self.keywords),
        }


class PromptNormalizer:
    """Deterministic stage-1 normalizer."""

    def normalize(self, prompt: str) -> NormalizedPrompt:
        """Normalize a raw prompt into a structured form."""
        raw = prompt
        text = normalize_text(prompt)
        text = trim_stopwords(text)
        return NormalizedPrompt(
            raw=raw,
            text=text,
            signature=keyword_signature(text),
            word_count=len(tokens(text)),
            keywords=sorted(set(tokens(text))),
        )
