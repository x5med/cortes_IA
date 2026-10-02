# Verificação da versão 0.2

Teste em 2 de outubro de 2026, Windows, Python 3.14. Transcrição local e `codex exec` autenticado no ChatGPT, sem chave de API paga.

## Live real

Arquivo fornecido: `videoplayback.mp4`, 14min27s, 640×360, áudio AAC. Transcrição completa com Whisper small: 260,5s na execução concluída. Seleção real com Codex: 84,9s. Esses tempos excluem instalação, download inicial e tentativas interrompidas.

Brief: até cinco cortes de 25–75s para médicos proprietários e gestores de clínicas. Foram retornados três candidatos válidos:

| Corte | Intervalo na live | Duração |
|---|---|---|
| Antes de investir em tráfego, encontre o gargalo da clínica | 02:54,43–03:46,61 | 52,18s |
| Baixa conversão: investigue antes de culpar a secretária | 06:42,80–07:23,64 | 40,84s |
| Como identificar o gargalo da sua clínica | 09:34,90–10:32,98 | 58,08s |

Recomendação inicial: revisar o primeiro corte, por seu caso concreto de duas unidades e conclusão aplicável. O segundo preserva a incerteza antes de culpar a recepção. O terceiro enumera pilares e tem caráter promocional, com menção ao evento, embora não inclua datas. Notas do modelo indicam prioridade editorial; não medem desempenho com público.

O recorte central 9:16 foi rejeitado na inspeção de quadros porque o apresentador se inclina e parte do rosto fica fora da imagem. As prévias verticais preservam o quadro completo com bordas. Os cortes principais mantêm a proporção original e não queimam legendas não verificadas.

Whisper small confundiu palavras de negócio. Uma segunda transcrição dos trechos usa Whisper medium e glossário de domínio. Ainda há confusões, inclusive no termo lead. SRT e prévias legendadas são materiais para revisão, não versões aprovadas para publicar. Nenhum corte foi marcado como aprovado pelo usuário.

## Verificações

- 18 testes passaram: seleção, citações e tempos, fidelidade, duplicação, autenticação, mídia parcial, exportação sintética FFmpeg, legendas, persistência Windows, transcrição local, cache e retomada.
- Login do Codex confirmado como ChatGPT; health check informa transcrição local e `paid_api=false`.
- MCP real via stdio: cinco ferramentas descobertas e consulta de projetos funcionando.
- Projeto real carregado no Chrome com brief restaurado, três candidatos e downloads MP4/SRT.
- Seis MP4 reais (três originais e três prévias verticais) foram decodificados sem erro; todos têm áudio. Downloads dos três cortes originais responderam com HTTP 206 ao teste de leitura parcial.

O registro de decodificação e dimensões da mídia real fica em `data/<id-do-projeto>/test-results.json`, criado por `scripts/verify_live.py`. Vídeo e dados da live ficam fora do Git e do pacote.

Não verificado: retenção/alcance, instalação em segundo computador, instalação do plugin no cliente, Actions HTTPS e criação de GPT na conta. A portabilidade foi preparada como pacote de código e instalação; cada computador precisa de Python, dependências e login autorizado do Codex. A análise permanece sujeita aos limites da conta existente.

Resultado: protótipo funcional com seleção estratégica real. Revisar fala, limites do corte e legendas continua necessário. A fonte 360p limita a imagem, mesmo exportando prévias em 720×1280.

## Ajuste de enquadramento e legendas

Na segunda live, videoplayback (1), os cinco cortes foram reexportados em 720×1280, sem padding preto e sem legendas queimadas. O recorte acompanha a posição horizontal do rosto, detectado localmente pelo OpenCV, inclusive com tentativa de detecção da cabeça inclinada. Inspeção de quadros no início, meio e fim; decodificação dos cinco arquivos completos. O player oferece prévia do recorte fixo; o acompanhamento ocorre na exportação.

19 testes passaram, incluindo vídeo sintético que verifica o movimento real do recorte via comandos FFmpeg e ausência de SRT no padrão sem legendas. A transcrição continua sendo usada internamente para selecionar os cortes, mas não é inserida no MP4.
