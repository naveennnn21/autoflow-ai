import pathlib
from scripts.generators.common.writer import FileWriter
from scripts.generators.backend.models_generator import ModelsGenerator

# Fix 1: Fix the Generation Manager CLI to accept sub-arguments
p = pathlib.Path('scripts/generate.py')
text = p.read_text()

# Change nargs from "?" to "+" and join with "."
if 'p.add_argument("target", nargs="?", default="backend")' in text:
    text = text.replace(
        'p.add_argument("target", nargs="?", default="backend")',
        'p.add_argument("target", nargs="*", default=["backend"])'
    )
    # Update the target handling
    text = text.replace(
        'args = p.parse_args()',
        'args = p.parse_args()\n    args.target = " ".join(args.target) if isinstance(args.target, list) else args.target\n    args.target = args.target.replace(" ", ".")'
    )
    p.write_text(text)
    print("Fixed CLI to accept sub-arguments")
else:
    print("CLI already fixed or different pattern")

# Fix 2: Regenerate all model files
w = FileWriter(pathlib.Path('.')) 
g = ModelsGenerator(writer=w)
files = g.generate(force=True)
print(f"Generated {len(files)} files:")
for f in files:
    print(f"  {f}")

# Fix 3: Validate all generated files
print("\nValidating syntax...")
import ast
valid = 0
for f in files:
    path = pathlib.Path(f)
    if path.exists():
        try:
            ast.parse(path.read_text())
            print(f"  OK {f}")
            valid += 1
        except SyntaxError as e:
            print(f"  FAIL {f}: {e}")

print(f"\n{valid}/{len(files)} files pass syntax check")
