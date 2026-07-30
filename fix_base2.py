import pathlib
p = pathlib.Path('scripts/generators/backend/models_generator.py')
text = p.read_text()

# Fix 1: Reorder BASE list - put docstring first, fix trailing comma
old = """BASE = J([
    'from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint',
    '"""AutoFlow AI - SQLAlchemy model."""',
    'import uuid',
    'from datetime import datetime, timezone',
    'from typing import Any, Dict, List, Optional',
    
    'from sqlalchemy.dialects.postgresql import UUID',
    'from sqlalchemy.orm import Mapped, mapped_column,',
    '    relationship',
    'from app.core.database import Base',
    'import enum',
])"""

new = """BASE = J([
    '"""AutoFlow AI - SQLAlchemy model."""',
    'import uuid',
    'from datetime import datetime, timezone',
    'from typing import Any, Dict, List, Optional',
    'from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey,',
    '    Index, Integer, JSON, String, Text, UniqueConstraint',
    'from sqlalchemy.dialects.postgresql import UUID',
    'from sqlalchemy.orm import Mapped, mapped_column,',
    '    relationship',
    'from app.core.database import Base',
    'import enum',
])"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print('Fixed BASE definition - reordered and fixed')
else:
    print('Old pattern not found - current BASE:')
    import re
    m = re.search(r'BASE = J\(\[(.*?)\]\)', text, re.DOTALL)
    if m:
        print(m.group(0))
