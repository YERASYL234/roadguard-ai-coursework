'use strict';
const $ = s => document.querySelector(s);
const labels = {clear:'Жарық анықталмады',damage:'Зақым бар',danger:'Қауіпті жағдай'};
const advice = {clear:'Модель осы кадрда жарық бар бөліктерді анықтамады.',damage:'Белгіленген бөліктерді маманға тексерту ұсынылады.',danger:'Зақым кең таралған болуы мүмкін. Учаскені басымдықпен тексеріңіз.'};
let selectedFile=null, result=null, previewImage=null, busy=false, ready=false;
let history=[];
try { const saved=JSON.parse(localStorage.getItem('roadguard-history')||'[]'); if(Array.isArray(saved)) history=saved.filter(r=>r&&labels[r.level]).slice(0,50); } catch {}
const today=new Date(), months=['қаңтар','ақпан','наурыз','сәуір','мамыр','маусым','шілде','тамыз','қыркүйек','қазан','қараша','желтоқсан'];
$('#today').textContent=`${today.getDate()} ${months[today.getMonth()]} ${today.getFullYear()}`;
function setError(message){$('#error').textContent=message;$('#error').hidden=!message;}
function syncButton(){$('#analyze').disabled=!selectedFile||busy||!ready;$('#file').disabled=busy;$('#remove-file').disabled=busy;$('#road').disabled=busy;document.querySelectorAll('.sample').forEach(b=>b.disabled=busy);}
function resetResult(){result=null;$('#result-content').hidden=true;$('#result-empty').hidden=false;$('#result-state').textContent='ТАЛДАУҒА ДАЙЫН';}
async function chooseFile(file){
  if(busy||!file)return;
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setError('JPG, PNG немесе WebP фотосын таңдаңыз.');return;}
  if(file.size>12*1024*1024){setError('Файл өлшемі 12 МБ-тан аспауы керек.');return;}
  setError('');selectedFile=file;resetResult();$('#filename').textContent=file.name;$('#filesize').textContent=`${(file.size/1024/1024).toFixed(2)} МБ · Талдауға дайын`;$('#file-info').hidden=false;
  const url=URL.createObjectURL(file), current=file;
  const img=new Image();img.onload=()=>{URL.revokeObjectURL(url);if(selectedFile!==current)return;previewImage=img;draw();};img.onerror=()=>{URL.revokeObjectURL(url);if(selectedFile!==current)return;selectedFile=null;setError('Фотосурет ашылмады. Басқа файл таңдаңыз.');syncButton();};img.src=url;syncButton();
}
function draw(){
  if(!previewImage)return;const canvas=$('#preview');canvas.width=previewImage.naturalWidth;canvas.height=previewImage.naturalHeight;const ctx=canvas.getContext('2d');ctx.drawImage(previewImage,0,0);
  if(result&&$('#overlay').checked){const color=result.level==='danger'?'218,80,68':'236,166,47';for(const cell of result.cells){if(!cell.crack)continue;let [x,y,x2,y2]=cell.box;ctx.fillStyle=`rgba(${color},.23)`;ctx.fillRect(x,y,x2-x,y2-y);ctx.strokeStyle=`rgba(${color},.9)`;ctx.lineWidth=Math.max(1,canvas.width/500);ctx.strokeRect(x+1,y+1,x2-x-2,y2-y-2);}}
  canvas.hidden=false;$('#empty-preview').hidden=true;$('#image-label').hidden=false;
}
$('#file').addEventListener('change',e=>chooseFile(e.target.files[0]));
$('#dropzone').addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();if(!busy)$('#file').click();}});
for(const event of ['dragover','dragenter'])$('#dropzone').addEventListener(event,e=>{e.preventDefault();if(!busy)$('#dropzone').classList.add('dragging');});
for(const event of ['dragleave','drop'])$('#dropzone').addEventListener(event,e=>{e.preventDefault();$('#dropzone').classList.remove('dragging');});
$('#dropzone').addEventListener('drop',e=>chooseFile(e.dataTransfer.files[0]));
$('#remove-file').onclick=()=>{if(busy)return;selectedFile=null;previewImage=null;$('#file').value='';$('#file-info').hidden=true;$('#preview').hidden=true;$('#empty-preview').hidden=false;$('#image-label').hidden=true;resetResult();$('#result-state').textContent='ФОТО КҮТІЛУДЕ';setError('');syncButton();};
$('#road').onchange=()=>{$('#route-name').textContent=$('#road').selectedOptions[0].textContent.split(' · ')[0];};
$('#overlay').onchange=draw;
$('#analyze').onclick=async()=>{
  if(!selectedFile||busy)return;busy=true;syncButton();setError('');$('#processing').hidden=false;$('#result-state').textContent='ТАЛДАНУДА';
  try{
    const response=await fetch('/api/predict',{method:'POST',headers:{'Content-Type':selectedFile.type,'X-Demo-Road':$('#road').value},body:selectedFile,signal:AbortSignal.timeout(120000)});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Талдау орындалмады.');result=data;
    await new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{previewImage=img;resolve();};img.onerror=reject;img.src=result.preview;});
    $('#result-title').textContent=labels[result.level];$('#result-title').style.color={clear:'#218165',damage:'#b77c20',danger:'#d5534d'}[result.level];$('#result-advice').textContent=advice[result.level];$('#result-icon').textContent=result.level==='clear'?'✓':'!';$('#result-icon').style.color=$('#result-title').style.color;
    $('#coverage').textContent=(result.affected_tile_fraction*100).toFixed(1)+'%';$('#tiles').textContent=`${result.positive_tiles} / ${result.total_tiles}`;$('#latency').textContent=(result.elapsed_ms/1000).toFixed(2)+' с';$('#result-empty').hidden=true;$('#result-content').hidden=false;$('#result-state').textContent='ТАЛДАУ АЯҚТАЛДЫ';draw();
    const entry={filename:selectedFile.name,road:result.road,level:result.level,coverage:result.affected_tile_fraction,timestamp:new Date().toISOString()};history.unshift(entry);history=history.slice(0,50);saveHistory();renderHistory();
  }catch(e){setError(e.message||'Сервермен байланыс үзілді.');$('#result-state').textContent='ТАЛДАУ ҚАТЕСІ';}
  finally{busy=false;$('#processing').hidden=true;syncButton();}
};
$('#download').onclick=()=>{if(!result)return;const {preview,...report}=result;report.filename=selectedFile.name;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='roadguard-report-'+Date.now()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
function saveHistory(){try{localStorage.setItem('roadguard-history',JSON.stringify(history));}catch{setError('Талдау дайын. Браузер тарихты сақтауға рұқсат бермеді.');}}
function renderHistory(){
  $('#history-count').textContent=history.length;$('#history-empty').hidden=history.length>0;$('#history-table').hidden=!history.length;$('#history-body').replaceChildren();
  for(const r of history){const tr=document.createElement('tr');for(const value of [new Date(r.timestamp).toLocaleString('kk-KZ'),r.filename,r.road,labels[r.level],(r.coverage*100).toFixed(1)+'%']){const td=document.createElement('td');td.textContent=value;tr.append(td);}const badge=document.createElement('span');badge.className='badge '+r.level;badge.textContent=labels[r.level];tr.children[3].replaceChildren(badge);$('#history-body').append(tr);}
}
$('#clear-history').onclick=()=>{history=[];saveHistory();renderHistory();};
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b===button));document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!=='view-'+button.dataset.view);$('#breadcrumb').textContent={analysis:'Фото талдау',history:'Тексеру тарихы',model:'Модель және метрикалар'}[button.dataset.view];});
async function initialize(){
  renderHistory();
  try{const response=await fetch('/api/health');if(!response.ok)throw Error();ready=(await response.json()).ready;$('#server-status').innerHTML='<i></i>Модель дайын · CPU';syncButton();}catch{$('#server-status').textContent='Сервер қолжетімсіз';setError('Python серверін іске қосыңыз: python app.py');}
  try{
    const response=await fetch('/api/metrics');if(!response.ok)throw Error();const data=await response.json();for(const [key,value]of Object.entries(data.test)){const node=document.querySelector(`[data-metric="${key}"]`);if(node)node.textContent=(value*100).toFixed(1)+'%';const row=document.createElement('div');row.className='metric-row';const label=document.createElement('span');label.textContent=key.toUpperCase();const b=document.createElement('b');b.textContent=(value*100).toFixed(2)+'%';row.append(label,b);$('#model-metrics').append(row);}
    const matrix=document.createElement('div');matrix.className='matrix';['','Жоқ','Жарық','Жоқ',data.confusion_matrix[0][0],data.confusion_matrix[0][1],'Жарық',data.confusion_matrix[1][0],data.confusion_matrix[1][1]].forEach((value,i)=>{const s=document.createElement('span');s.textContent=value;if([4,5,7,8].includes(i))s.className='cell'+([4,8].includes(i)?' correct':'');matrix.append(s);});$('#confusion').append(matrix);
    $('#dataset-summary').textContent=`Train: ${data.split.train.sources} фото / ${data.split.train.patches} бөлік. Validation: ${data.split.val.sources} фото / ${data.split.val.patches} бөлік. Test: ${data.split.test.sources} фото / ${data.test_samples} бөлік. Best epoch: ${data.best_epoch}. Decision threshold: ${data.threshold.toFixed(3)}.`;
  }catch{$('#model-metrics').textContent='Test метрикалары әлі жоқ. scripts/train.py --evaluate іске қосыңыз.';}
  try{const samples=await(await fetch('/api/samples')).json();for(const sample of samples){const b=document.createElement('button');b.className='sample';b.title=sample.label;const img=document.createElement('img');img.src=sample.url;img.alt=sample.label;const span=document.createElement('span');span.textContent=sample.label;b.append(img,span);b.onclick=async()=>{if(busy)return;try{const response=await fetch(sample.url);if(!response.ok)throw Error();const blob=await response.blob();await chooseFile(new File([blob],sample.filename,{type:'image/jpeg'}));}catch{setError('Мысал сурет жүктелмеді.');}};$('#samples').append(b);}}catch{setError('Дайын суреттер қолжетімсіз. Өз фотоңызды жүктеңіз.');}
}
initialize();
