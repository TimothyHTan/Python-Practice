// Settings page: the save folder (server.py /api/settings) and the AI helper defaults
// (the same localStorage keys the practice page's Model/Effort pickers use).
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const OFFLINE = 'The local server is not running. Start it with <code>site\\start.bat</code> (Windows) or <code>./site/start.sh</code> (Linux), then reload.';

async function api(path, body) {
  const opts = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? `Request failed (${res.status})`);
  return data;
}
// fetch() throws a TypeError when nothing is listening.
const fail = (el, e) => { el.innerHTML = e instanceof TypeError ? OFFLINE : esc(e.message); el.dataset.state = 'bad'; };

let info = null;
function showFolder(saved) {
  $('folder').value = info.folder;
  $('folder-status').innerHTML = `${saved ? 'Saved. ' : ''}Saving to <code>${esc(info.folder)}</code>${info.folder === info.default ? ' (the default)' : ''}.`;
  $('folder-status').dataset.state = 'ok';
}

const AI = { 'ai-model': 'vw.ai.model', 'ai-effort': 'vw.ai.effort' };
const loadAi = () => { for (const [id, key] of Object.entries(AI)) $(id).value = JSON.parse(localStorage.getItem(key) ?? '""'); };
for (const [id, key] of Object.entries(AI)) $(id).addEventListener('change', () => localStorage.setItem(key, JSON.stringify($(id).value)));
loadAi();

function showAi() {
  $('ai-status').innerHTML = info.claude
    ? `Found the CLI at <code>${esc(info.claude)}</code>. Route: ${esc(info.route)}.`
    : 'The Claude Code CLI was not found on PATH. Install it (see the README), run <code>claude</code> once to log in, then restart the server.';
  $('ai-status').dataset.state = info.claude ? 'ok' : 'bad';
  if (info.models?.length) {
    const group = document.createElement('optgroup');
    group.label = 'Your CLI tool';
    group.innerHTML = info.models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    $('ai-model').append(group);
    loadAi(); // a saved CLI-tool model can only be selected once its option exists
  }
}

async function setFolder(folder) {
  $('folder-status').textContent = 'Saving…';
  delete $('folder-status').dataset.state;
  try { info = await api('/api/settings', { folder }); showFolder(true); } catch (e) { fail($('folder-status'), e); }
}
$('folder-form').addEventListener('submit', (e) => { e.preventDefault(); setFolder($('folder').value); });
$('folder-default').addEventListener('click', () => setFolder(''));
$('folder-open').addEventListener('click', () => api('/api/open-folder', {}).catch((e) => fail($('folder-status'), e)));

api('/api/settings')
  .then((d) => { info = d; showFolder(false); showAi(); })
  .catch((e) => { fail($('folder-status'), e); fail($('ai-status'), e); });
