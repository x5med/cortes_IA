"""Selection with evidence validation and configurable editorial hypotheses."""
import json
import os
from pathlib import Path
from .codex_engine import select
from .models import Brief, Candidate, Scores, Segment, Selection

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {'hook': 20, 'completeness': 20, 'value': 20, 'audience': 15, 'pace': 10, 'fidelity': 15}


def score(scores: Scores) -> float:
    return round(sum(getattr(scores, key) / 5 * weight for key, weight in WEIGHTS.items()), 1)


def validate_transcript(segments: list[Segment]) -> list[Segment]:
    previous_end = 0.0
    for s in segments:
        if s.start < previous_end - 0.05:
            raise ValueError('Segmentos devem estar em ordem e não podem se sobrepor.')
        previous_end = s.end
    return segments


def windows(segments: list[Segment], max_duration: int):
    # 10-minute windows with enough overlap for a full clip at a boundary.
    i = 0
    while i < len(segments):
        end = i + 1
        while end < len(segments) and segments[end].end - segments[i].start <= 600:
            end += 1
        yield list(range(i, end))
        if end == len(segments):
            break
        boundary = segments[end - 1].end - max_duration
        nxt = i + 1
        while nxt < end and segments[nxt].start < boundary:
            nxt += 1
        i = nxt


def eligible(candidate: Candidate, segments: list[Segment], brief: Brief, allowed: set[int]):
    a, b = candidate.first_segment, candidate.last_segment
    if a > b or any(i not in allowed for i in range(a, b + 1)):
        return None
    selected = segments[a:b + 1]
    start, end = selected[0].start, selected[-1].end
    if not brief.min_duration <= end - start <= brief.max_duration:
        return None
    text = ' '.join(s.text for s in selected)
    normalize = lambda x: ' '.join(x.lower().split())
    if not candidate.hook_quote.strip() or normalize(candidate.hook_quote) not in normalize(selected[0].text):
        return None
    if candidate.scores.fidelity < 4 or candidate.scores.completeness < 3:
        return None
    return {**candidate.model_dump(), 'start': start, 'end': end, 'duration': round(end-start, 3),
            'transcript': text, 'score': score(candidate.scores), 'approved': False,
            'review_required': True}


def rank(candidates: list[dict], count: int) -> list[dict]:
    result = []
    for item in sorted(candidates, key=lambda x: x['score'], reverse=True):
        if any(max(0, min(item['end'], old['end']) - max(item['start'], old['start'])) /
               min(item['duration'], old['duration']) > 0.35 for old in result):
            continue
        result.append({**item, 'id': f'clip-{len(result)+1}'})
        if len(result) == count:
            break
    return result


def demo_selection(segments: list[Segment], brief: Brief):
    # Deliberately no pretend semantic scores: this is a timing-only smoke test.
    result = []
    i = 0
    while i < len(segments) and len(result) < brief.count:
        j = i
        while j < len(segments) and segments[j].end - segments[i].start < brief.min_duration:
            j += 1
        if j < len(segments) and segments[j].end - segments[i].start <= brief.max_duration:
            result.append({'id': f'clip-{len(result)+1}', 'start': segments[i].start, 'end': segments[j].end,
                           'duration': segments[j].end-segments[i].start, 'title': 'Exemplo técnico de corte',
                           'hook_quote': segments[i].text, 'transcript': ' '.join(s.text for s in segments[i:j+1]),
                           'reason': 'Demonstração por duração. A estratégia exige o modo GPT.',
                           'category': 'explicacao', 'scores': None, 'score': None,
                           'risks': ['Exemplo sem análise semântica'], 'needs_visual_context': True,
                           'review_required': True, 'approved': False})
            i = j + 1
        else:
            i += 1
    return result


def analyze(segments: list[Segment], brief: Brief, progress=lambda _: None):
    validate_transcript(segments)
    if brief.mode == 'demo':
        return demo_selection(segments, brief)
    rules = (ROOT / 'knowledge' / 'editor.md').read_text(encoding='utf-8')
    candidates = []
    groups = list(windows(segments, brief.max_duration))
    for n, ids in enumerate(groups):
        progress(f'Analisando bloco {n+1}/{len(groups)}')
        response = select(rules, {
            'brief': brief.model_dump(), 'segments': [
                {'id': i, 'start': segments[i].start, 'end': segments[i].end, 'text': segments[i].text} for i in ids]})
        for candidate in response.clips:
            item = eligible(candidate, segments, brief, set(ids))
            if item:
                candidates.append(item)
    return rank(candidates, brief.count)
