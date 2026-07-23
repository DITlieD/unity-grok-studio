"""Thin vision-describe MCP for FreeLLMAPI / OpenAI-compatible vision endpoints."""
from __future__ import annotations
import base64, json, mimetypes, os, sys, urllib.request, urllib.error
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # minimal stdio fallback message
    FastMCP = None

BASE = os.environ.get('FREELLM_BASE_URL', 'http://127.0.0.1:3001/v1').rstrip('/')
API_KEY = os.environ.get('FREELLM_API_KEY', os.environ.get('OPENAI_API_KEY', 'freellmapi-local'))
VISION_MODEL = os.environ.get('VISION_MODEL', 'auto')

def _b64_image(path: str) -> tuple[str, str]:
    p = Path(path).expanduser().resolve()
    data = p.read_bytes()
    mime = mimetypes.guess_type(str(p))[0] or 'image/png'
    return mime, base64.b64encode(data).decode('ascii')

def describe_image(image_path: str = '', image_base64: str = '', mime: str = 'image/png', question: str = 'Describe this image for a game-dev agent. Be concrete about UI, layout, colors, and text.') -> str:
    if image_path:
        mime, image_base64 = _b64_image(image_path)
    if not image_base64:
        return 'error: provide image_path or image_base64'
    url = f'{BASE}/chat/completions'
    body = {
        'model': VISION_MODEL,
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': question},
                {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{image_base64}'}},
            ],
        }],
        'max_tokens': 1024,
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {API_KEY}')
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
        return payload['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors='replace')
        return f'error HTTP {e.code}: {err[:500]}'
    except Exception as e:
        return f'error: {e}'

if FastMCP is not None:
    mcp = FastMCP('vision-check')
    @mcp.tool()
    def vision_describe(image_path: str = '', image_base64: str = '', mime: str = 'image/png', question: str = 'Describe this image for a game-dev agent. Be concrete about UI, layout, colors, and text.') -> str:
        """Describe an image via FreeLLMAPI vision models (or any OpenAI-compatible vision endpoint)."""
        return describe_image(image_path=image_path, image_base64=image_base64, mime=mime, question=question)
    if __name__ == '__main__':
        mcp.run()
else:
    if __name__ == '__main__':
        # CLI fallback for hooks
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument('--image', required=True)
        ap.add_argument('--question', default='Describe this image for a game-dev agent.')
        args = ap.parse_args()
        print(describe_image(image_path=args.image, question=args.question))
