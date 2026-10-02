"""Finalize and verify an already transcribed real test, preserving caption previews."""
import argparse
import json
import os
import sys
from pathlib import Path
import av

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import main
from app.media import render, run_ffmpeg, clip_filename
from app.models import Segment, RenderRequest

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    project = main.read(args.project)
    folder = main.folder(args.project)
    output = folder/'exports'
    results = []
    for clip in project['clips']:
        rows = [Segment(**s) for s in json.loads((folder/'review'/clip['id']/'captions.json').read_text(encoding='utf-8'))]
        for s in rows:
            s.start += clip['start']; s.end += clip['start']
            for w in s.words:
                w.start += clip['start']; w.end += clip['start']
        clip['caption_segments'] = [s.model_dump() for s in rows]
        clip['caption_model'] = 'medium'
        # Separate preview is explicitly for caption review. The main downloadable
        # cut preserves the original footage and does not burn unverified ASR.
        preview = dict(clip, id=clip['id']+'-vertical-preview')
        render(folder/project['video'], preview, rows, RenderRequest(format='vertical_fit'), output)
        target = render(folder/project['video'], clip, rows, RenderRequest(format='original', subtitles=False), output)
        clip.update(exported=True, export_format='original', export_subtitles=False, review_required=True, approved=False, test_preview=True)
        for path in (target, output/clip_filename(preview)):
            run_ffmpeg(['-v','error','-i',str(path),'-f','null','-'])
            with av.open(str(path)) as c:
                video = c.streams.video[0]
                results.append({'file':path.name,'duration':round(c.duration/1e6,3),
                                'width':video.width,'height':video.height,
                                'audio':bool(c.streams.audio),'decode_errors':False})
        run_ffmpeg(['-ss','18','-i',str(output/clip_filename(preview)),'-frames:v','1',str(output/(clip['id']+'-review.png'))])
        print('Verificado: '+clip['title'], flush=True)
    (folder/'test-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    main.update(args.project, clips=project['clips'], message='3 cortes originais e prévias verticais exportados. Legendas exigem revisão.', status='pronto')

if __name__ == '__main__':
    run()
