import json
import csv
import re
import subprocess
import textwrap
import unicodedata
from pathlib import Path
import imageio_ffmpeg
import os
import threading
from functools import lru_cache
from .models import Segment, Word
from .strategy import validate_transcript


def run_ffmpeg(args, cwd=None):
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-y', *args],
                            cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=7200)
    if result.returncode:
        raise ValueError('Falha no processamento do vídeo: ' + result.stderr[-1500:])
    return result


def timestamp(value):
    h, m, s = value.replace(',', '.').split(':')
    return int(h)*3600 + int(m)*60 + float(s)


def parse_transcript(content: str, suffix: str):
    if suffix.lower() == '.json':
        raw = json.loads(content)
        rows = raw['segments'] if isinstance(raw, dict) else raw
        return validate_transcript([Segment.model_validate(x) for x in rows])
    rows = []
    for block in re.split(r'\n\s*\n', content.replace('\r', '').strip()):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if '-->' in line), None)
        if timing is not None:
            a, b = lines[timing].split('-->')
            rows.append(Segment(start=timestamp(a.strip()), end=timestamp(b.strip()),
                                text=' '.join(lines[timing+1:])))
    if not rows:
        raise ValueError('Envie SRT ou JSON com segmentos {start, end, text}.')
    return validate_transcript(rows)


ASR_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def whisper_model():
    from faster_whisper import WhisperModel
    return WhisperModel(os.getenv('CORTES_WHISPER_MODEL', 'small'), device='cpu', compute_type='int8',
                        cpu_threads=min(4, os.cpu_count() or 2), num_workers=1)


def transcribe(video: Path, progress=lambda _: None):
    # Local inference only. Model files are downloaded once and cached per computer.
    audio = video.parent/'transcription.wav'
    checkpoint = video.parent/'transcription.checkpoint.json'
    signature = {'size':video.stat().st_size, 'mtime_ns':video.stat().st_mtime_ns,
                 'model':os.getenv('CORTES_WHISPER_MODEL','small'), 'language':os.getenv('CORTES_LANGUAGE',''),
                 'glossary':os.getenv('CORTES_ASR_GLOSSARY','')}
    rows = []
    if checkpoint.exists():
        try:
            cached = json.loads(checkpoint.read_text(encoding='utf-8'))
            cached['signature'].setdefault('glossary', '')
            if cached['signature'] == signature:
                rows = [Segment(**s) for s in cached['rows']]
                if cached.get('complete'):
                    return validate_transcript(rows)
        except (ValueError, KeyError):
            rows = []
    offset = rows[-1].end if rows else 0
    progress('Extraindo áudio localmente')
    run_ffmpeg(['-ss', str(offset), '-i', str(video), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(audio)])
    def save_checkpoint(complete=False):
        temporary = checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps({'signature':signature, 'rows':[s.model_dump() for s in rows],
                                         'complete':complete}, ensure_ascii=False), encoding='utf-8')
        temporary.replace(checkpoint)
    with ASR_LOCK:
        progress('Carregando Whisper local (primeira execução baixa o modelo gratuito)')
        model = whisper_model()
        segments, info = model.transcribe(str(audio), language=os.getenv('CORTES_LANGUAGE') or None,
            beam_size=5, word_timestamps=True, vad_filter=True, condition_on_previous_text=False,
            initial_prompt=os.getenv('CORTES_ASR_GLOSSARY') or None)
        for segment in segments:
            if not segment.text.strip() or segment.end <= segment.start:
                continue
            words = [Word(start=offset+w.start, end=offset+w.end, word=w.word) for w in segment.words or []]
            rows.append(Segment(start=offset+segment.start, end=offset+segment.end, text=segment.text.strip(), words=words))
            save_checkpoint()
            progress(f'Transcrição local: {offset+segment.end:.0f}s / {offset+info.duration:.0f}s · idioma {info.language}')
    audio.unlink(missing_ok=True)
    if not rows:
        raise ValueError('Não foi encontrada fala no áudio.')
    save_checkpoint(complete=True)
    return validate_transcript(rows)


