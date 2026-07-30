import pathlib, ast
p = pathlib.Path("scripts/generators/backend/api_generator.py")
t = p.read_text()
t = t.replace("\"    responses={200: {\"description\": \"Paginated list of  + en.lower() + \"s\"}", "\"    responses={200: {\"description\": \"Paginated list of \" + en.lower() + \"s\"}")
p.write_text(t)
try: ast.parse(t); print("OK")
except: import sys; print(f"ERR: {sys.exc_info()[1]}")
