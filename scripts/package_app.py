"""Create a clean Windows source distribution, without account auth or live files."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'dist'/'cortes-ia-windows.zip'
target.parent.mkdir(exist_ok=True)
folders=['app','static','knowledge','docs','gpt','plugin','scripts','tests']
files=['requirements.txt','README.md','start.cmd','start.ps1','.env.example','.gitignore']
with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(ROOT/name,'cortes-ia/'+name)
    for name in folders:
        for path in (ROOT/name).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.mp4','.wav') and path.name != 'live-test.png':
                archive.write(path,'cortes-ia/'+path.relative_to(ROOT).as_posix())
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert not any('/data/' in p or p.endswith('/.env') for p in archive.namelist())
print('Pacote para outros computadores: dist/cortes-ia-windows.zip')
