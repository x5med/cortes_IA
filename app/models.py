from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Word(StrictModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    word: str


class Segment(StrictModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=10000)
    words: list[Word] = Field(default_factory=list)

    @model_validator(mode='after')
    def ordered(self):
        if self.end <= self.start:
            raise ValueError('O fim deve ser maior que o início.')
        return self


class Brief(StrictModel):
    audience: str = Field(default='Pessoas interessadas no tema da live', max_length=1000)
    goal: Literal['alcance', 'autoridade', 'conversao', 'comunidade'] = 'alcance'
    platform: Literal['shorts', 'reels', 'tiktok'] = 'shorts'
    min_duration: int = Field(default=20, ge=5, le=180)
    max_duration: int = Field(default=60, ge=5, le=180)
    count: int = Field(default=5, ge=1, le=20)
    mode: Literal['codex', 'demo'] = 'codex'

    @model_validator(mode='after')
    def durations(self):
        if self.max_duration < self.min_duration:
            raise ValueError('Duração máxima menor que a mínima.')
        return self


class Scores(StrictModel):
    hook: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    value: int = Field(ge=0, le=5)
    audience: int = Field(ge=0, le=5)
    pace: int = Field(ge=0, le=5)
    fidelity: int = Field(ge=0, le=5)


class Candidate(StrictModel):
    first_segment: int = Field(ge=0)
    last_segment: int = Field(ge=0)
    title: str
    hook_quote: str
    reason: str
    category: Literal['historia', 'explicacao', 'opiniao', 'humor', 'dica']
    scores: Scores
    risks: list[str]
    needs_visual_context: bool


class Selection(StrictModel):
    clips: list[Candidate]


class TranscriptRequest(StrictModel):
    title: str = Field(default='Minha live', max_length=200)
    segments: list[Segment] = Field(min_length=1, max_length=20000)


class RenderRequest(StrictModel):
    format: Literal['original', 'vertical_fit', 'vertical_crop'] = 'vertical_crop'
    subtitles: bool = False
    crop_x: float = Field(default=0.5, ge=0, le=1)
    follow_face: bool = True
    confirmed: bool = False


class Feedback(StrictModel):
    decision: Literal['aprovado', 'rejeitado']
    note: str = Field(default='', max_length=2000)
    platform: Literal['shorts', 'reels', 'tiktok'] = 'shorts'
    views: int | None = Field(default=None, ge=0)
    stayed_to_watch: float | None = Field(default=None, ge=0, le=100)
    average_percentage_viewed: float | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
