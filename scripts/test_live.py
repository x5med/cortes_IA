"""Process a user-specified local video with reusable, checkpointed stages."""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import main
from app.media import transcribe, render, run_ffmpeg
from app.models import Segment, Brief, RenderRequest
from app.strategy import analyze


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video')
    parser.add_argument('--project')
    parser.add_argument('--stage', choices=['transcribe', 'analyze', 'render'], required=True)
    parser.add_argument('--audience', default='Pessoas interessadas nos assuntos discutidos pelo apresentador')
    args = parser.parse_args()
    if args.project:
        project = main.read(args.project)
    else:
        source = Path(args.video).resolve(strict=True)
        project = main.create('Teste real · ' + source.stem)
        target = main.folder(project['id']) / ('source' + source.suffix.lower())
        shutil.copyfile(source, target)
        main.update(project['id'], video=target.name)
    project_id = project['id']
    print('PROJECT_ID=' + project_id, flush=True)
    started = time.monotonic()
    def progress(message):
        main.update(project_id, message=message)
        print(message, flush=True)
    main.update(project_id, status='processando')
    try:
        project = main.read(project_id)
        if args.stage == 'transcribe':
            rows = transcribe(main.folder(project_id)/project['video'], progress)
            main.update(project_id, segments=[s.model_dump() for s in rows], clips=[],
                transcription_seconds=round(time.monotonic()-started, 1))
            (main.folder(project_id)/'transcript.json').write_text(
                json.dumps([s.model_dump() for s in rows], ensure_ascii=False, indent=2), encoding='utf-8')
        elif args.stage == 'analyze':
            brief = Brief(audience=args.audience, min_duration=25, max_duration=75, count=5)
            clips = analyze([Segment(**s) for s in project['segments']], brief, progress)
            main.update(project_id, clips=clips, brief=brief.model_dump(),
                analysis_seconds=round(time.monotonic()-started, 1))
        else:
            raise ValueError('A exportação do teste é realizada após revisão dos candidatos.')
        main.update(project_id, status='pronto', message='Etapa de teste concluída')
        print(f'Concluído em {time.monotonic()-started:.1f}s', flush=True)
    except Exception as exc:
        main.update(project_id, status='erro', message=str(exc))
        raise


if __name__ == '__main__':
    run()
