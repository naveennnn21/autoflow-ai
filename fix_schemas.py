import pathlib
p = pathlib.Path('scripts/generators/backend/schemas_generator.py')
text = p.read_text()

# Fix 1: Add key_to_class helper
old = "def make_field(name, py_t, required=True, sensitive=False):"
# Use chr(34) to avoid triple-quote issues
Q = chr(34)
new = f"""def key_to_class(key):
    {Q}{Q}{Q}Convert schema key to proper class name. Key 'team_member' -> 'TeamMember'.{Q}{Q}{Q}
    return ''.join(w.capitalize() for w in key.split('_'))


def make_field(name, py_t, required=True):"""
text = text.replace(old, new)

# Fix 2: Fix key.title() -> key_to_class(key)
text = text.replace("f'class {key.title()}Create(BaseModel):'", "f'class {key_to_class(key)}Create(BaseModel):'")
text = text.replace("f'class {key.title()}Update(BaseModel):'", "f'class {key_to_class(key)}Update(BaseModel):'")
text = text.replace("f'class {key.title()}Response(BaseModel):'", "f'class {key_to_class(key)}Response(BaseModel):'")
text = text.replace("f'class {key.title()}Public(BaseModel):'", "f'class {key_to_class(key)}Public(BaseModel):'")

# Fix 3: Fix Response required logic
text = text.replace(
    "parts.append(make_field(name, pt, required=(not req)))",
    "parts.append(make_field(name, pt, required=True))"
)

# Fix 4: Fix Public schema to use sens flag
text = text.replace(
    "if not sens and name not in ('password_hash', 'access_token', 'refresh_token', 'key_hash'):",
    "if not sens:"
)

# Fix 5: marketplace -> marketplace_item
text = text.replace("SCHEMAS['marketplace'] = {", "SCHEMAS['marketplace_item'] = {")
text = text.replace("('marketplace.py', 'marketplace')", "('marketplace.py', 'marketplace_item')")

# Fix 6: Complete generate() method
old_end = "        results.append(common_path)\n        #"
new_end = f"""        results.append(common_path)
        # Write __init__.py
        init_path = 'backend/app/schemas/__init__.py'
        w.write(init_path, INIT_CONTENT, force=force)
        results.append(init_path)
        return results"""
text = text.replace(old_end, new_end)

p.write_text(text)
print("Applied all fixes")

import ast
try:
    ast.parse(text)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error: {e}")
    # Show last 5 lines
    lines = text.split(chr(10))
    for i in range(max(0, len(lines)-5), len(lines)):
        print(f"{i+1}: {lines[i]}")
