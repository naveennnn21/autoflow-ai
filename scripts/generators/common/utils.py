"""GeneratorUtils - Shared utilities."""
import pathlib
from typing import List

class GeneratorUtils:
    @staticmethod
    def snake_to_pascal(name: str) -> str:
        return ''.join(word.capitalize() for word in name.split('_'))
    @staticmethod
    def pluralize(name: str) -> str:
        if name.endswith('y'):
            return name[:-1] + 'ies'
        return name + 's'
    @staticmethod
    def get_existing_files(root: pathlib.Path, pattern: str = "*.py") -> List[str]:
        return sorted([str(f.relative_to(root)) for f in root.rglob(pattern)])
