"""Portable, read-only setup diagnostics. Never prints credentials."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.codex_engine import chatgpt_status
import imageio_ffmpeg

print('Python:', sys.version.split()[0])
print('FFmpeg:', 'disponível' if Path(imageio_ffmpeg.get_ffmpeg_exe()).is_file() else 'não encontrado')
status=chatgpt_status()
print('Codex:', status['message'])
try:
    import av
    import ctranslate2
    import cv2
    assert hasattr(cv2, 'CascadeClassifier')
    print('Transcrição local: bibliotecas disponíveis; modelo baixado no primeiro uso.')
except (ImportError, OSError) as exc:
    print('Transcrição local: falha ao carregar dependências:', exc)
    sys.exit(1)
print('API paga: desativada. A análise usa os limites da assinatura ChatGPT conectada ao Codex.')
