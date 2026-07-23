import pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Construct banned patterns without storing full forbidden literals as contiguous greppable product text.
BANNED = [
  '/home/' + 'lied/teikoku',
  'C:/Users/' + 'LieD',
  'uvx' + '.exe',
  'com.' + 'taporbit',
]
SKIP_DIR = {'.git','.venv','node_modules','__pycache__','tests'}
SKIP_FILE = {'EXCLUDE.md','NOTICE','hygiene_grep.sh','test_path_hygiene.py'}
BIN = {'.png','.jpg','.jpeg','.wav','.dll','.so','.pyc','.pdb','.db'}
def test_no_banned_literals():
    hits = []
    for f in ROOT.rglob('*'):
        if not f.is_file(): continue
        if any(p in f.parts for p in SKIP_DIR): continue
        if f.name in SKIP_FILE: continue
        if f.suffix.lower() in BIN: continue
        try: text = f.read_text(encoding='utf-8', errors='ignore')
        except Exception: continue
        for pat in BANNED:
            if pat in text:
                hits.append((str(f.relative_to(ROOT)), pat))
    assert hits == [], hits[:20]
def test_hygiene_script_exit0():
    r = subprocess.run(['bash', str(ROOT/'scripts'/'hygiene_grep.sh')], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
