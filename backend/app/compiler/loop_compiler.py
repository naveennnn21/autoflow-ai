"""AutoFlow AI - Loop compiler (generated from metadata).

Compiles loop specifications (``{collection, item, index, max_iterations,
steps}``) into ``LoopSpec`` with validation.
"""

from typing import Any, Dict

from app.compiler.exceptions import InvalidLoopError
from app.compiler.models import LoopSpec

VALID_LOOP_KEYS = {"collection", "item", "index", "max_iterations", "steps",
                   "raw", "source"}


def compile_loop(loop: Any) -> LoopSpec:
    """Compile a loop spec from dict or None."""
    if loop is None:
        raise InvalidLoopError("loop is None")
    if isinstance(loop, str):
        return LoopSpec(raw=loop, collection=loop)
    if not isinstance(loop, dict):
        raise InvalidLoopError(
            f"cannot compile loop of type {type(loop).__name__}")
    unknown = set(loop.keys()) - VALID_LOOP_KEYS
    if unknown:
        raise InvalidLoopError(f"unknown loop keys: {sorted(unknown)}")
    collection = str(loop.get("collection") or loop.get("source") or "")
    if not collection:
        raise InvalidLoopError("loop requires a 'collection'")
    # Use the default only when the key is absent; an explicit 0 (or any
    # value < 1) is an error.
    if "max_iterations" in loop:
        try:
            max_iter = int(loop["max_iterations"])
        except (TypeError, ValueError):
            raise InvalidLoopError("max_iterations must be an integer")
    else:
        max_iter = 100
    if max_iter < 1:
        raise InvalidLoopError("max_iterations must be >= 1")
    steps = [str(s) for s in (loop.get("steps") or [])]
    return LoopSpec(
        raw=str(loop.get("raw", "")),
        collection=collection,
        item=str(loop.get("item", "item")),
        index=str(loop.get("index", "index")),
        max_iterations=max_iter,
        steps=steps,
    )
