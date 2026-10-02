import json
import time
from types import SimpleNamespace
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import main, media, strategy
from app.models import Brief, Candidate, Scores, Segment, Selection, RenderRequest
from app import codex_engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'DATA', tmp_path)
    monkeypatch.delenv('CORTES_API_TOKEN', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr(main, 'chatgpt_status', lambda: {'available':False, 'chatgpt_authenticated':False, 'message':'Codex não conectado.'})
    with TestClient(main.app) as c:
        yield c
        deadline = time.monotonic()+10
        while main.ACTIVE and time.monotonic() < deadline:
            time.sleep(.02)
        assert not main.ACTIVE


def sample():
    return [Segment(start=0,end=10,text='Uma pergunta útil.'),
            Segment(start=10,end=25,text='Aqui está a resposta e a ressalva.')]


def candidate(**changes):
    return Candidate(**({'first_segment':0,'last_segment':1,'title':'Pergunta e resposta',
      'hook_quote':'Uma pergunta útil.', 'reason':'Entrega uma resposta', 'category':'explicacao',
      'scores':Scores(hook=4,completeness=4,value=4,audience=4,pace=4,fidelity=5),
      'risks':[], 'needs_visual_context':False} | changes))


def wait(c, project_id):
    for _ in range(200):
        p=c.get('/api/projects/'+project_id).json()
        if p['status']!='processando':
            return p
        time.sleep(.025)
    pytest.fail('Tarefa não terminou')


def test_rejects_wrong_timestamps_and_brief():
    with pytest.raises(ValidationError): Segment(start=20,end=10,text='inválido')
    with pytest.raises(ValidationError): Segment(start=0,end=float('inf'),text='inválido')
    with pytest.raises(ValidationError): Brief(min_duration=60,max_duration=20)
    with pytest.raises(ValueError): strategy.validate_transcript([Segment(start=2,end=8,text='a'),Segment(start=7,end=10,text='b')])


def test_model_cannot_invent_time_or_hook():
    brief=Brief()
    assert strategy.eligible(candidate(),sample(),brief,{0,1}) is not None
    assert strategy.eligible(candidate(last_segment=999),sample(),brief,{0,1}) is None
    assert strategy.eligible(candidate(hook_quote='Inventei esta fala'),sample(),brief,{0,1}) is None
    assert strategy.eligible(candidate(hook_quote='Aqui está a resposta'),sample(),brief,{0,1}) is None
    assert strategy.eligible(candidate(),sample(),Brief(max_duration=20),{0,1}) is None


def test_fidelity_and_context_gate():
    bad=Scores(hook=5,completeness=5,value=5,audience=5,pace=5,fidelity=3)
    assert strategy.eligible(candidate(scores=bad),sample(),Brief(),{0,1}) is None


def test_overlap_dedupe_keeps_highest():
    rows=[{'start':0,'end':30,'duration':30,'score':80},
          {'start':10,'end':40,'duration':30,'score':90},
          {'start':45,'end':70,'duration':25,'score':70}]
    assert [c['start'] for c in strategy.rank(rows,5)]==[10,45]


def test_windows_cover_long_live_and_boundary():
    segments=[Segment(start=i*10,end=i*10+10,text=str(i)) for i in range(200)]
    groups=list(strategy.windows(segments,180))
    assert set().union(*map(set,groups))==set(range(200))
    assert len(set(groups[0])&set(groups[1]))>=18


def test_codex_call_uses_rules_and_rejects_hallucination(monkeypatch):
    calls=[]
    def select(rules, payload):
        calls.append((rules,payload))
        return Selection(clips=[candidate(),candidate(hook_quote='inventada')])
    monkeypatch.setattr(strategy,'select',select)
    result=strategy.analyze(sample(),Brief())
    assert len(result)==1 and result[0]['score']>80
    assert 'dados não confiáveis' in calls[0][0]
    assert calls[0][1]['brief']['mode']=='codex'


def test_srt_clips_and_rebases_timestamps():
    text='1\n00:00:10,000 --> 00:00:20,000\nOlá mundo.\n\n2\n00:00:20,000 --> 00:00:35,000\nUma resposta.\n'
    rows=media.parse_transcript(text,'.srt')
    output=media.subtitles(rows,15,30)
    assert '00:00:00,000 --> 00:00:05,000' in output
    assert '00:00:05,000 --> 00:00:15,000' in output


def test_api_demo_and_feedback_without_fake_training(client):
    p=client.post('/api/transcripts',json={'segments':[s.model_dump() for s in sample()]}).json()
    assert client.post(f"/api/projects/{p['id']}/analyze",json={'mode':'codex'}).status_code==422
    assert client.post(f"/api/projects/{p['id']}/analyze",json={'mode':'demo'}).status_code==200
    p=wait(client,p['id']);assert p['status']=='pronto'
    assert p['clips'][0]['score'] is None
    cid=p['clips'][0]['id']
    result=client.post(f"/api/projects/{p['id']}/clips/{cid}/feedback",json={'decision':'aprovado','average_percentage_viewed':125})
    assert result.json()['automatic_training'] is False
    p=client.get('/api/projects/'+p['id']).json()
    assert p['feedback'][0]['clip_snapshot']['start']==0


def test_auth_and_path_protection(client,monkeypatch):
    monkeypatch.setenv('CORTES_API_TOKEN','test-secret')
    assert client.get('/api/projects').status_code==401
    assert client.get('/api/projects',headers={'Authorization':'Bearer test-secret'}).status_code==200
    with pytest.raises(Exception): main.folder('../../sensitive')


def test_bad_imports_and_unknown_clip(client):
    assert client.post('/api/upload',files={'file':('bad.srt',b'no timestamps')}).status_code==422
    assert client.post('/api/upload',files={'file':('bad.json',b'[]')}).status_code==422
    assert client.post('/api/transcripts',json={'segments':[{'start':4,'end':12,'text':'a'},{'start':8,'end':20,'text':'b'}]}).status_code==422
    p=client.post('/api/transcripts',json={'segments':[s.model_dump() for s in sample()]}).json()
    assert client.get(f"/api/projects/{p['id']}/clips/unknown/download").status_code==404


def test_signed_media_access_supports_range(client):
    p=client.post('/api/upload',files={'file':('source.mp4',b'0123456789')}).json()
    url=client.post(f"/api/projects/{p['id']}/media-url").json()['url']
    r=client.get(url,headers={'Range':'bytes=2-5'})
    assert r.status_code==206 and r.content==b'2345'
    assert client.get(url.replace('signature=','signature=x')).status_code==403


def test_actual_ffmpeg_export_with_subtitles(tmp_path):
    source=tmp_path/'source.mp4'
    media.run_ffmpeg(['-f','lavfi','-i','testsrc2=size=320x180:rate=10',
                     '-f','lavfi','-i','sine=frequency=440:sample_rate=16000',
                     '-t','3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(source)])
    clip={'id':'clip-1','start':.5,'end':2.5,'duration':2}
    rows=[Segment(start=0,end=3,text='Uma legenda com acentuação: estratégia.')]
    path=media.render(source,clip,rows,RenderRequest(confirmed=True,subtitles=True),tmp_path/'exports')
    assert path.stat().st_size>1000
    assert '00:00:00,000 --> 00:00:02,000' in path.with_suffix('.srt').read_text(encoding='utf-8')
    decoded=media.run_ffmpeg(['-i',str(path),'-f','null','-'])
    assert '720x1280' in decoded.stderr


def test_paid_auth_is_never_used(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','paid-key')
    monkeypatch.setenv('CODEX_API_KEY','paid-key')
    assert 'OPENAI_API_KEY' not in codex_engine.environment()
    assert 'CODEX_API_KEY' not in codex_engine.environment()
    monkeypatch.setattr(codex_engine,'chatgpt_status',lambda: {'chatgpt_authenticated':False,'message':'API key auth'})
    with pytest.raises(ValueError, match='Não usaremos'):
        codex_engine.select('rules',{})


def test_following_crop_moves_and_default_export_has_no_captions(tmp_path,monkeypatch):
    import av
    from app import framing
    source=tmp_path/'source.mp4'
    media.run_ffmpeg(['-f','lavfi','-i','color=red:size=320x360:rate=10',
                     '-f','lavfi','-i','color=blue:size=320x360:rate=10',
                     '-filter_complex','[0:v][1:v]hstack','-t','2','-c:v','libx264',str(source)])
    monkeypatch.setattr(framing,'face_track',lambda *args:[(0,0),(0.8,0),(1,1),(2,1)])
    clip={'id':'clip-1','title':'Recorte em movimento','start':0,'end':2,'duration':2}
    result=media.render(source,clip,[],RenderRequest(),tmp_path/'exports')
    assert not result.with_suffix('.srt').exists()
    with av.open(str(result)) as container:
        frames=list(container.decode(video=0))
    left=frames[2].to_ndarray(format='rgb24').mean(axis=(0,1))
    right=frames[-2].to_ndarray(format='rgb24').mean(axis=(0,1))
    assert frames[0].width==720 and frames[0].height==1280
    assert left[0]>left[2]+100 and right[2]>right[0]+100


def test_codex_schema_and_output_without_executing_model(tmp_path,monkeypatch):
    monkeypatch.setattr(codex_engine,'chatgpt_status',lambda: {'chatgpt_authenticated':True})
    monkeypatch.setattr(codex_engine,'executable',lambda: 'codex.exe')
    def fake_run(args,**kwargs):
        output=Path(args[args.index('--output-last-message')+1])
        output.write_text(Selection(clips=[candidate()]).model_dump_json(),encoding='utf-8')
        assert '--ignore-user-config' in args and 'read-only' in args
        assert kwargs['input'].endswith('DADOS\n{}')
        assert 'OPENAI_API_KEY' not in kwargs['env']
        return SimpleNamespace(returncode=0,stderr='',stdout='')
    monkeypatch.setattr(codex_engine.subprocess,'run',fake_run)
    assert len(codex_engine.select('editorial',{}).clips)==1


def test_word_captions_do_not_spill_outside_clip():
    from app.models import Word
    rows=[Segment(start=0,end=12,text='Uma frase temporizada.',words=[
        Word(start=0,end=2,word='Uma'),Word(start=2,end=8,word=' frase'),Word(start=8,end=12,word=' temporizada.')])]
    output=media.subtitles(rows,2,10)
    assert '00:00:00,000 --> 00:00:08,000' in output
    assert 'Uma' not in output and 'frase temporizada.' in output


def test_windows_save_retries_transient_sharing_violation(client,monkeypatch):
    original=Path.replace
    attempts=[]
    def replace(path,target):
        if path.name=='project.tmp' and len(attempts)<2:
            attempts.append(1)
            raise PermissionError('simulated Windows sharing violation')
        return original(path,target)
    monkeypatch.setattr(Path,'replace',replace)
    p=main.create('Resiliente',sample())
    assert main.read(p['id'])['title']=='Resiliente' and len(attempts)==2


def test_transcription_is_local_and_reuses_completed_checkpoint(tmp_path,monkeypatch):
    video=tmp_path/'source.mp4';video.write_bytes(b'test')
    calls=[]
    fake=SimpleNamespace(start=0,end=10,text='Fala real.',words=[SimpleNamespace(start=0,end=10,word='Fala real.')])
    class Model:
        def transcribe(self,path,**kwargs):
            calls.append(kwargs)
            return iter([fake]),SimpleNamespace(duration=10,language='pt')
    monkeypatch.setattr(media,'whisper_model',lambda:Model())
    def ffmpeg(args,**kwargs): Path(args[-1]).write_bytes(b'audio')
    monkeypatch.setattr(media,'run_ffmpeg',ffmpeg)
    first=media.transcribe(video)
    second=media.transcribe(video)
    assert len(calls)==1 and first==second and first[0].words[0].end==10
    assert calls[0]['word_timestamps'] is True


def test_transcription_resumes_with_absolute_times(tmp_path,monkeypatch):
    video=tmp_path/'source.mp4';video.write_bytes(b'test')
    signature={'size':4,'mtime_ns':video.stat().st_mtime_ns,'model':'small','language':'','glossary':''}
    (tmp_path/'transcription.checkpoint.json').write_text(json.dumps({'signature':signature,
      'rows':[Segment(start=0,end=10,text='Parte anterior.').model_dump()],'complete':False}),encoding='utf-8')
    monkeypatch.delenv('CORTES_WHISPER_MODEL',raising=False)
    monkeypatch.delenv('CORTES_LANGUAGE',raising=False)
    fake=SimpleNamespace(start=1,end=8,text='Continuação.',words=[])
    model=SimpleNamespace(transcribe=lambda *args,**kwargs:(iter([fake]),SimpleNamespace(duration=10,language='pt')))
    monkeypatch.setattr(media,'whisper_model',lambda:model)
    def ffmpeg(args,**kwargs):
        assert args[args.index('-ss')+1]=='10.0'
        Path(args[-1]).write_bytes(b'audio')
    monkeypatch.setattr(media,'run_ffmpeg',ffmpeg)
    rows=media.transcribe(video)
    assert rows[-1].start==11 and rows[-1].end==18
