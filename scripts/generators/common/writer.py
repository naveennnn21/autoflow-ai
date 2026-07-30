"""FileWriter - Safe file generation."""
import pathlib
from typing import Set

class FileWriter:
    def __init__(self, root, dry_run=False):
        self.root = root
        self.dry_run = dry_run
        self.written = set()
        self.skipped = set()
        self.logs = []
    def write(self, path, content, force=False):
        full = self.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        if full.exists() and not force:
            self.skipped.add(path)
            self.logs.append(f"SKIP: {path}")
            return False
        self.written.add(path)
        tag = "WOULD" if self.dry_run else "WRITE"
        self.logs.append(f"{tag}: {path}")
        if not self.dry_run:
            full.write_text(content, encoding="utf-8")
        return True
    def write_if_missing(self, path, content):
        if (self.root / path).exists():
            return False
        return self.write(path, content, force=True)
    def summary(self):
        return {"written": len(self.written), "skipped": len(self.skipped), "files": sorted(self.written)}
