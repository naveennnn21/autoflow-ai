import pathlib
p = pathlib.Path('scripts/generators/backend/models_generator.py')
text = p.read_text()

# Fix using simple string replacements - no triple quotes
# Line 1: move docstring before the sqlalchemy import
Q = chr(34)
old1 = f"    'from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint',\n    {Q}{Q}{Q}AutoFlow AI - SQLAlchemy model.{Q}{Q}{Q}'"
new1 = f"    {Q}{Q}{Q}AutoFlow AI - SQLAlchemy model.{Q}{Q}{Q}'\n    'import uuid',\n    'from datetime import datetime, timezone',\n    'from typing import Any, Dict, List, Optional',\n    'from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey,',\n    '    Index, Integer, JSON, String, Text, UniqueConstraint',\n    'from sqlalchemy.dialects.postgresql import UUID',"

text = text.replace(old1, new1)

# Line 2: fix trailing comma in sqlalchemy.orm import
old2 = f"    'from sqlalchemy.orm import Mapped, mapped_column,'"
new2 = f"    'from sqlalchemy.orm import Mapped, mapped_column, relationship'"
text = text.replace(old2, new2)

# Line 3: remove the orphan '    relationship' line
old3 = f"    '    relationship'"
text = text.replace(old3, '')

p.write_text(text)
print('Fixed BASE definition')

# Verify generator syntax
import ast
try:
    ast.parse(text)
    print('Generator syntax: OK')
except SyntaxError as e:
    print(f'Generator syntax error: {e}')
