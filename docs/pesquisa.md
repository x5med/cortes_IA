# Base de pesquisa — Cortes IA

Pesquisa consultada em 2 de outubro de 2026. Priorizamos documentação das próprias plataformas. As fontes orientam decisões; não demonstram que uma fórmula garante distribuição. Fontes de anúncios são identificadas para evitar generalização indevida para lives orgânicas.

## 1. Retenção e contexto — YouTube

[Momentos importantes de retenção](https://support.google.com/youtube/answer/9314415?hl=en).

A curva permite investigar quedas, trechos estáveis e picos. Um pico pode indicar interesse, compartilhamento ou dificuldade de compreensão. O YouTube recomenda antecipar conteúdo interessante e alinhar a abertura à expectativa criada pelo título. A métrica de introdução citada nesse relatório considera os primeiros 30 segundos; isso não estabelece uma regra de abertura para Shorts.

Aplicação: procurar trechos que entregam a promessa do título e investigar picos com contexto. Nesta versão não importamos curvas de retenção: o motor usa a transcrição. Essa extensão exige dados reais do canal.

## 2. Medir Shorts corretamente — YouTube

[Entender o desempenho do conteúdo](https://support.google.com/youtube/answer/12220281?hl=en).

“Stayed to watch” descreve a proporção de vezes em que espectadores assistiram em vez de deslizar. Duração média e porcentagem média assistida, para Shorts, usam os espectadores que continuaram assistindo. São medidas com denominadores diferentes. Portanto, registramos as métricas em campos separados, sem sintetizar uma probabilidade de viralização.

Aplicação proposta: comparar cortes de mesmo canal, objetivo e duração semelhante; preservar a janela de observação e o volume da amostra. Views isoladas não provam qualidade nem causalidade. O aplicativo registra feedback, mas ainda não importa métricas automaticamente.

## 3. Gancho, estrutura e legibilidade — TikTok Ads

[Boas práticas de criativos de performance](https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en), atualizado em junho de 2025.

O guia recomenda vídeo vertical, cuidado com áreas cobertas pela interface, comunicação do valor cedo, gancho nos primeiros segundos e uso de legendas/contexto. Também sugere estrutura de gancho, desenvolvimento e fechamento, e testar criativos continuamente. Trata-se de orientação para anunciantes, não evidência de um limiar universal para cortes orgânicos.

Aplicação: exigir uma abertura relacionada à entrega, oferecer 9:16 e legendas. As margens da legenda são uma escolha inicial do produto, não certificação de área segura em todas as plataformas. Nesta versão o enquadramento preserva o quadro ou recorta o centro; não acompanha rostos.

## 4. Originalidade — Instagram / Meta

[Ajudando o criador a encontrar novos públicos](https://about.fb.com/br/news/2024/04/ajudando-o-criador-de-conteudo-a-encontrar-novos-publicos/), publicado em abril de 2024.

A Meta descreve priorização do original quando encontra conteúdo idêntico e mudanças para reduzir recomendação de agregadores. O texto também distingue transformações significativas. Isso não significa que apenas cortar ou legendar material de terceiros o torna original ou elegível.

Aplicação: trabalhar com lives próprias ou autorizadas e preservar autoria. A seleção não verifica direitos, nem pode garantir elegibilidade de recomendação. A publicação nas redes fica fora desta versão.

## 5. Transcrição e validação — OpenAI

[Transcrição de arquivos](https://developers.openai.com/api/docs/guides/speech-to-text).

A API aceita arquivos até 25 MB e oferece timestamps com whisper-1. Esta foi a opção pesquisada para a versão inicial. **Na versão 0.2 a transcrição é local e gratuita**, usando [faster-whisper](https://github.com/SYSTRAN/faster-whisper), modelo small em CPU/int8, com estimativas de tempo por palavra. O áudio não é enviado à API de transcrição. SRT importado mantém tempos por segmento. Ambas as modalidades precisam de revisão.

[Saídas estruturadas](https://developers.openai.com/api/docs/guides/structured-outputs).

Usamos um schema para candidatos, notas, justificativas e IDs de segmentos. Validamos duração, intervalo, existência de IDs e citação do primeiro segmento depois da resposta. Schema correto não garante interpretação editorial correta. Na versão 0.2, o schema é passado ao Codex CLI por --output-schema, usando a conta ChatGPT conectada e sem chamadas à API paga. O uso e o tratamento de dados seguem a conta do Codex.

[Modelo GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

Modelo considerado na primeira versão com API. A versão 0.2 usa o modelo padrão do Codex CLI com login ChatGPT, para aproveitar a assinatura existente. [Execução não interativa do Codex](https://learn.chatgpt.com/docs/non-interactive-mode). Não fizemos comparação empírica de modelos neste canal.

## 6. Avaliação antes de ajuste fino — OpenAI

[Trabalhando com avaliações](https://developers.openai.com/api/docs/guides/evals).

O guia organiza avaliação em critérios, entradas e execução de testes. Nossa adaptação é criar um conjunto representativo de lives com cortes anotados por editores e comparar candidatos contra os critérios. Não fizemos fine-tuning; não existe ainda um conjunto real de treinamento ou evidência de desempenho do nosso selecionador.

Protocolo proposto (decisão de produto):

1. Separar lives por origem e apresentador em desenvolvimento e teste, sem compartilhar trechos da mesma live entre conjuntos.
2. Registrar cortes aceitos/rejeitados, contexto anterior/posterior e motivo. Ter dois editores numa parte da amostra e revisar divergências.
3. Medir porcentagem de sugestões aproveitadas, contexto distorcido, erros de fronteira e tempo economizado. Comparar com seleção manual e com a versão anterior.
4. Usar métricas publicadas como sinal adicional, comparando mesma janela de tempo e objetivo; distribuição pode confundir a avaliação.
5. Só considerar fine-tuning depois de estabelecer uma avaliação estável e exemplos suficientes. Não enviar feedback automaticamente para treinamento.

## 7. Rubrica editorial implementada (hipótese própria)

| Critério | Peso | O que buscamos |
|---|---:|---|
| Gancho | 20 | Assunto/curiosidade relevante logo na abertura |
| Ideia completa | 20 | Trecho compreensível e com resolução |
| Valor | 20 | Utilidade, descoberta, história ou entretenimento |
| Público e objetivo | 15 | Aderência ao brief |
| Densidade textual | 10 | Pouca preparação para a entrega |
| Fidelidade | 15 | Manutenção do sentido e das ressalvas |

Cada dimensão recebe 0–5. A soma ponderada resulta em prioridade 0–100. **Esses pesos não vêm das plataformas e precisam ser calibrados.** Fidelidade abaixo de 4 ou ideia completa abaixo de 3 elimina o candidato. Sobreposição acima de 35% da duração do menor trecho elimina duplicações. Esses limiares também são escolhas do produto.

A análise cobre blocos de dez minutos com sobreposição suficiente para a duração máxima solicitada. Considera todos os blocos e depois ordena os candidatos. Não faz análise visual, não prevê desempenho e não reordena falas.

## 8. Integração e processamento

[GPT Actions](https://developers.openai.com/api/docs/actions/introduction) e [autenticação](https://developers.openai.com/api/docs/actions/authentication): um GPT pode chamar uma API descrita em OpenAPI. O pacote contém instruções, conhecimento e schema; conexão no ChatGPT exige uma API acessível por HTTPS e autenticação configurada.

[Filtros do FFmpeg](https://ffmpeg.org/ffmpeg-filters.html): usamos scale/crop para preencher 9:16 e sendcmd para reposicionar o recorte com detecção local de um rosto via OpenCV. O padrão não queima legendas. Há opção de recorte fixo com ajuste horizontal e scale/pad para preservar conteúdo com bordas. Revisão audiovisual permanece necessária, especialmente com várias pessoas ou mudanças de câmera.

[SDK oficial Python MCP](https://py.sdk.modelcontextprotocol.io/v2/): o servidor local expõe ferramentas via stdio. Essa conexão é alternativa para clientes desktop compatíveis; não torna o computador acessível ao ChatGPT na web.
