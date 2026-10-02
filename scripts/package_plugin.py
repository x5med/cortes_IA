"""Package only authored plugin files, never dependencies or private studio data."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT/'plugin'/'cortes-ia'
references = PLUGIN/'skills'/'cortes-estrategicos'/'references'
references.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT/'knowledge'/'editor.md', references/'editor.md')
shutil.copyfile(ROOT/'docs'/'pesquisa.md', references/'pesquisa.md')
manifest = json.loads((PLUGIN/'plugin.json').read_text(encoding='utf-8'))
assert len(manifest['extensions']['com.openai']['interface']['shortDescription']) <= 30
target = ROOT/'dist'/'cortes-ia-plugin.zip'
target.parent.mkdir(exist_ok=True)
with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
    for path in PLUGIN.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            archive.write(path, path.relative_to(PLUGIN.parent))
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert 'cortes-ia/plugin.json' in archive.namelist()
print('Plugin privado exportado: dist/cortes-ia-plugin.zip')
