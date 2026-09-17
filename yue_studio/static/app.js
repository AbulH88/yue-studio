const $ = (id) => document.getElementById(id);
const projects = [
  {name:'Medieval Echoes', subtitle:'ANCIENT SOUNDS, NEW HORIZONS', art:'art-castle', datasets:3, tracks:14, checkpoint:'Step 1000', status:'Ready'},
  {name:'Dark Ambient', subtitle:'SHADOWS IN SOUND', art:'art-dark', datasets:2, tracks:8, checkpoint:'Step 800', status:'Training'},
  {name:'Cinematic Strings', subtitle:'EMOTION IN EVERY NOTE', art:'art-strings', datasets:1, tracks:22, checkpoint:'Step 1500', status:'Ready'}
];
const demoTracks = [
  ['01','monastery_chant_01.wav','WAV','02:15','Captioned','wav'],['02','lute_melody_ancient.mp3','MP3','01:42','Captioned','mp3'],['03','tavern_crowd_loop.wav','WAV','03:28','Needs review','wav'],['04','hurdy_gurdy_phrase.mp3','MP3','01:06','Captioned','mp3'],['05','cathedral_ambience.flac','FLAC','04:12','Needs review','flac'],['06','wooden_tavern_interior.wav','WAV','02:37','Captioned','wav']
];
function renderProjects(){
  $('projectGrid').innerHTML=projects.map((p,i)=>`<article class="project-card" data-project="${i}"><div class="project-art ${p.art}">${i===0?'♜':i===1?'☾':'♬'}</div><div class="project-card-body"><button class="project-menu" data-delete="${i}" title="Delete project">•••</button><h3>${p.name}</h3><em>${p.subtitle}</em><div class="card-rule"></div><div class="project-meta"><div><span>DATASETS</span>${p.datasets} datasets</div><div><span>LAST CHECKPOINT</span>${p.checkpoint}</div><div><span>TRACKS</span>${p.tracks} tracks</div><div><span>LAST ACTIVITY</span>Today, 14:32</div></div><b class="project-status ${p.status==='Training'?'training':''}">${p.status}</b></div></article>`).join('');
  document.querySelectorAll('.project-card').forEach(c=>c.addEventListener('click',()=>openProject(Number(c.dataset.project))));
  document.querySelectorAll('[data-delete]').forEach(b=>b.addEventListener('click',(event)=>{event.stopPropagation();const i=Number(b.dataset.delete);if(confirm(`Delete project "${projects[i].name}"? This will remove its project data but not shared models or ComfyUI files.`)){projects.splice(i,1);renderProjects();}}));
}
function renderTracks(){ $('tracks').innerHTML=demoTracks.map(t=>`<div class="track-row"><span>${t[0]}</span><b>${t[1]}</b><span class="format ${t[5]}">${t[2]}</span><span>${t[3]}</span><span class="status-pill ${t[4]==='Needs review'?'review':''}">${t[4]}</span><span class="mini-wave"></span><button class="play">▶</button></div>`).join(''); }
function openProject(i){ $('projectsScreen').classList.add('hidden');$('detailScreen').classList.remove('hidden');$('crumbName').textContent=projects[i].name;$('projectName').textContent=projects[i].name;renderTracks(); }
function showProjects(){ $('detailScreen').classList.add('hidden');$('projectsScreen').classList.remove('hidden');$('crumbName').textContent='Projects'; }
document.querySelectorAll('.rail-item').forEach(b=>b.addEventListener('click',()=>{ if(b.dataset.screen==='projects'||b.dataset.screen==='home')showProjects(); }));
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');if(b.dataset.tab!=='datasets')alert(`${b.textContent} view is coming next.`);}));
document.querySelectorAll('.steps button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.steps button').forEach(x=>x.classList.remove('chosen'));b.classList.add('chosen');}));
$('newProject').addEventListener('click',()=>{const name=prompt('Project name');if(name){projects.push({name,subtitle:'A NEW MUSICAL WORLD',art:'art-castle',datasets:0,tracks:0,checkpoint:'None',status:'Ready'});renderProjects();}});
$('addDataset').addEventListener('click',()=>alert('Dataset creation will let you choose a name and add MP3, WAV, FLAC, or M4A files.'));
renderProjects();
