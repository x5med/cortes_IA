# Cortes IA

Gerador de cortes para Windows que usa **Codex conectado ao ChatGPT**, transcrição gratuita no computador e exportação local. Não usa API OpenAI paga e não exige nova assinatura.

## Instalar em outro computador

Baixe o [pacote para Windows na versão 0.2.0](https://github.com/x5med/cortes_IA/releases/download/v0.2.0/cortes-ia-windows.zip).

1. Instale Python 3.12 ou superior, 64 bits, marcando a opção de adicionar ao PATH.
2. Instale e conecte o Codex à conta ChatGPT que já tem acesso ao serviço. Para CLI, execute `codex login`; o aplicativo também procura o executável incluído no Codex desktop do Windows.
3. Extraia `cortes-ia-windows.zip` numa pasta própria e dê dois cliques em `start.cmd`. A primeira execução instala as bibliotecas gratuitas. Mantenha o terminal aberto enquanto usar o estúdio.
4. Abra http://127.0.0.1:8000. O indicador informa se o Codex está conectado. Envie o vídeo, transcreva no computador, defina a estratégia e selecione cortes.

Cada computador usa a conta autenticada localmente. Computadores com a mesma conta compartilham os limites dessa conta. Nenhuma credencial é incluída no ZIP. Internet é necessária para baixar o modelo gratuito na primeira transcrição e para as chamadas do Codex. Não há compra automática de créditos ou alternativa de API paga implementada; o consumo segue suas configurações e limites no ChatGPT.

Se o Codex não estiver no PATH nem na instalação desktop padrão, copie `.env.example` para `.env` e preencha `CORTES_CODEX_PATH` com o caminho do executável dessa máquina. Não é necessário informar chave OpenAI. Não copie o arquivo de autenticação do Codex entre computadores.

## Fluxo

- Importar MP4/MOV/MKV/WEBM ou SRT/JSON com tempos absolutos.
- Transcrever com faster-whisper, modelo small, CPU/int8. Idioma detectado automaticamente; palavras temporizadas para legendas em grupos curtos. O modelo fica no cache desse computador.
- Selecionar candidatos com `codex exec`, schema JSON e login ChatGPT existente. As instruções vêm de `knowledge/editor.md`. Tokens de API são removidos da chamada e autenticação por API key é rejeitada. A versão usa a configuração padrão do CLI, sem carregar integrações pessoais.
- Analisar todos os blocos de dez minutos com sobreposição, validar intervalos e citações e filtrar duplicações.
- Revisar no player e exportar em 9:16 preenchendo a tela, sem legendas. O acompanhamento local de um rosto ajusta a posição horizontal durante a exportação. Para recorte fixo, desmarque Acompanhar o rosto e posicione o controle horizontal; o player mostra essa prévia manual. Proporção original e quadro com bordas continuam como alternativas.
- MP4 e SRT recebem o padrão `01 - Título do corte`, com numeração de pelo menos dois dígitos. Acentos são preservados; caracteres incompatíveis com nomes de arquivo no Windows são removidos.
- Exportação usa Lanczos para redimensionar e H.264 CRF 17/preset medium para reduzir perdas de compressão. Isso não recupera detalhes ausentes da live. Para recorte vertical nítido, prefira a gravação original em 1080p ou superior; fontes 360p ficam ampliadas e perdem definição aparente.
- Registrar avaliações; feedback não treina o modelo automaticamente.

SRT importado usa tempos por segmento; vídeo transcrito localmente tem tempos estimados por palavra. Ambas as opções precisam de revisão de nomes e sentido. As legendas ficam desativadas no estúdio. O acompanhamento de rosto foi feito para um apresentador; falhas de detecção, mudanças de câmera e várias pessoas exigem revisão. O aplicativo não baixa links, não acompanha live em tempo real nem publica nas redes. Notas são prioridade editorial, não previsão de alcance.

Para priorizar precisão, configure `CORTES_WHISPER_MODEL=medium` no `.env` (download maior e processamento mais lento). `CORTES_LANGUAGE=pt` fixa o português; `CORTES_ASR_GLOSSARY` aceita termos do canal para orientar a transcrição. Isso reduz algumas confusões, mas não substitui a revisão das legendas.

JSON: lista de `{ "start": 0, "end": 8, "text": "Fala do apresentador" }`, ou objeto com chave `segments`. Tempos em segundos, em ordem e sem sobreposição. Exemplo em `static/example.json`.

## Pesquisa e integrações

`docs/pesquisa.md` reúne fontes, hipóteses, rubrica e avaliação. A estratégia é instrução e validação, não fine-tuning. `plugin/cortes-ia` contém MCP local para clientes compatíveis. `gpt` contém configuração de Actions como opção adicional, que requer servidor HTTPS. A instalação local usa apenas o computador e o Codex existente.

Comandos: `start.ps1` para iniciar pelo PowerShell; `python scripts/doctor.py` para diagnóstico; `python -m pytest -q` para testes; `python scripts/export_actions.py` para atualizar o contrato; `python scripts/package_app.py` para empacotar. Execute Python do ambiente `.venv`.

## Dados e execução

Vídeo, áudio e transcrição ficam em `data/`, ignorado pelo Git e pelo pacote. Somente o texto e o brief são enviados ao Codex para seleção. Cada instalação é independente; projetos não são sincronizados. Dois trabalhos simultâneos, transcritor serializado, fila em memória e persistência JSON: servidor único, sem múltiplos workers. Após reiniciar, tarefas interrompidas precisam ser iniciadas novamente.

O servidor inicia em localhost. Para acesso remoto, CORTES_API_TOKEN é obrigatório. Esta versão não tem autenticação individual nem isolamento de clientes e não deve ser exposta como serviço multiusuário.

Referências: [automação do Codex](https://learn.chatgpt.com/docs/non-interactive-mode), [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
