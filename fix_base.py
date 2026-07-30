import pathlib
p = pathlib.Path('scripts/generators/backend/models_generator.py')
text = p.read_text()

# The BASE definition has multi-line imports without parentheses
# which Python 3.13 rejects. Fix by combining onto one line.
old_base_start = "BASE = J(["
old_items = [
    "    'from sqlalchemy import Boolean, DateTime, Enum, Float,'",
    "    '    ForeignKey, Index, Integer, JSON, String, Text,'",
    "    '    UniqueConstraint',",
]
new_item = "    'from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint',"

# Replace exact first occurrence
idx = text.find(old_base_start)
if idx >= 0:
    for old in old_items:
        text = text.replace(old, '', 1)
    # Insert the new combined line after the BASE = J([ line
    insert_pos = text.find(old_base_start) + len(old_base_start)
    text = text[:insert_pos] + chr(10) + new_item + text[insert_pos:]

p.write_text(text)
print("Fixed BASE imports")
# Verify
count = text.count("'from sqlalchemy import")
print(f"Found {count} import lines in BASE")
