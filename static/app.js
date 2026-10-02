let current = null, pollTimer = null, mediaUrl = null;
const $ = id => document.getElementById(id);
const escapeHtml = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const time = seconds => new Date(seconds*1000).toISOString().slice(11,19);
const token = () => sessionStorage.getItem('cortes_token');
async function request(path, options={}) {
  const headers = {...options.headers}; if(token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(path, {...options, headers});
  if(!response.ok){let body;try{body=await response.json()}catch{throw new Error('Falha de conexão')};throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));}
  return response;
}
async function api(path, body) {
  return (await request(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
}
function message(text){$('message').textContent=text;}
async function safely(action){try{await action()}catch(error){message(error.message)}}
async function refreshList(){const projects=await api('/api/projects');$('projects').replaceChildren();for(const p of projects){const b=document.createElement('button');b.textContent=p.title;b.onclick=()=>safely(()=>load(p.id));$('projects').append(b)}}
async function load(id){
  const switching=current?.id!==id;
  clearTimeout(pollTimer);current=await api(`/api/projects/${id}`);
  if(switching && current.brief)for(const [key,value] of Object.entries(current.brief)){const field=$('brief').elements.namedItem(key);if(field)field.value=value;}
  if(switching){$('player').ontimeupdate=null;$('cropX').value=Math.round((current.framing_crop_x??0.5)*100);}
  draw();updateFraming();
  if(current.status==='processando') pollTimer=setTimeout(()=>safely(()=>load(id)),1800);
  if(current.video && $('player').dataset.project !== id){
    const media=await api(`/api/projects/${id}/media-url`,{});
    $('player').src=media.url;$('player').dataset.project=id;
  }
}
function draw(){
  const busy=current.status==='processando';$('analyze').disabled=busy;$('transcribe').disabled=busy;
  $('transcribe').hidden=!current.video || !!current.segments.length;$('results').hidden=false;
  $('player').hidden=!current.video;$('projectTitle').textContent=current.title;
  message(current.message);$('clips').innerHTML='';
  if(!current.clips.length && !busy) $('clips').innerHTML='<p class="muted">Nenhum corte selecionado. Analise a transcrição ou ajuste a duração e o público.</p>';
  for(const c of current.clips){
    const article=document.createElement('article');article.className='clip';
    const labels={hook:'Gancho',completeness:'Ideia completa',value:'Valor',audience:'Público',pace:'Densidade',fidelity:'Fidelidade'};
    article.innerHTML=`<div class="clip-top"><div><h3>${escapeHtml(c.title)}</h3><span class="muted">${time(c.start)} → ${time(c.end)} · ${Math.round(c.duration)}s · ${escapeHtml(c.category)}</span></div><span class="badge">${c.score===null?'DEMONSTRAÇÃO':c.score+' / 100'}</span></div><p class="quote">“${escapeHtml(c.hook_quote)}”</p><p>${escapeHtml(c.reason)}</p><div class="scores">${c.scores?Object.entries(c.scores).map(([k,v])=>`<span>${labels[k]} ${v}/5</span>`).join(''):''}</div><p class="risks">${c.needs_visual_context?'Revisar referências visuais. ':''}${escapeHtml(c.risks.join(' · '))}</p><details><summary>Ver transcrição do trecho</summary><p class="transcript">${escapeHtml(c.caption_segments ? c.caption_segments.map(s=>s.text).join(" ") : c.transcript)}</p></details><div class="actions"><button data-action="preview" class="secondary">▶ Revisar no vídeo</button><button data-action="export">Exportar MP4 ↗</button>${c.exported?'<button data-action="download" class="secondary">Baixar MP4</button>':''}</div><details><summary>Registrar avaliação editorial</summary><p class="muted">O feedback é salvo para avaliação futura; não treina o modelo automaticamente.</p><input class="feedback-note" placeholder="O que funcionou ou precisa melhorar?"><div class="actions"><button data-action="approve" class="secondary">${c.approved?'Aprovado ✓':'Aprovar'}</button><button data-action="reject" class="secondary">Rejeitar</button></div></details>`;
    article.querySelector('[data-action=preview]').disabled=!current.video;
    article.querySelector('[data-action=export]').disabled=!current.video || busy;
    article.addEventListener('click', e=>{const action=e.target.dataset.action;if(!action)return;safely(async()=>{
      const base=`/api/projects/${current.id}/clips/${c.id}`;
      if(action==='preview'){$('player').currentTime=c.start;await $('player').play();$('player').scrollIntoView({behavior:'smooth'});$('player').ontimeupdate=()=>{if($('player').currentTime>=c.end)$('player').pause()};}
      if(action==='export'){
        if(!confirm(`Você revisou o trecho ${time(c.start)}–${time(c.end)} e o enquadramento escolhido?`))return;
        await api(base+'/render',{format:$('format').value,subtitles:false,crop_x:Number($('cropX').value)/100,follow_face:$('followFace').checked,confirmed:true});await load(current.id);
      }
      if(action==='download'||action==='srt'){const kind=action==='srt'?'srt':'mp4';const response=await request(base+'/download?kind='+kind);const disposition=response.headers.get('Content-Disposition')||'';const encoded=disposition.match(/filename\*=UTF-8''([^;]+)/i);const plain=disposition.match(/filename="([^"]+)"/i);const name=encoded?decodeURIComponent(encoded[1]):plain?plain[1]:c.id+'.'+kind;const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
      if(action==='approve'||action==='reject'){await api(base+'/feedback',{decision:action==='approve'?'aprovado':'rejeitado',note:article.querySelector('input').value,platform:$('brief').elements.platform.value});await load(current.id);message('Avaliação salva.');}
    })});$('clips').append(article);
  }
}
$('file').onchange=()=>safely(async()=>{const file=$('file').files[0];if(!file)return;const data=new FormData();data.append('file',file);$('uploadStatus').textContent='Enviando '+file.name+'…';const p=await(await request('/api/upload',{method:'POST',body:data})).json();await load(p.id);await refreshList();$('uploadStatus').textContent='Material recebido.';});
$('demo').onclick=()=>safely(async()=>{const sample=await(await fetch('/static/example.json')).json();const p=await api('/api/transcripts',sample);$('mode').value='demo';await load(p.id);await refreshList();message('Exemplo carregado. Clique em Encontrar cortes. Demonstração sem análise estratégica.');});
$('transcribe').onclick=()=>safely(async()=>{await api(`/api/projects/${current.id}/transcribe`,{});await load(current.id)});
$('brief').onsubmit=e=>{e.preventDefault();safely(async()=>{if(!current)throw new Error('Envie um material ou carregue o exemplo primeiro.');const body=Object.fromEntries(new FormData(e.target));for(const k of ['min_duration','max_duration','count'])body[k]=Number(body[k]);await api(`/api/projects/${current.id}/analyze`,body);await load(current.id);});};
$('newProject').onclick=()=>{clearTimeout(pollTimer);current=null;$('results').hidden=true;$('transcribe').hidden=true;$('analyze').disabled=false;$('file').value='';message('Selecione um novo material.');};
$('access').onclick=()=>safely(async()=>{const value=prompt('Chave CORTES_API_TOKEN (armazenada só nesta sessão do navegador):');if(value!==null){sessionStorage.setItem('cortes_token',value);await refreshList();message('Chave atualizada.')}});
safely(async()=>{const h=await api('/api/health');$('health').textContent=h.codex.chatgpt_authenticated?'● Codex conectado · sem API paga':'○ Conecte o Codex ao ChatGPT';await refreshList();const project=new URLSearchParams(location.search).get('project');if(project)await load(project)});

function updateFraming(){
  const crop=$('format').value==='vertical_crop';
  $('cropControl').hidden=!crop||$('followFace').checked;
  $('cropValue').textContent=$('cropX').value+'%';
  $('player').classList.toggle('crop-preview',crop);
  $('player').style.objectPosition=$('cropX').value+'% 50%';
}
$('format').onchange=updateFraming;
$('cropX').oninput=updateFraming;
updateFraming();

$('followFace').onchange=updateFraming;
