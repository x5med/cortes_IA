import json
import logging
import os
import secrets
import threading
import uuid
import time
import hmac
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from .models import Brief, Feedback, RenderRequest, Segment, TranscriptRequest
from .strategy import ROOT, analyze, validate_transcript
from .media import parse_transcript, render, transcribe, clip_filename
from .codex_engine import chatgpt_status

load_dotenv(ROOT / '.env')
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
POOL = ThreadPoolExecutor(max_workers=2)
LOCK = threading.RLock()
ACTIVE = set()
MEDIA_SECRET = secrets.token_bytes(32)
BEARER = HTTPBearer(auto_error=False)


def auth(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(BEARER)):
    token = os.getenv('CORTES_API_TOKEN', '')
    if token:
        if not credentials or not secrets.compare_digest(credentials.credentials, token):
            raise HTTPException(401, 'Chave de acesso inválida.')
    elif not request.client or request.client.host not in ('127.0.0.1', '::1', 'localhost', 'testclient'):
        raise HTTPException(403, 'Acesso remoto exige CORTES_API_TOKEN.')


def folder(project_id):
    try:
        normalized = str(uuid.UUID(project_id))
    except ValueError:
        raise HTTPException(404, 'Projeto não encontrado.')
    return DATA / normalized


def read(project_id):
    with LOCK:
        path = folder(project_id) / 'project.json'
        if not path.exists():
            raise HTTPException(404, 'Projeto não encontrado.')
        return json.loads(path.read_text(encoding='utf-8'))


def save(project):
    with LOCK:
        path = folder(project['id']) / 'project.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding='utf-8')
        # Windows can briefly deny replacement while another process/player polls.
        for attempt in range(8):
            try:
                temp.replace(path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.025 * (attempt + 1))


def update(project_id, **changes):
    with LOCK:
        project = read(project_id)
        project.update(changes)
        save(project)


def create(title, segments=None):
    project = {'id': str(uuid.uuid4()), 'title': title, 'status': 'pronto', 'message': 'Pronto para analisar',
               'segments': [s.model_dump() for s in segments or []], 'clips': [], 'video': None, 'feedback': []}
    folder(project['id']).mkdir()
    save(project)
    return project


def enqueue(project_id, task, message):
    with LOCK:
        if project_id in ACTIVE:
            raise HTTPException(409, 'Este projeto já está processando uma tarefa.')
        ACTIVE.add(project_id)
        update(project_id, status='processando', message=message)
    def work():
        try:
            task()
            update(project_id, status='pronto', message='Processamento concluído')
        except Exception as exc:
            logging.exception('Falha no projeto %s', project_id)
            # API errors can carry sensitive request metadata: only expose known local errors.
            message = str(exc) if isinstance(exc, ValueError) else 'Falha no serviço. Consulte o log local e tente novamente.'
            update(project_id, status='erro', message=message)
        finally:
            with LOCK:
                ACTIVE.discard(project_id)
    POOL.submit(work)


@asynccontextmanager
async def lifespan(app):
    for path in DATA.glob('*/project.json'):
        project = json.loads(path.read_text(encoding='utf-8'))
        if project['status'] == 'processando':
            update(project['id'], status='erro', message='Tarefa interrompida. Execute novamente.')
    yield


app = FastAPI(title='Cortes IA', version='0.2.0', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.get('/', include_in_schema=False)
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/health', operation_id='health')
def health():
    status = chatgpt_status()
    return {'ok': True, 'codex': status, 'transcription': 'local', 'paid_api': False,
            'auth_required': bool(os.getenv('CORTES_API_TOKEN'))}


@app.get('/api/projects', dependencies=[Depends(auth)], operation_id='listProjects')
def projects():
    return [{k: p[k] for k in ('id', 'title', 'status', 'message')} for path in DATA.glob('*/project.json')
            for p in [json.loads(path.read_text(encoding='utf-8'))]]


@app.post('/api/transcripts', dependencies=[Depends(auth)], operation_id='createTranscript')
def transcript(body: TranscriptRequest):
    try:
        validate_transcript(body.segments)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return create(body.title, body.segments)


@app.post('/api/upload', dependencies=[Depends(auth)], operation_id='uploadVideo')
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ('.mp4', '.mov', '.mkv', '.webm', '.srt', '.json'):
        raise HTTPException(422, 'Formatos aceitos: MP4, MOV, MKV, WEBM, SRT e JSON.')
    if suffix in ('.srt', '.json'):
        content = await file.read(10_000_001)
        if len(content) > 10_000_000:
            raise HTTPException(413, 'Transcrição excede 10 MB.')
        try:
            rows = parse_transcript(content.decode('utf-8-sig'), suffix)
            if not rows:
                raise ValueError('Transcrição vazia.')
            return create(Path(file.filename).stem[:200], rows)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, str(exc))
    project = create(Path(file.filename).stem[:200])
    target = folder(project['id']) / ('source' + suffix)
    size = 0
    with target.open('wb') as stream:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 4 * 1024**3:
                update(project['id'], status='erro', message='Vídeo excede 4 GB.')
                stream.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, 'Vídeo excede 4 GB.')
            stream.write(chunk)
    update(project['id'], video=target.name, message='Vídeo recebido. Transcreva para continuar.')
    return read(project['id'])


