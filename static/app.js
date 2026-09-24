'use strict';
const $ = s => document.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state, token, actor = 'ops', selected, filter = 'all', busy = false, createRequest;
const pending = new Map();
const labels = {approve:'Approve access',deny:'Decline access',acknowledge:'Acknowledge handbook',deliver:'Process delivery',retry:'Retry delivery',escalate:'Request People Ops review',resolve:'Resolve review'};
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').hidden = true, 6500); }
async function api(path, body) {
  const response = await fetch(path, {method:body ? 'POST':'GET', headers:{'Content-Type':'application/json','X-Demo-Actor':actor,'X-Demo-Token':token || ''}, ...(body ? {body:JSON.stringify(body)}:{})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed.');
  return data;
}
const needsAttention = c => c.escalated || ['Needs revision','Delivery failed','Needs approval'].includes(c.status);
function badge(c) { return `<span class="badge ${c.status === 'Complete' ? 'success' : c.delivery === 'failed' || c.approval === 'denied' ? 'danger' : 'warning'}">${esc(c.status)}</span>`; }
const actorName = id => state.actors.find(a => a.id === id)?.name || id;
async function refresh() { state = await api('/api/state'); if (!state.cases.some(c => c.id === selected)) selected = state.cases.find(c => c.approval === 'pending')?.id || state.cases[0]?.id; render(); }
function render() {
  $('#actor').innerHTML = state.actors.map(a => `<option value="${esc(a.id)}" ${a.id === actor ? 'selected':''}>${esc(a.name)}${a.role === 'employee' ? ' · Employee':''}</option>`).join('');
  $('#new-button').disabled = busy || state.actor.role !== 'operator';
  $('#actor').disabled = busy;
  const cases = state.cases;
  $('#stats').innerHTML = [[cases.length,'Onboarding cases'],[cases.filter(needsAttention).length,'Need attention'],[cases.filter(c => c.status === 'Complete').length,'Completed'],[cases.reduce((n,c)=>n+c.events.length,0),'Recorded events']].map(([n,label]) => `<div class="stat"><span class="stat-number">${n}</span><span class="stat-label">${label}</span></div>`).join('');
  const visible = cases.filter(c => filter === 'all' || (filter === 'attention' ? needsAttention(c) : c.status === 'Complete'));
  if (visible.length && !visible.some(c => c.id === selected)) selected = visible[0].id;
  $('#count').textContent = `${visible.length} ${visible.length === 1 ? 'person':'people'}`;
  $('#roster').innerHTML = visible.length ? visible.map(c => `<button class="person ${c.id === selected ? 'selected':''}" data-case="${esc(c.id)}" aria-pressed="${c.id === selected}"><span class="avatar">${esc(c.name.split(' ').map(s=>s[0]).slice(0,2).join(''))}</span><span class="person-main"><strong>${esc(c.name)}</strong><span>${esc(c.department)} · ${esc(c.starts_on)}</span>${badge(c)}</span><span class="person-arrow">↗</span></button>`).join('') : '<p class="empty">No onboarding cases in this view.</p>';
  renderDetail(visible.find(c => c.id === selected));
}
function renderDetail(c) {
  if (!c) { $('#detail').innerHTML = '<div class="empty"><h2>You’re all caught up.</h2><p>Choose another filter or start a new onboarding.</p></div>'; return; }
  const checks = [
    ['Welcome task created','A local task was queued. No email was sent.',true],
    ['Handbook acknowledgment','The employee confirms they have read the demo handbook.',c.acknowledged],
    ['Manager approval',c.approval === 'denied' ? 'Access declined. People Ops must review this case.' : `Assigned to ${actorName(c.manager_id)}.`,c.approval === 'approved'],
    ['Workspace delivery',c.delivery === 'failed' ? 'Simulated 503. The task is retained and ready to retry.' : c.delivery === 'delivered' ? `Simulated receipt: ${c.receipt}` : c.approval === 'approved' ? 'Approved. People Ops can now process the simulated delivery.' : 'Requires approval before the connector simulator can run.',c.delivery === 'delivered']
  ];
  const done = checks.filter(x=>x[2]).length;
  const actions = c.actions.filter(a => a !== 'escalate' || !c.escalated);
  $('#detail').innerHTML = `<div class="detail-heading"><div><div class="eyebrow">ONBOARDING CHECKLIST</div><h2>${esc(c.name)}</h2><p class="muted">${esc(c.department)} · Starts ${esc(c.starts_on)}</p></div>${badge(c)}</div>
    ${c.escalated ? '<div class="notice">People Ops review is open. Approval requirements still apply.</div>':''}
    <div class="progress-caption"><span>${done} of 4 steps complete</span><span>Version ${c.version}</span></div><div class="progress-track"><div class="progress-fill p${done}"></div></div>
    <div class="checklist">${checks.map(([name,description,complete]) => `<div class="check-row"><span class="check-icon ${complete ? 'done':''}">${complete ? '✓':'○'}</span><div><strong>${esc(name)}</strong><p>${esc(description)}</p></div></div>`).join('')}</div>
    <p class="access-note"><strong>Requested access:</strong> ${state.config.departments[c.department].access.map(esc).join(' · ')}</p>
    <div class="actions">${actions.map((a,i) => `<button class="${i === 0 && a !== 'escalate' ? 'primary':'secondary'}" data-action="${a}" ${busy ? 'disabled':''}>${labels[a]}</button>`).join('')}</div>
    ${state.actor.role === 'operator' && c.approval === 'pending' ? '<p class="form-note">Switch to the assigned manager to approve access.</p>':''}
    ${state.actor.role === 'employee' && !c.acknowledged ? '<details class="handbook"><summary>Read the demo handbook before acknowledging</summary><p>Welcome to fictional Harbor Works. Complete your first-week checklist, ask your assigned manager to approve workspace access, and contact People Ops if you are blocked. The standard equipment bundle is a laptop and headset; no reimbursement or shipping commitment is specified. This is a portfolio demonstration, not an actual employment policy.</p></details>':''}
    <div class="audit-heading"><h3>Activity trail</h3><button class="text-button" id="export-case">Download evidence ↓</button></div><div class="audit">${c.events.map(e=>`<div class="audit-item"><span class="audit-dot"></span><div><strong>${esc(e.action)}</strong><p>${esc(e.detail)}</p><span class="audit-meta">${esc(actorName(e.actor))} · ${esc(new Date(e.at).toLocaleString())}</span></div></div>`).join('')}</div>`;
}
async function command(action, reason) {
  if (busy) return;
  const c = state.cases.find(c=>c.id === selected); if (!c) return;
  const base = {action,id:c.id,version:c.version,...(reason ? {reason}:{})};
  const signature = JSON.stringify([actor,base]);
  if (!pending.has(signature)) pending.set(signature, {...base,key:crypto.randomUUID()});
  busy = true; render();
  try { await api('/api/command',pending.get(signature)); pending.delete(signature); await refresh(); toast(action === 'deliver' ? 'The simulator failed once. Retry delivery to recover.' : 'Saved. The activity trail has been updated.'); }
  catch(e) { toast(e.message); try { await refresh(); } catch (_) {} }
  finally { busy = false; render(); }
}
$('#roster').addEventListener('click',e=>{const b=e.target.closest('[data-case]');if(b){selected=b.dataset.case;render();}});
$('#detail').addEventListener('click',e=>{
  const b=e.target.closest('[data-action]'); if(b) command(b.dataset.action, b.dataset.action === 'escalate' ? 'Review requested from the onboarding checklist.' : undefined);
  if(e.target.closest('#export-case')) {
    const c = state.cases.find(c=>c.id === selected);
    const data={notice:'FICTIONAL DATA. Local demonstration; connectors simulated.',exported_at:new Date().toISOString(),case:c};
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
    const a=document.createElement('a'); a.href=url; a.download='demo-onboarding-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
});
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));render();}));
$('#actor').addEventListener('change',async e=>{actor=e.target.value;try{await refresh();}catch(e){toast(e.message);}});
$('#guide-toggle').addEventListener('click',()=>{const guide=$('#guide');guide.hidden=!guide.hidden;$('#guide-toggle').setAttribute('aria-expanded',String(!guide.hidden));});
$('#new-button').addEventListener('click',()=>{
  $('#department').innerHTML=Object.keys(state.config.departments).map(d=>`<option>${esc(d)}</option>`).join('');
  const date=new Date();date.setDate(date.getDate()+7);$('#starts-on').value=date.toISOString().slice(0,10);$('#new-dialog').showModal();
});
$('#close-dialog').addEventListener('click',()=>$('#new-dialog').close());
$('#new-form').addEventListener('submit',async e=>{
  e.preventDefault();if(busy)return;
  const base={action:'create',name:$('#employee-name').value,department:$('#department').value,starts_on:$('#starts-on').value};
  const signature=JSON.stringify(base);
  if(createRequest?.signature!==signature)createRequest={signature,payload:{...base,key:crypto.randomUUID()}};
  busy=true;$('#create-button').disabled=true;
  try {const result=await api('/api/command',createRequest.payload);createRequest=null;selected=result.id;filter='all';document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x.dataset.filter==='all'));$('#new-dialog').close();$('#new-form').reset();await refresh();toast('Onboarding created. Access is waiting for the assigned manager.');}
  catch(e){toast(e.message);}finally{busy=false;$('#create-button').disabled=false;render();}
});
async function ask() {
  const question=$('#question').value.trim();if(!question)return;
  $('#ask-button').disabled=true;$('#answer').textContent='Checking the demo handbook…';
  try {
    const data=await api('/api/ask',{question});
    $('#model-mode').textContent=data.mode;
    $('#answer').innerHTML=`<p class="answer-message">${esc(data.message)}</p>${data.sources.map(p=>`<article class="source"><div class="source-label">${esc(p.id)} · ${esc(p.title)} · ${esc(p.section)} · v${esc(p.version)}</div><blockquote>${esc(p.text)}</blockquote></article>`).join('')}<p class="form-note">${esc(data.model_status)}</p>${data.escalate ? '<button class="secondary" id="policy-escalate">Request People Ops review for selected case</button>':''}`;
    $('#policy-escalate')?.addEventListener('click',()=>{if(!selected)return toast('Select an onboarding case first.');command('escalate',`Policy question: ${question}`.slice(0,500));});
  } catch(e){$('#answer').textContent=e.message;}finally{$('#ask-button').disabled=false;}
}
$('#question-form').addEventListener('submit',e=>{e.preventDefault();ask();});
document.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>{$('#question').value=b.dataset.question;ask();}));
(async()=>{try{const boot=await api('/api/bootstrap');token=boot.token;if(boot.model_configured)$('#model-mode').textContent='Local model configured · awaiting first response';await refresh();}catch(e){$('#detail').innerHTML=`<div class="empty"><h2>Demo unavailable</h2><p>${esc(e.message)}</p><p>Start the local server, then reload this page.</p></div>`;$('#new-button').disabled=true;}})();
