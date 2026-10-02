"""Re-export existing candidates in full-height 9:16 without captions."""
import argparse
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import main
from app.media import render, run_ffmpeg, clip_filename
from app.models import RenderRequest

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',required=True)
    parser.add_argument('--crop-x',type=float,default=0.5)
    args=parser.parse_args()
    options=RenderRequest(format='vertical_crop',subtitles=False,crop_x=args.crop_x)
    project=main.read(args.project)
    folder=main.folder(args.project)
    output=folder/'exports'
    backup=folder/'previous-exports'
    backup.mkdir(exist_ok=True)
    for clip in project['clips']:
        name=clip_filename(clip)
        if (output/name).exists() and not (backup/name).exists():
            shutil.copyfile(output/name,backup/name)
        target=render(folder/project['video'],clip,[],options,output)
        run_ffmpeg(['-v','error','-i',str(target),'-f','null','-'])
        clip.update(exported=True,export_format='vertical_crop',export_subtitles=False,export_crop_x=args.crop_x,export_follow_face=True)
        review=folder/'framing-review'
        review.mkdir(exist_ok=True)
        for label,at in [('start',2),('middle',clip['duration']/2),('end',clip['duration']-2)]:
            run_ffmpeg(['-ss',str(at),'-i',str(target),'-frames:v','1',str(review/(clip['id']+'-'+label+'.png'))])
        print('Exportado e decodificado: '+name,flush=True)
    main.update(args.project,clips=project['clips'],framing_crop_x=args.crop_x,message='Cortes 9:16 reexportados sem legendas e sem bordas.',status='pronto')

if __name__=='__main__':
    run()
