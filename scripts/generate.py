"""AutoFlow AI - Generation Manager."""

import argparse
import importlib
import sys
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from typing import List, Optional, Type
from scripts.generators.common.writer import FileWriter
from scripts.generators.common.validator import OutputValidator

GENERATOR_MAP = {
    "backend.models": {"module": "scripts.generators.backend.models_generator", "class": "ModelsGenerator", "deps": []},
    "backend.schemas": {"module": "scripts.generators.backend.schemas_generator", "class": "SchemasGenerator", "deps": ["backend.models"]},
    "backend.services": {"module": "scripts.generators.backend.services_generator", "class": "ServicesGenerator", "deps": ["backend.models", "backend.schemas"]},
    "backend.api": {"module": "scripts.generators.backend.api_generator", "class": "APIGenerator", "deps": ["backend.services"]},
    "backend.middleware": {"module": "scripts.generators.backend.middleware_generator", "class": "MiddlewareGenerator", "deps": ["backend.models"]},
    "backend.ai": {"module": "scripts.generators.backend.ai_generator", "class": "AIGenerator", "deps": ["backend.models"]},
    "backend.repositories": {"module": "scripts.generators.backend.repositories_generator", "class": "RepositoriesGenerator", "deps": ["backend.models"]},
    "backend.tasks": {"module": "scripts.generators.backend.tasks_generator", "class": "TasksGenerator", "deps": ["backend.services"]},
    "backend.docker": {"module": "scripts.generators.backend.docker_generator", "class": "DockerGenerator", "deps": []},
}

GROUP_MAP = {
    "backend": ["backend.models", "backend.schemas", "backend.repositories", "backend.services", "backend.api", "backend.middleware", "backend.ai", "backend.tasks", "backend.docker"],
    "frontend": ["frontend.pages", "frontend.components", "frontend.stores", "frontend.services"],
    "infra": ["infra.docker", "infra.kubernetes", "infra.github_actions"],
    "docs": ["docs"],
    "all": [g for g in GENERATOR_MAP],
}


class GeneratorRegistry:
    def __init__(self):
        self.generators = dict(GENERATOR_MAP)

    def resolve_group(self, group: str) -> List[str]:
        if group in GROUP_MAP:
            return GROUP_MAP[group]
        if group in self.generators:
            return [group]
        for key in self.generators:
            if key.startswith(group + "."):
                return [key]
        raise ValueError(f"Unknown generator group: {group}")

    def resolve_deps(self, keys: List[str]) -> List[str]:
        resolved = []
        visited = set()
        def visit(key: str):
            if key in visited:
                return
            visited.add(key)
            info = self.generators.get(key)
            if info:
                for dep in info.get("deps", []):
                    visit(dep)
            resolved.append(key)
        for key in keys:
            visit(key)
        return resolved

    def get_info(self, key):
        return self.generators.get(key)


def import_generator_class(module_path: str, class_name: str) -> Type:
    m = importlib.import_module(module_path)
    return getattr(m, class_name)


def execute_generators(keys, root, dry_run=False, force=False):
    reg = GeneratorRegistry()
    resolved = reg.resolve_deps(keys)
    writer = FileWriter(root, dry_run=dry_run)
    results = {}
    total = len(resolved)
    if total == 0:
        print(f'  No generators found for target. Check --list to see available generators.')
        return results
    for i, key in enumerate(resolved):
        info = reg.get_info(key)
        if not info:
            continue
        print(f"  [{i+1}/{total}] {key}...", end="", flush=True)
        start = time.time()
        try:
            cls = import_generator_class(info["module"], info["class"])
            gen = cls(writer=writer)
            files = gen.generate(writer=writer, force=force)
            elapsed = time.time() - start
            results[key] = {"status": "ok", "files": files}
            print(f" done ({elapsed:.1f}s, {len(files)} files)")
        except ImportError as e:
            results[key] = {"status": "skipped"}
            print(f" skipped - {e}")
        except Exception as e:
            results[key] = {"status": "error", "error": str(e)}
            print(f" ERROR: {e}")
        writer.logs.append(f"{key}: {results[key]['status']}")
    return results


def main():
    p = argparse.ArgumentParser(description="AutoFlow AI Code Generator")
    p.add_argument("target", nargs="*", default=["backend"])
    p.add_argument("--dry-run", "-n", action="store_true")
    p.add_argument("--force", "-f", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--validate", action="store_true")
    args = p.parse_args()
    args.target = " ".join(args.target) if isinstance(args.target, list) else args.target
    args.target = args.target.replace(" ", ".")
    root = Path(__file__).resolve().parent.parent
    reg = GeneratorRegistry()
    if args.list:
        print("Available generators:")
        for key in sorted(reg.generators):
            print(f"  {key}")
        print(f"Groups: {sorted(GROUP_MAP.keys())}")
        return
    try:
        keys = reg.resolve_group(args.target)
    except ValueError as e:
        print(f"Error: {e}")
        return
    print(f"Generating: {args.target}")
    print(f"Dry-run: {args.dry_run}, Force: {args.force}")
    results = execute_generators(keys, root, dry_run=args.dry_run, force=args.force)
    ok = sum(1 for r in results.values() if r.get("status") == "ok")
    err = sum(1 for r in results.values() if r.get("status") == "error")
    skp = sum(1 for r in results.values() if r.get("status") == "skipped")
    print(f"Done: {ok} ok, {skp} skipped, {err} errors")
    if args.validate:
        v = OutputValidator.validate_all(root / "backend")
        valid = sum(1 for _, ok, _ in v if ok)
        print(f"Validated: {valid}/{len(v)} files valid")

if __name__ == "__main__":
    main()
