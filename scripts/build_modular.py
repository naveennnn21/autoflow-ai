import pathlib, os

ROOT = pathlib.Path(__file__).resolve().parent.parent

def write(path, content):
    full = ROOT / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding='utf-8')
    print(f'  OK {path}')

# ============================================================
# PHASE 1: Common Module Init
# ============================================================
write('scripts/generators/__init__.py', '"""AutoFlow AI - Modular Code Generators."""\n')
write('scripts/generators/common/__init__.py', '"""Common generator utilities."""\nfrom scripts.generators.common.writer import FileWriter\nfrom scripts.generators.common.utils import GeneratorUtils\nfrom scripts.generators.common.templates import TemplateProvider\nfrom scripts.generators.common.formatter import CodeFormatter\nfrom scripts.generators.common.validator import OutputValidator\n\n__all__ = ["FileWriter", "GeneratorUtils", "TemplateProvider", "CodeFormatter", "OutputValidator"]\n')
write('scripts/generators/backend/__init__.py', '"""Backend code generators."""\n')
write('scripts/generators/frontend/__init__.py', '"""Frontend code generators."""\n')
write('scripts/generators/infra/__init__.py', '"""Infrastructure code generators."""\n')
write('scripts/generators/docs/__init__.py', '"""Documentation generators."""\n')

print('\nPhase 1: Init files created!')

# ============================================================
# PHASE 2: Common Modules
# ============================================================

write('scripts/generators/common/writer.py', '''"""FileWriter - Safe file generation with dry-run, backup, and diff support."""
import pathlib
import difflib
import shutil
from datetime import datetime
from typing import Optional, Set


class FileWriter:
    """Writes files safely with dry-run mode, backup, and validation."""
    
    def __init__(self, root: pathlib.Path, dry_run: bool = False):
        self.root = root
        self.dry_run = dry_run
        self.written: Set[str] = set()
        self.skipped: Set[str] = set()
        self.errors: list = []
        self.logs: list = []

    def write(self, path: str, content: str, force: bool = False) -> bool:
        full = self.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        
        if full.exists() and not force:
            existing = full.read_text(encoding='utf-8')
            if existing.strip() == content.strip():
                self.skipped.add(path)
                return False
            if not force:
                self.skipped.add(path)
                return False
        
        self.written.add(path)
        self.logs.append(f"{'Would write' if self.dry_run else 'Written'}: {path}")
        
        if not self.dry_run:
            full.write_text(content, encoding='utf-8')
        
        return True

    def write_if_missing(self, path: str, content: str) -> bool:
        full = self.root / path
        if full.exists():
            self.skipped.add(path)
            return False
        return self.write(path, content, force=True)

    def summary(self) -> dict:
        return {
            "written": len(self.written),
            "skipped": len(self.skipped),
            "errors": len(self.errors),
            "files": sorted(self.written),
            "logs": self.logs,
        }
''')

write('scripts/generators/common/utils.py', '''"""GeneratorUtils - Shared utilities for all generators."""
import pathlib
import re
from typing import List, Optional


class GeneratorUtils:
    """Static utility methods for code generation."""

    @staticmethod
    def snake_to_pascal(name: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in name.split('_'))

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """Convert snake_case to camelCase."""
        parts = name.split('_')
        return parts[0] + ''.join(p.capitalize() for p in parts[1:])

    @staticmethod
    def pascal_to_snake(name: str) -> str:
        """Convert PascalCase to snake_case."""
        s1 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
        return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @staticmethod
    def pluralize(name: str) -> str:
        """Simple pluralization."""
        if name.endswith('y'):
            return name[:-1] + 'ies'
        if name.endswith('s') or name.endswith('x') or name.endswith('ch'):
            return name + 'es'
        return name + 's'

    @staticmethod
    def ensure_dir(path: pathlib.Path) -> pathlib.Path:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_existing_files(root: pathlib.Path, pattern: str = "*.py") -> List[str]:
        """Get existing Python files relative to root."""
        files = []
        for f in root.rglob(pattern):
            rel = f.relative_to(root)
            files.append(str(rel))
        return sorted(files)

    @staticmethod
    def header(description: str) -> str:
        """Generate a standard file header."""
        return f'"""{description}"""\n'
''')

write('scripts/generators/common/templates.py', '''"""TemplateProvider - Reusable code templates for generators."""
from typing import Any, Dict, Optional


class TemplateProvider:
    """Provides reusable code templates for code generation."""

    @staticmethod
    def model_imports() -> str:
        return '''import uuid\nfrom datetime import datetime, timezone\nfrom typing import Any, Dict, List, Optional\n\nfrom sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text\nfrom sqlalchemy.dialects.postgresql import UUID\nfrom sqlalchemy.orm import Mapped, mapped_column, relationship\n\nfrom app.core.database import Base\nimport enum\n'''

    @staticmethod
    def schema_imports() -> str:
        return '''from datetime import datetime\nfrom typing import Any, Dict, List, Optional\nfrom uuid import UUID\n\nfrom pydantic import BaseModel, Field\n'''

    @staticmethod
    def service_imports() -> str:
        return '''from typing import Any, Dict, List, Optional\nfrom uuid import UUID\n\nfrom fastapi import HTTPException, status\nfrom sqlalchemy import func, select\nfrom sqlalchemy.ext.asyncio import AsyncSession\n'''

    @staticmethod
    def api_imports() -> str:
        return '''from typing import Optional\nfrom uuid import UUID\n\nfrom fastapi import APIRouter, Depends, HTTPException, Query, status\n'''
''')

write('scripts/generators/common/formatter.py', '''"""CodeFormatter - Formats generated Python code."""
import re
from typing import List


class CodeFormatter:
    """Formats and beautifies generated Python code."""

    @staticmethod
    def format_python(code: str) -> str:
        """Basic Python code formatting."""
        lines = code.split('\n')
        result = []
        indent = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                result.append('')
                continue
            
            # Dedent for closing brackets/braces
            if stripped.startswith('}') or stripped.startswith(']') or stripped.startswith(')'):
                indent = max(0, indent - 1)
            
            result.append('    ' * indent + stripped)
            
            # Indent for opening brackets/braces
            if stripped.endswith('{') or stripped.endswith('[') or stripped.endswith('('):
                indent += 1
            if stripped.endswith(':'):
                indent += 1
        
        return '\n'.join(result)

    @staticmethod
    def ensure_blank_line_before_class(code: str) -> str:
        """Ensure blank line before class definitions."""
        return re.sub(r'([^\n])\nclass ', r'\1\n\nclass ', code)

    @staticmethod
    def ensure_blank_line_before_def(code: str) -> str:
        """Ensure blank line before function definitions (outside classes)."""
        return re.sub(r'([^\n])\n(?=def )', r'\1\n\n', code)
''')

writ
