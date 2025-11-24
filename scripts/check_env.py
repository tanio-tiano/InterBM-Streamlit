import os
from pathlib import Path

def mask(s):
    if s is None:
        return None
    s = str(s)
    if len(s) <= 8:
        return s
    return f"len={len(s)} prefix={s[:4]}... suffix={s[-4:]}"

root = Path(__file__).resolve().parents[1]
env_path = root / '.env'
print('Workspace root:', root)
print('\n.env exists:', env_path.exists())
if env_path.exists():
    raw = env_path.read_text()
    lines = [l for l in raw.splitlines() if l.strip()!='']
    print('\n.env (first 10 non-empty lines):')
    for i,l in enumerate(lines[:10],1):
        print(f" {i}: {l}")

print('\nOS environ GOOGLE_API_KEY:', mask(os.environ.get('GOOGLE_API_KEY')))
print('OS environ DEV_GOOGLE_API_KEY:', mask(os.environ.get('DEV_GOOGLE_API_KEY')))

try:
    from config import settings
    val = getattr(settings, 'GOOGLE_API_KEY', None)
    print('\nsettings.GOOGLE_API_KEY:', mask(val))
except Exception as e:
    print('\nError importing settings:', e)

# Try git grep for occurrences
try:
    import subprocess
    res = subprocess.run(['git','grep','-n','GOOGLE_API_KEY'], capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        print('\nFiles referencing GOOGLE_API_KEY in repo:')
        print(res.stdout)
    else:
        print('\nNo git grep results or no git available')
except Exception as e:
    print('\nCould not run git grep:', e)
