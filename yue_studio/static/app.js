const $ = (id) => document.getElementById(id);
let config = {};
let tracks = [];

async function api(url, options = {}) {
  const response = await fetch(url, {headers: {'Content-Type': 'application/json'}, ...options});
  return response.json();
}

function show(view) {
  document.querySelectorAll('.view').forEach((el) => el.classList.toggle('active-view', el.id === view));
  document.querySelectorAll('.nav-item').forEach((el) => el.classList.toggle('active', el.dataset.view === view));
}

function renderTracks() {
  $('trackCount').textContent = tracks.length;
  const host = $('trackList');
  if (!tracks.length) { host.innerHTML = '<div class="empty-state">Choose an audio folder to begin.</div>'; return; }
  host.innerHTML = tracks.map((t, i) => `<div class="track-row" data-index="${i}">
    <div><b>${escapeHtml(t.name)}</b><small>${t.duration ? `${t.duration}s` : 'duration unavailable'} · ${t.has_caption ? 'caption found' : 'needs caption'}</small></div>
    <textarea class="caption" placeholder="Analyze this track to create a caption">${escapeHtml(t.caption || '')}</textarea>
    <button class="subtle-button analyze-one">${t.caption ? 'Regenerate' : 'Analyze'}</button>
  </div>`).join('');
  host.querySelectorAll('.analyze-one').forEach((button) => button.addEventListener('click', async (event) => {
    const row = event.target.closest('.track-row'); const track = tracks[Number(row.dataset.index)];
    const result = await api('/api/caption', {method: 'POST', body: JSON.stringify({track})});
    row.querySelector('.caption').value = result.caption;
    track.caption = result.caption;
  }));
  host.querySelectorAll('textarea').forEach((textarea) => textarea.addEventListener('change', async (event) => {
    const row = event.target.closest('.track-row'); const track = tracks[Number(row.dataset.index)];
    track.caption = event.target.value;
    await api('/api/caption/save', {method: 'POST', body: JSON.stringify({caption_path: track.caption_path, caption: track.caption})});
  }));
}

function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

async function scan() {
  config.dataset_path = $('datasetPath').value.trim();
  await api('/api/config', {method: 'POST', body: JSON.stringify(config)});
  tracks = (await api('/api/dataset')).tracks || [];
  $('scanStatus').textContent = `${tracks.length} track${tracks.length === 1 ? '' : 's'} found`;
  renderTracks();
}

async function load() {
  config = await api('/api/config');
  $('projectTitle').textContent = config.project_name || 'Untitled Music Project';
  $('projectName').value = config.project_name || '';
  $('projectType').value = config.project_type || 'General Music';
  $('triggerWord').value = config.trigger_word || '';
  $('exportFolder').value = config.export_path || './exports';
  $('datasetPath').value = config.dataset_path || '';
  $('instrumental').checked = config.instrumental !== false;
  $('exportPath').textContent = config.export_path || './exports';
  tracks = (await api('/api/dataset')).tracks || [];
  renderTracks();
}

document.querySelectorAll('.nav-item').forEach((button) => button.addEventListener('click', () => show(button.dataset.view)));
document.querySelectorAll('[data-go]').forEach((button) => button.addEventListener('click', () => show(button.dataset.go)));
$('scanButton').addEventListener('click', scan);
$('analyzeAll').addEventListener('click', async () => { for (const row of document.querySelectorAll('.analyze-one')) row.click(); });
$('saveSettings').addEventListener('click', async () => {
  config.project_name = $('projectName').value.trim() || 'Untitled Music Project';
  config.project_type = $('projectType').value; config.trigger_word = $('triggerWord').value.trim();
  config.export_path = $('exportFolder').value.trim() || './exports'; config.instrumental = $('instrumental').checked;
  await api('/api/config', {method: 'POST', body: JSON.stringify(config)});
  $('projectTitle').textContent = config.project_name; $('exportPath').textContent = config.export_path;
  alert('Studio settings saved locally.');
});
$('exportButton').addEventListener('click', () => show('checkpoints'));
load();
