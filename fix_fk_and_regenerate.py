import pathlib

p = pathlib.Path('scripts/generators/backend/models_generator.py')
text = p.read_text()

# Fix 1: Update FK function to support nullable parameter
text = text.replace(
    "def FK(t, ondel='CASCADE'):",
    "def FK(t, ondel='CASCADE', nn=True):"
)
text = text.replace(
    "    return f'mapped_column(UUID(as_uuid=True), ForeignKey({Q}{t}.id{Q}, ondelete={Q}{ondel}{Q}), nullable=False, index=True)'",
    "    nns = 'True' if nn else 'False'\n    return f'mapped_column(UUID(as_uuid=True), ForeignKey({Q}{t}.id{Q}, ondelete={Q}{ondel}{Q}), nullable={nns}, index=True)'"
)

# Fix 2: Remove all fragile string replacements
# FK('users') + '.replace("nullable=False", "nullable=True")' -> FK('users', nn=False)
text = text.replace(
    "FK('projects') + '.replace(\"nullable=False, index=True\", \"nullable=True, index=True\")'",
    "FK('projects', nn=False)"
)
text = text.replace(
    "FK('users') + '.replace(\"nullable=False\", \"nullable=True\")'",
    "FK('users', nn=False)"
)
text = text.replace(
    "FK('workflow_nodes') + '.replace(\"nullable=False\", \"nullable=True\")'",
    "FK('workflow_nodes', nn=False)"
)
text = text.replace(
    "FK('subscriptions') + '.replace(\"nullable=False\", \"nullable=True\")'",
    "FK('subscriptions', nn=False)"
)

p.write_text(text)
print("Fixed FK function and removed fragile string replacements")

# Verify no more .replace patterns remain
if '.replace(' in text:
    import re
    matches = re.findall(r'.replace\([^)]+\)', text)
    print(f"WARNING: Still found replace patterns: {matches}")
else:
    print("OK: No remaining .replace patterns")

