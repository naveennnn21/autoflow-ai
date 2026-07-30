"""OutputValidator - Validates generated Python files."""
import ast
import pathlib
from typing import List, Tuple

class OutputValidator:
    @staticmethod
    def validate_syntax(code: str) -> Tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
    @staticmethod
    def validate_file(path: pathlib.Path) -> Tuple[bool, str]:
        if not path.exists():
            return False, "Not found"
        try:
            return OutputValidator.validate_syntax(path.read_text(encoding='utf-8'))
        except Exception as e:
            return False, str(e)
    @staticmethod
    def validate_all(root: pathlib.Path) -> List[Tuple[str, bool, str]]:
        return [(str(f.relative_to(root)), *OutputValidator.validate_file(f)) for f in sorted(root.rglob("*.py"))]
