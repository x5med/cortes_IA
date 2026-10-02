# Conectar ao ChatGPT

Esta pasta é um pacote de configuração opcional, não um GPT já instalado na conta. Para usar sem nova contratação, prefira a instalação local por `start.cmd`: transcrição local e análise pelo Codex conectado ao ChatGPT, sem hospedagem pública. Cada computador instala sua própria cópia.

1. Execute e hospede o backend com HTTPS estável, armazenamento persistente e CORTES_API_TOKEN forte. O endereço local 127.0.0.1 serve para testar no computador, mas não pode ser chamado pelo ChatGPT na web.
2. Defina CORTES_PUBLIC_URL para o endereço real e execute `python scripts/export_actions.py` novamente. O schema gerado usa o endereço configurado e aponta para o mesmo backend.
3. No editor de GPTs, configure o nome **Cortes IA**, copie `instructions.md` para Instruções e carregue `knowledge/editor.md` e `docs/pesquisa.md` em Conhecimento. Esses arquivos também estão nesta pasta como cópias para upload.
4. Em Actions, importe `openapi.json`. Configure autenticação API Key / Bearer com CORTES_API_TOKEN. Esse token protege o servidor Cortes IA; não é chave de cobrança da OpenAI. O servidor deve ter Codex instalado e autenticado pelo ChatGPT. Não exponha a conta pessoal como serviço para terceiros.
5. Teste listar projetos, selecionar um projeto, analisar e consultar status. Teste exportação depois de revisar um corte real. Publique no ChatGPT somente depois dessa verificação.

Actions não oferecem upload automático dos anexos da conversa para este serviço. O usuário envia vídeos pela interface web; o GPT opera os projetos já disponíveis. O acesso desta versão é para um único estúdio com token compartilhado. Antes de atender múltiplos clientes, implemente autenticação individual, isolamento de dados, quotas, política de privacidade e filas duráveis.

Também há um plugin local em `plugin/cortes-ia`, com MCP via stdio para clientes desktop compatíveis. Ele requer o servidor web em execução, Python disponível e as dependências do projeto. Instalação em uma conta ou conexão no editor de GPTs não foi realizada automaticamente.

Referências: [GPT Actions](https://developers.openai.com/api/docs/actions/introduction), [autenticação](https://developers.openai.com/api/docs/actions/authentication).
