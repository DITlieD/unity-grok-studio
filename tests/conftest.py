import os, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
os.environ.setdefault('UNITY_GROK_ROOT', str(ROOT))
os.environ.setdefault('SFX_LIB', str(ROOT/'sfx_library'))