@app.get('/api/projects/{project_id}', dependencies=[Depends(auth)], operation_id='getProject')
def project(project_id: str):
    return read(project_id)


@app.post('/api/projects/{project_id}/transcribe', dependencies=[Depends(auth)], operation_id='transcribeProject')
def transcription(project_id: str):
    p = read(project_id)
    if not p['video']:
        raise HTTPException(422, 'Projeto sem vídeo.')
    def task():
        rows = transcribe(folder(project_id) / p['video'], lambda msg: update(project_id, message=msg))
        update(project_id, segments=[s.model_dump() for s in rows], clips=[])
    enqueue(project_id, task, 'Preparando áudio')
    return {'project_id': project_id, 'status': 'processando'}


@app.post('/api/projects/{project_id}/analyze', dependencies=[Depends(auth)], operation_id='analyzeProject')
def analysis(project_id: str, brief: Brief):
    p = read(project_id)
    if not p['segments']:
        raise HTTPException(422, 'Importe uma transcrição ou transcreva o vídeo primeiro.')
    if brief.mode == 'codex':
        status = chatgpt_status()
        if not status['chatgpt_authenticated']:
            raise HTTPException(422, status['message'])
    def task():
        clips = analyze([Segment(**s) for s in p['segments']], brief, lambda msg: update(project_id, message=msg))
        update(project_id, clips=clips, brief=brief.model_dump())
    enqueue(project_id, task, 'Selecionando cortes')
    return {'project_id': project_id, 'status': 'processando'}


@app.post('/api/projects/{project_id}/clips/{clip_id}/render', dependencies=[Depends(auth)], operation_id='renderClip')
def export(project_id: str, clip_id: str, options: RenderRequest):
    p = read(project_id)
    clip = next((c for c in p['clips'] if c['id'] == clip_id), None)
    if not clip:
        raise HTTPException(404, 'Corte não encontrado.')
    if not p['video']:
        raise HTTPException(422, 'Projeto sem vídeo para exportar.')
    if not options.confirmed:
        raise HTTPException(422, 'Revise o intervalo no vídeo e confirme antes de exportar.')
    def task():
        captions = clip.get('caption_segments', p['segments'])
        render(folder(project_id) / p['video'], clip, [Segment(**s) for s in captions], options, folder(project_id)/'exports')
        current = read(project_id)
        for c in current['clips']:
            if c['id'] == clip_id:
                c['exported'] = True
                c['export_format'] = options.format
                c['export_subtitles'] = options.subtitles
                c['export_crop_x'] = options.crop_x
                c['export_follow_face'] = options.follow_face
        save(current)
    enqueue(project_id, task, 'Exportando corte')
    return {'project_id': project_id, 'status': 'processando'}


@app.post('/api/projects/{project_id}/media-url', dependencies=[Depends(auth)], include_in_schema=False)
def media_url(project_id: str):
    read(project_id)
    expires = int(time.time()) + 8 * 3600
    signature = hmac.new(MEDIA_SECRET, f'{project_id}:{expires}'.encode(), hashlib.sha256).hexdigest()
    return {'url': f'/api/projects/{project_id}/video?expires={expires}&signature={signature}'}


@app.get('/api/projects/{project_id}/video', include_in_schema=False)
def video(project_id: str, expires: int, signature: str):
    expected = hmac.new(MEDIA_SECRET, f'{project_id}:{expires}'.encode(), hashlib.sha256).hexdigest()
    if expires < time.time() or not secrets.compare_digest(signature, expected):
        raise HTTPException(403, 'Link de vídeo inválido ou expirado.')
    p = read(project_id)
    if not p['video']:
        raise HTTPException(404, 'Sem vídeo.')
    return FileResponse(folder(project_id) / p['video'])


@app.get('/api/projects/{project_id}/clips/{clip_id}/download', dependencies=[Depends(auth)], operation_id='downloadClip')
def download(project_id: str, clip_id: str, kind: str = 'mp4'):
    p = read(project_id)
    if kind not in ('mp4', 'srt') or not any(c['id'] == clip_id for c in p['clips']):
        raise HTTPException(404, 'Arquivo não encontrado.')
    clip = next(c for c in p['clips'] if c['id'] == clip_id)
    name = clip_filename(clip, kind)
    path = folder(project_id) / 'exports' / name
    if not path.exists():
        path = folder(project_id) / 'exports' / f'{clip_id}.{kind}'
    if not path.exists() or not any(c.get('exported') for c in p['clips'] if c['id'] == clip_id):
        raise HTTPException(404, 'Exporte o corte primeiro.')
    return FileResponse(path, filename=name)


@app.post('/api/projects/{project_id}/clips/{clip_id}/feedback', dependencies=[Depends(auth)], operation_id='recordFeedback')
def feedback(project_id: str, clip_id: str, body: Feedback):
    with LOCK:
        p = read(project_id)
        clip = next((c for c in p['clips'] if c['id'] == clip_id), None)
        if not clip:
            raise HTTPException(404, 'Corte não encontrado.')
        clip['approved'] = body.decision == 'aprovado'
        p['feedback'].append({'clip_id': clip_id, 'clip_snapshot': dict(clip), **body.model_dump()})
        save(p)
    return {'saved': True, 'automatic_training': False}