def srt_time(seconds):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def subtitles(segments, start, end):
    entries = []
    for s in segments:
        a, b = max(start, s.start), min(end, s.end)
        if b <= a:
            continue
        def append_caption(begin, finish, text):
            clean = re.sub(r'<[^>]*>', '', text).replace('{', '').replace('}', '').replace('\\', '')
            lines = '\n'.join(textwrap.wrap(clean.strip(), 32))
            if finish > begin and lines:
                entries.append(f'{len(entries)+1}\n{srt_time(begin-start)} --> {srt_time(finish-start)}\n{lines}\n')
        if not s.words:
            append_caption(a, b, s.text)
            continue
        words = [w for w in s.words if w.end > start and w.start < end]
        batch = []
        for i, word in enumerate(words):
            batch.append(word)
            if len(batch) >= 6 or len(''.join(w.word for w in batch)) >= 45 or i == len(words)-1:
                append_caption(max(start, batch[0].start), min(end, batch[-1].end), ''.join(w.word for w in batch))
                batch = []
    return '\n'.join(entries)


def clip_filename(clip, extension='mp4'):
    number = re.fullmatch(r'clip-(\d+)(-vertical-preview)?', clip['id'])
    if not number or extension not in ('mp4', 'srt'):
        raise ValueError('Identificador ou extensão de corte inválido.')
    title = unicodedata.normalize('NFC', clip.get('title') or 'Corte')
    title = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f“”‘’]', '', title)
    title = re.sub(r'\s+', ' ', title).strip(' .')[:100].rstrip(' .') or 'Corte'
    suffix = ' - Prévia vertical' if number.group(2) else ''
    return f'{int(number.group(1)):02d} - {title}{suffix}.{extension}'


def render(video, clip, segments, options, output):
    output.mkdir(exist_ok=True)
    srt = output / clip_filename(clip, 'srt')
    if options.subtitles:
        srt.write_text(subtitles(segments, clip['start'], clip['end']), encoding='utf-8')
    filters = []
    if options.format == 'vertical_fit':
        filters.append('scale=720:1280:force_original_aspect_ratio=decrease:flags=lanczos,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black')
    elif options.format == 'vertical_crop':
        follow = ''
        if options.follow_face:
            from .framing import face_track, crop_commands
            commands=output/f"{clip['id']}-framing.txt"
            commands.write_text(crop_commands(face_track(video,clip['start'],clip['end'],options.crop_x),clip['duration']),encoding='ascii')
            follow=f'sendcmd=f={commands.name},'
        filters.append(f'scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos,{follow}crop@follow=720:1280:x=(iw-ow)*{options.crop_x}:y=(ih-oh)/2,setsar=1')
    else:
        filters.append('scale=trunc(iw/2)*2:trunc(ih/2)*2')
    if options.subtitles:
        # Explicit ASS canvas prevents SRT's default 384x288 canvas from producing giant text.
        if options.format == 'original':
            import av
            with av.open(str(video)) as container:
                stream = container.streams.video[0]
                width, height = stream.width // 2 * 2, stream.height // 2 * 2
        else:
            width, height = 720, 1280
        ass = output / f"{clip['id']}.ass"
        margin_v = round(height * 0.30) if options.format == 'vertical_fit' else None
        ass.write_text(srt_to_ass(srt.read_text(encoding='utf-8'), width, height, margin_v), encoding='utf-8')
        filters.append(f'ass={ass.name}')
    target = output / clip_filename(clip)
    run_ffmpeg(['-ss', str(clip['start']), '-i', str(video.resolve()), '-t', str(clip['duration']),
                '-map', '0:v:0', '-map', '0:a:0?', '-vf', ','.join(filters), '-c:v', 'libx264',
                '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                '-movflags', '+faststart', str(target.resolve())], cwd=output)
    return target


def srt_to_ass(content, width, height, margin_v=None):
    font_size = max(18, round(width * 0.061))
    if margin_v is None:
        margin_v = round(height * 0.115) if height > width else round(height * 0.08)
    margin_h = round(width * 0.055)
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,&H00151515,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    def ass_time(text):
        value = timestamp(text)
        centiseconds = round(value * 100)
        h, rest = divmod(centiseconds, 360000)
        m, rest = divmod(rest, 6000)
        s, cs = divmod(rest, 100)
        return f'{h}:{m:02}:{s:02}.{cs:02}'
    dialogues = []
    for block in re.split(r'\n\s*\n', content.strip()):
        lines = block.splitlines()
        if len(lines) >= 3:
            a, b = lines[1].split('-->')
            text = r'\N'.join(lines[2:])
            dialogues.append(f'Dialogue: 0,{ass_time(a.strip())},{ass_time(b.strip())},Default,,0,0,0,,{text}')
    return header + '\n'.join(dialogues) + '\n'
