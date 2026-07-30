import pathlib
t = pathlib.Path('scripts/generate.py').read_text()
t = t.replace('[\status\]', '[\status\]')
pathlib.Path('scripts/generate.py').write_text(t)
print('Fixed!')
