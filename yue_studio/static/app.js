const $ = (id) => document.getElementById(id);
const projects = [{name:'TEST', subtitle:'NEW MUSICAL WORLD', art:'art-castle', datasets:0, tracks:0, checkpoint:'None', status:'Ready'}];
const demoTracks = [];
function renderProjects(){
  $('projectGrid').innerHTML=projects.map((p,i)=>`<article class="project-card" data-project="${i}"><div class="project-art ${p.art}">${i===0?'♜':i===1?'☾':'♬'}</div><div class="project-card-body"><button class="project-menu" data-delete="${i}" title="Delete project">•••</button><h3>${p.name}</h3><em>${p.subtitle}</em><div class="card-rule"></div><div class="project-meta"><div><span>DATASETS</span>${p.datasets} datasets</div><div><span>LAST CHECKPOINT</span>${p.checkpoint}</div><div><span>TRACKS</span>${p.tracks} tracks</div><div><span>LAST ACTIVITY</span>Today, 14:32</div></div><b class="project-status ${p.status==='Training'?'training':''}">${p.status}</b></div></article>`).join('');
  document.querySelectorAll('.project-card').forEach(c=>c.addEventListener('click',()=>openProject(Number(c.dataset.project))));
  document.querySelectorAll('[data-delete]').forEach(b=>b.addEventListener('click',(event)=>{event.stopPropagation();const i=Number(b.dataset.delete);if(confirm(`Delete project "${projects[i].name}"? This will remove its project data but not shared models or ComfyUI files.`)){projects.splice(i,1);renderProjects();}}));
}
function renderTracks(){ $('tracks').innerHTML=demoTracks.length?demoTracks.map(t=>`<div class="track-row"><span>${t[0]}</span><b>${t[1]}</b><span class="format ${t[5]}">${t[2]}</span><span>${t[3]}</span><span class="status-pill ${t[4]==='Needs review'?'review':''}">${t[4]}</span><span class="mini-wave"></span><button class="play">▶</button></div>`).join(''):'<div class="empty-table">No audio files have been added to this project.</div>'; }
function openProject(i){ $('projectsScreen').classList.add('hidden');$('detailScreen').classList.remove('hidden');$('crumbName').textContent=projects[i].name;$('projectName').textContent=projects[i].name;renderTracks(); }
function showProjects(){ $('detailScreen').classList.add('hidden');$('projectsScreen').classList.remove('hidden');$('crumbName').textContent='Projects'; }
document.querySelectorAll('.rail-item').forEach(b=>b.addEventListener('click',()=>{
  const screen=b.dataset.screen;
  if(screen==='projects'||screen==='home'){showProjects();return;}
  if(!projects.length)return;
  openProject(0);
  if(screen==='datasets')showTab('datasets');
  else if(screen==='training')showTab('runs');
  else if(screen==='generate')showTab('generate');
  else if(screen==='exports')showTab('checkpoints');
  else if(screen==='models')showTab('models');
}));
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
$('addDataset').addEventListener('click',()=>alert('Dataset creation will let you choose a name and add MP3, WAV, FLAC, or M4A files.'));
if($('emptyAddDataset'))$('emptyAddDataset').addEventListener('click',()=>alert('Dataset creation will let you choose a name and add MP3, WAV, FLAC, or M4A files.'));
if($('applySteps'))$('applySteps').addEventListener('click',()=>{const value=Number($('customSteps').value);if(!Number.isInteger(value)||value<1){alert('Training steps must be a whole number greater than 0.');return;}document.querySelectorAll('.steps button').forEach(x=>x.classList.remove('chosen'));alert(`Training steps set to ${value}.`);});
if($('startTraining'))$('startTraining').addEventListener('click',()=>{const value=Number($('customSteps').value);if(!Number.isInteger(value)||value<1){alert('Enter a valid number of training steps first.');return;}alert(`Training run configured for ${value} steps. The real WSL2 trainer connection is the next integration.`);});
renderProjects();
