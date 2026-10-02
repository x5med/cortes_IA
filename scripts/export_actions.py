"""Generate the GPT Actions contract from the actual app routes."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import app

schema = app.openapi()
schema['servers'] = [{'url': os.getenv('CORTES_PUBLIC_URL', 'http://127.0.0.1:8000')}]
# Browser handles multipart upload and file download; Actions orchestrate work.
schema['paths'] = {p: methods for p, methods in schema['paths'].items()
                   if p not in ('/api/upload', '/api/health') and not p.endswith('/download')}
for methods in schema['paths'].values():
    for method, operation in methods.items():
        if method == 'post':
            operation['x-openai-isConsequential'] = True
(ROOT / 'gpt' / 'openapi.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
for source, name in [(ROOT/'knowledge'/'editor.md', 'editor.md'), (ROOT/'docs'/'pesquisa.md', 'pesquisa.md')]:
    (ROOT/'gpt'/name).write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
print('Schema e conhecimento do GPT atualizados.')
