const $ = (id) => document.getElementById(id);
const projects = [{name:'TEST', subtitle:'NEW MUSICAL WORLD', art:'art-castle', datasets:0, tracks:0, checkpoint:'None', status:'Ready'}];
let datasets = [];
let currentDataset = null;
function renderProjects(){
  $('projectGrid').innerHTML=projects.map((p,i)=>`<article class="project-card" data-project="${i}"><div class="project-art ${p.art}">${i===0?'♜':i===1?'☾':'♬'}</div><div class="project-card-body"><button class="project-menu" data-delete="${i}" title="Delete project">•••</button><h3>${p.name}</h3><em>${p.subtitle}</em><div class="card-rule"></div><div class="project-meta"><div><span>DATASETS</span>${p.datasets} datasets</div><div><span>LAST CHECKPOINT</span>${p.checkpoint}</div><div><span>TRACKS</span>${p.tracks} tracks</div><div><span>LAST ACTIVITY</span>Today, 14:32</div></div><b class="project-status ${p.status==='Training'?'training':''}">${p.status}</b></div></article>`).join('');
  document.querySelectorAll('.project-card').forEach(c=>c.addEventListener('click',()=>openProject(Number(c.dataset.project))));
  document.querySelectorAll('[data-delete]').forEach(b=>b.addEventListener('click',(event)=>{event.stopPropagation();const i=Number(b.dataset.delete);if(confirm(`Delete project "${projects[i].name}"? This will remove its project data but not shared models or ComfyUI files.`)){projects.splice(i,1);renderProjects();}}));
}
function formatDuration(seconds){if(seconds===null||seconds===undefined)return '—';const total=Math.round(seconds);return `${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`;}
function renderTracks(){
  const tracks=currentDataset?.tracks||[];
  $('trackCount').textContent=`${tracks.length} track${tracks.length===1?'':'s'}`;
  $('tracks').innerHTML=tracks.length?tracks.map((t,i)=>`<div class="track-row"><span>${String(i+1).padStart(2,'0')}</span><b>${t.name}</b><span class="format ${t.name.split('.').pop().toUpperCase()}">${t.name.split('.').pop().toUpperCase()}</span><span>${formatDuration(t.duration)}</span><span class="status-pill ${t.has_caption?'':'review'}">${t.has_caption?'Captioned':'Needs review'}</span><span class="mini-wave"></span><button class="play" title="Audio path: ${t.path}">▶</button></div>`).join(''):'<div class="empty-table">No audio files have been added to this project.</div>';
}
function renderDatasets(){
  const cards=$('datasetCards');
  if(!datasets.length){cards.innerHTML='<div class="empty-dataset"><strong>No datasets yet</strong><span>Create a dataset and add your MP3, WAV, FLAC, or M4A files.</span><button class="dark-gold" id="emptyAddDataset">＋ Create Dataset</button></div>';const empty=$('emptyAddDataset');if(empty)empty.addEventListener('click',createDataset);}
  else {cards.innerHTML=datasets.map((d,i)=>`<button class="dataset-card ${currentDataset===d?'selected':''}" data-dataset="${i}"><strong>${d.name}</strong><span>${d.track_count} tracks · ${d.path}</span></button>`).join('');document.querySelectorAll('[data-dataset]').forEach(b=>b.addEventListener('click',()=>{currentDataset=datasets[Number(b.dataset.dataset)];renderDatasets();renderTracks();}));}
  const select=$('datasetSelect');if(select){select.innerHTML=datasets.length?datasets.map((d,i)=>`<option value="${i}">${d.name} (${d.track_count} tracks)</option>`).join(''):'<option>No datasets available</option>';select.disabled=!datasets.length;}
  renderTracks();
}
async function loadDatasets(){const response=await fetch('/api/dataset');const data=await response.json();datasets=data.datasets||[];currentDataset=datasets[0]||null;projects[0].datasets=datasets.length;projects[0].tracks=datasets.reduce((sum,d)=>sum+d.track_count,0);renderDatasets();}
async function createDataset(){const name=prompt('Dataset name');if(!name)return;const path=prompt('Full audio folder path (for example: C:\\Users\\jimi\\Music\\Test Music\\Medival)');if(!path)return;try{const response=await fetch('/api/dataset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,path})});const data=await response.json();if(!response.ok||data.error)throw new Error(data.error||'Dataset could not be created.');await loadDatasets();alert(`Dataset "${name}" added with ${data.dataset.track_count} audio files.`);}catch(error){alert(error.message);}}
async function openProject(i){ $('projectsScreen').classList.add('hidden');$('detailScreen').classList.remove('hidden');$('crumbName').textContent=projects[i].name;$('projectName').textContent=projects[i].name;await loadDatasets(); }
function showProjects(){ $('detailScreen').classList.add('hidden');$('projectsScreen').classList.remove('hidden');$('crumbName').textContent='Projects'; }
document.querySelectorAll('.rail-item').forEach(b=>b.addEventListener('click',showProjects));
function showTab(name){
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));
  document.querySelectorAll('.tab-screen').forEach(x=>x.classList.add('hidden-tab'));
  const panel=$(name==='datasets'?'datasetsTab':name==='runs'?'runsTab':name==='checkpoints'?'checkpointsTab':name==='models'?'modelsTab':'generateTab');
  if(panel)panel.classList.remove('hidden-tab');
}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));
document.querySelectorAll('[data-jump]').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.jump)));
document.querySelectorAll('.steps button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.steps button').forEach(x=>x.classList.remove('chosen'));b.classList.add('chosen');}));
document.querySelectorAll('.steps button').forEach(b=>b.addEventListener('click',()=>{const input=$('customSteps');if(input)input.value=b.dataset.steps;}));
$('newProject').addEventListener('click',()=>{const name=prompt('Project name');if(name){projects.push({name,subtitle:'A NEW MUSICAL WORLD',art:'art-castle',datasets:0,tracks:0,checkpoint:'None',status:'Ready'});renderProjects();}});
$('addDataset').addEventListener('click',createDataset);
if($('emptyAddDataset'))$('emptyAddDataset').addEventListener('click',createDataset);
if($('applySteps'))$('applySteps').addEventListener('click',()=>{const value=Number($('customSteps').value);if(!Number.isInteger(value)||value<1){alert('Training steps must be a whole number greater than 0.');return;}document.querySelectorAll('.steps button').forEach(x=>x.classList.remove('chosen'));alert(`Training steps set to ${value}.`);});
if($('startTraining'))$('startTraining').addEventListener('click',()=>{const value=Number($('customSteps').value);if(!Number.isInteger(value)||value<1){alert('Enter a valid number of training steps first.');return;}alert(`Training run configured for ${value} steps. The real WSL2 trainer connection is the next integration.`);});
renderProjects();
