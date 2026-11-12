// Settings page: the save folder (server.py /api/settings) and the AI helper defaults
// (the same localStorage keys the practice page's Model/Effort pickers use).
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const OFFLINE = 'The local server is not running. Start it with <code>site\\start.bat</code> (Windows) or <code>./site/start.sh</code> (Linux), then reload.';

async function api(path, body) {
  const opts = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  // 404 on our own API: the server window was started before this page was updated.
  if (res.status === 404) throw new Error('The site server is older than this page. Close its window and start it again (start.bat / start.sh).');
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

const COMMAND = { claude: 'claude', codex: 'codex' };
function showAi() {
  const path = info.clis[info.provider], name = info.providers[info.provider];
  const ready = info.ready[info.provider];
  $('ai-status').innerHTML = info.proxy
    ? `Route: ${esc(info.route)}.`
    : path
      ? `Using ${esc(name)} at <code>${esc(path)}</code>. Route: ${esc(info.route)}.${info.hint ? ' ' + esc(info.hint) : ''}`
      : `${esc(name)} was not found on PATH. Install it (see the README), run <code>${COMMAND[info.provider]}</code> once to log in, then restart the server.`;
  $('ai-status').dataset.state = ready ? 'ok' : 'bad';
  for (const opt of $('ai-provider').options) {
    opt.textContent = info.providers[opt.value] + (info.ready[opt.value] ? '' : ' (not installed)');
  }
  $('ai-provider').value = info.provider;
  $('ai-model').innerHTML = '<option value="">Default</option>'
    + info.models.map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join('');
  loadAi(); // a saved model can only be selected once its option exists
  // A model saved for the other tool (or one this account can't run) isn't listed: fall back to Default.
  if ($('ai-model').selectedIndex < 0) {
    $('ai-model').value = '';
    localStorage.setItem(AI['ai-model'], '""');
  }

  // Codex: the server tries each model once, so a free account only sees the models it can run.
  const codex = info.provider === 'codex' && ready;
  $('ai-scan').hidden = $('ai-models').hidden = !codex;
  $('ai-scan').disabled = info.scanning;
  if (!codex) return;
  $('ai-models').innerHTML = info.scanning
    ? 'Checking which Codex models your account can use (sends each one a tiny test prompt, about 30 seconds)…'
    : info.models.length
      ? `Models your account can use: ${info.models.map(([, label]) => esc(label)).join(', ')}. "Default" uses the first one.`
      : 'Codex has no model list yet. Run <code>codex</code> once and sign in, then press Scan again.';
  if (info.scanning) delete $('ai-models').dataset.state; else $('ai-models').dataset.state = info.models.length ? 'ok' : 'bad';
  if (info.scanning) setTimeout(refreshAi, 3000);
}

async function refreshAi() {
  try { info = { ...info, ...(await api('/api/ai-info')) }; showAi(); } catch (e) { fail($('ai-models'), e); }
}

$('ai-provider').addEventListener('change', async () => {
  $('ai-status').textContent = 'Switching…';
  delete $('ai-status').dataset.state;
  try { info = await api('/api/settings', { ai: $('ai-provider').value }); showAi(); } catch (e) { fail($('ai-status'), e); }
});
$('ai-scan').addEventListener('click', async () => {
  try { info = await api('/api/settings', { scan: true }); showAi(); } catch (e) { fail($('ai-models'), e); }
});

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
