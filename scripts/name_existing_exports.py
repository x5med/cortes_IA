"""Add numbered title filenames to existing exports, retaining legacy aliases."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.media import clip_filename

def run():
    import json
    for metadata in (ROOT/'data').glob('*/project.json'):
        project = json.loads(metadata.read_text(encoding='utf-8'))
        output = metadata.parent/'exports'
        for clip in project['clips']:
            if not clip.get('exported'):
                continue
            for item in (clip, dict(clip, id=clip['id']+'-vertical-preview')):
                for extension in ('mp4', 'srt'):
                    source = output/f"{item['id']}.{extension}"
                    target = output/clip_filename(item, extension)
                    if source.exists() and not target.exists():
                        shutil.copyfile(source, target)
                        print(target.name)

if __name__ == '__main__':
    run()
