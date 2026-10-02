"""Local MCP bridge. API must already be running; no unrestricted file access."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
server = MCPServer('Cortes IA', instructions='Revise contexto antes de exportar. Notas não preveem viralização.')


def call(path, body=None):
    token = os.getenv('CORTES_API_TOKEN', '')
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    url = os.getenv('CORTES_SERVER_URL', 'http://127.0.0.1:8000') + path
    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=headers) if body is None else client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()


@server.tool()
def list_projects() -> list[dict]:
    """Listar lives recebidas pelo estúdio local."""
    return call('/api/projects')


@server.tool()
def get_project(project_id: str) -> dict:
    """Consultar processamento e cortes de uma live."""
    return call(f'/api/projects/{project_id}')


@server.tool()
def analyze_project(project_id: str, audience: str, goal: str = 'alcance', platform: str = 'shorts',
                    min_duration: int = 20, max_duration: int = 60, count: int = 5) -> dict:
    """Iniciar seleção estratégica GPT; consultar projeto até concluir."""
    return call(f'/api/projects/{project_id}/analyze', {'audience': audience, 'goal': goal, 'platform': platform,
        'min_duration': min_duration, 'max_duration': max_duration, 'count': count, 'mode': 'codex'})


@server.tool()
def transcribe_project(project_id: str) -> dict:
    """Iniciar transcrição de um vídeo já enviado ao estúdio."""
    return call(f'/api/projects/{project_id}/transcribe', {})


@server.tool()
def render_clip(project_id: str, clip_id: str, reviewed_by_user: bool = False,
                format: str = 'vertical_crop', subtitles: bool = False, crop_x: float = 0.5, follow_face: bool = True) -> dict:
    """Exportar corte somente depois de o usuário confirmar revisão audiovisual."""
    return call(f'/api/projects/{project_id}/clips/{clip_id}/render',
                {'format': format, 'subtitles': subtitles, 'crop_x': crop_x, 'follow_face': follow_face, 'confirmed': reviewed_by_user})


if __name__ == '__main__':
    server.run(transport='stdio')
