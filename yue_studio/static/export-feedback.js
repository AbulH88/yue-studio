document.addEventListener('click', async (event) => {
  const button = event.target.closest('#exportCheckpoints');
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  const names = [...document.querySelectorAll('.checkpoint-select:checked')].map((box) => box.value);
  if (!names.length) { window.alert('Select at least one checkpoint first.'); return; }
  button.disabled = true;
  button.textContent = 'Choose destination…';
  try {
    const picker = await fetch('/api/picker/export-folder');
    const selected = await picker.json();
    if (!picker.ok) throw new Error(selected.error || 'Windows folder picker could not open.');
    if (!selected.path) { button.textContent = 'Export cancelled'; return; }
    button.textContent = 'Exporting…';
    const runId = (await (await fetch('/api/training/checkpoints')).json()).run_id;
    const response = await fetch('/api/training/export', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:runId,checkpoint_names:names,destination:selected.path})});
    const result = await response.json();
    if (!response.ok || result.error) throw new Error(result.error || 'Export failed.');
    window.alert(`Exported ${result.exported.length} ComfyUI adapter${result.exported.length === 1 ? '' : 's'}.`);
  } catch (error) {
    window.alert(`Export could not start: ${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = '⇧ Export selected to ComfyUI';
  }
}, true);
