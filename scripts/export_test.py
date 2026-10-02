"""Render editorial test previews; never marks them as approved by the user."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import main
from app.media import run_ffmpeg, transcribe, render
from app.models import RenderRequest

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    project = main.read(args.project)
    folder = main.folder(args.project)
    os.environ['CORTES_LANGUAGE'] = 'pt'
    os.environ['CORTES_ASR_GLOSSARY'] = 'Fábio Rodrigues, X5MED, clínica, clínicas, faturamento, tráfego pago, lead, leads, conversão, script, secretária, Escala Médico, captação, mentalidade empresarial.'
    for clip in project['clips']:
        review = folder / 'review' / clip['id']
        review.mkdir(parents=True, exist_ok=True)
        sample = review / 'source.mp4'
        run_ffmpeg(['-ss', str(clip['start']), '-i', str(folder/project['video']),
                    '-t', str(clip['duration']), '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', str(sample)])
        print('Revisando legendas: ' + clip['id'], flush=True)
        rows = transcribe(sample)
        (review/'captions.json').write_text(json.dumps([s.model_dump() for s in rows], ensure_ascii=False, indent=2), encoding='utf-8')
        for segment in rows:
            segment.start += clip['start']
            segment.end += clip['start']
            for word in segment.words:
                word.start += clip['start']
                word.end += clip['start']
        print('Exportando: ' + clip['title'], flush=True)
        render(folder/project['video'], clip, rows, RenderRequest(format='vertical_fit'), folder/'exports')
        clip['exported'] = True
        clip['export_format'] = 'vertical_fit'
        clip['review_required'] = True
        clip['approved'] = False
        clip['test_preview'] = True
        clip['caption_source'] = 'local-whisper-with-domain-glossary'
        clip['caption_model'] = os.getenv('CORTES_WHISPER_MODEL', 'small')
        clip['caption_segments'] = [s.model_dump() for s in rows]
    main.update(args.project, clips=project['clips'], message='3 prévias reais exportadas; revisar fala e legendas antes de publicar.', status='pronto')

if __name__ == '__main__':
    run()
