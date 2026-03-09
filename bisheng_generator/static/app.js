// Bisheng Workflow Studio — Atelier Theme

const $ = id => document.getElementById(id);

const queryInput        = $('queryInput');
const generateBtn       = $('generateBtn');
const sendIcon          = $('sendIcon');
const sendSpinner       = $('sendSpinner');
const chatMessages      = $('chatMessages');
const welcomeBlock      = $('welcomeBlock');
const inputHint         = $('inputHint');
const newSessionBtn     = $('newSessionBtn');
const toggleTokenBtn    = $('toggleTokenBtn');
const tokenPanel        = $('tokenPanel');
const tokenDot          = $('tokenDot');
const bishengTokenInput = $('bishengTokenInput');
const saveTokenBtn      = $('saveTokenBtn');
const tokenHint         = $('tokenHint');
const toggleSidebarBtn  = $('toggleSidebarBtn');
const sidebar           = $('sidebar');
const historyList       = $('historyList');
const refreshHistoryBtn = $('refreshHistoryBtn');
const historyBackBtn    = $('historyBackBtn');
const historyPanelTitle = $('historyPanelTitle');
const sessionDetail     = $('sessionDetail');
const sessionTimeline   = $('sessionTimeline');
const progressSection   = $('progressSection');
const progressLogs      = $('progressLogs');
const errorBar          = $('error');
const jsonModal         = $('jsonModal');
const jsonContent       = $('jsonContent');
const modalImportBtn    = $('modalImportBtn');
const modalDownloadBtn  = $('modalDownloadBtn');
const modalCopyBtn      = $('modalCopyBtn');
const modalCloseBtn     = $('modalCloseBtn');

let currentWorkflow      = null;
let currentFilename      = null;
let currentSessionId     = null;
let appState             = 'idle';
let pendingClarification = null;
let currentProgressEl    = null;
let eventSource          = null;

const uid = () => 'x'.repeat(32).replace(/x/g, () => (Math.random()*16|0).toString(16));
const esc = t => { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; };

// ==================== Init ====================
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    bind();
    loadToken();
    initTextarea();
    if (window.mermaid) {
        try {
            window.mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
        } catch (_) {}
    }
});

// ==================== Token ====================
function getCookie(n) {
    const m = document.cookie.match(new RegExp('(^| )' + n + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : '';
}
function loadToken() {
    if (!bishengTokenInput) return;
    if (getCookie('access_token_cookie')) {
        bishengTokenInput.placeholder = '已保存 — 可重新输入覆盖';
        if (tokenDot) tokenDot.classList.add('ok');
        if (tokenHint) { tokenHint.textContent = '已保存'; tokenHint.style.display = 'block'; }
    }
}
function saveToken() {
    if (!bishengTokenInput) return;
    const v = bishengTokenInput.value.trim();
    if (!v) { if (tokenHint) { tokenHint.textContent = '请输入 Token'; tokenHint.style.display = 'block'; } return; }
    document.cookie = 'access_token_cookie=' + encodeURIComponent(v) + '; path=/; max-age=86400; SameSite=Lax';
    if (tokenDot) tokenDot.classList.add('ok');
    if (tokenHint) { tokenHint.textContent = '已保存'; tokenHint.style.display = 'block'; }
}

// ==================== Textarea ====================
function initTextarea() {
    if (!queryInput) return;
    queryInput.addEventListener('input', () => {
        queryInput.style.height = 'auto';
        queryInput.style.height = Math.min(queryInput.scrollHeight, 150) + 'px';
    });
    queryInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleGenerate(); }
    });
}

// ==================== Bind ====================
function bind() {
    generateBtn.addEventListener('click', handleGenerate);

    if (toggleTokenBtn) toggleTokenBtn.addEventListener('click', () => {
        const on = tokenPanel.style.display === 'none';
        tokenPanel.style.display = on ? 'block' : 'none';
    });
    if (toggleSidebarBtn && sidebar) toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        if (sidebar.classList.contains('open')) {
            showHistoryList();
            loadHistory();
        }
    });

    if (saveTokenBtn)      saveTokenBtn.addEventListener('click', saveToken);
    if (newSessionBtn)     newSessionBtn.addEventListener('click', newSession);
    if (refreshHistoryBtn) refreshHistoryBtn.addEventListener('click', () => { showHistoryList(); loadHistory(); });
    if (historyBackBtn) historyBackBtn.addEventListener('click', showHistoryList);
    if (modalImportBtn)    modalImportBtn.addEventListener('click', doImport);
    if (modalDownloadBtn)  modalDownloadBtn.addEventListener('click', doDownload);
    if (modalCopyBtn)      modalCopyBtn.addEventListener('click', doCopy);
    if (modalCloseBtn)     modalCloseBtn.addEventListener('click', closeJsonModal);
    if (jsonModal)         jsonModal.addEventListener('click', e => { if (e.target === jsonModal) closeJsonModal(); });

    document.querySelectorAll('.chip').forEach(c => {
        c.addEventListener('click', () => { if (queryInput) { queryInput.value = c.dataset.q || ''; queryInput.focus(); } });
    });
}

// ==================== Generate ====================
async function handleGenerate() {
    const q = queryInput.value.trim();
    if (!q) { showErr(appState === 'needs_clarification' ? '请输入补充信息' : '请输入工作流需求描述'); return; }
    hideErr(); removeWelcome(); closePanels();

    if (appState === 'needs_clarification') {
        addUser(q); clearInput(); setInputIdle(); appState = 'streaming'; setLoading(true);
        const orig = (pendingClarification && pendingClarification.original_user_input) || '';
        try { await stream(q, currentSessionId, true, orig); } catch(e) { showErr('续轮失败：'+e.message); addError(e.message); }
        setLoading(false); return;
    }

    hideResult(); appState = 'streaming'; setLoading(true);
    if (!currentSessionId) currentSessionId = uid();
    addUser(q); clearInput();
    try { await stream(q, currentSessionId, false); } catch(e) { showErr('生成失败：'+e.message); addError(e.message); }
    setLoading(false);
}

function clearInput() { if (queryInput) { queryInput.value = ''; queryInput.style.height = 'auto'; } }
function setLoading(on) {
    generateBtn.disabled = on;
    if (sendIcon) sendIcon.style.display = on ? 'none' : '';
    if (sendSpinner) sendSpinner.style.display = on ? 'inline-block' : 'none';
}
function closePanels() {
    if (tokenPanel) tokenPanel.style.display = 'none';
}

// ==================== SSE ====================
function stream(query, sid, resume, originalQuery) {
    return new Promise((resolve, reject) => {
        if (eventSource) { eventSource.close(); eventSource = null; }
        const p = new URLSearchParams({ query });
        if (sid) p.set('session_id', sid);
        if (resume) {
            p.set('is_resume', 'true');
            if (originalQuery) p.set('original_query', originalQuery);
        }
        eventSource = new EventSource('/api/generate/stream?' + p);
        let done = false, progShown = false;

        eventSource.onmessage = ev => {
            try {
                const d = JSON.parse(ev.data);

                if (d.event_type === 'needs_clarification') {
                    done = true; closeSSE();
                    const pay = d.data || {};
                    if (pay.session_id) currentSessionId = pay.session_id;
                    pendingClarification = pay.pending_clarification || {};
                    appState = 'needs_clarification';
                    updateProg('等待补充信息');
                    collapseProc();
                    addClarify(pendingClarification);
                    setInputClarify();
                    setLoading(false);
                    resolve(); return;
                }
                if (d.event_type === 'complete') {
                    done = true; closeSSE();
                    const payload = d.data || {};
                    const hasWorkflow = payload.workflow || payload.status === 'success';
                    if (hasWorkflow) {
                        const resultData = {
                            status: 'success',
                            workflow: payload.workflow,
                            metadata: payload.metadata || {},
                            flow_sketch_mermaid: payload.flow_sketch_mermaid || null,
                            file_path: payload.file_path,
                            import_result: payload.import_result || null,
                        };
                        updateProg('生成完成');
                        finishProc('done');
                        addResult(resultData);
                        showResult(resultData);
                        appState = 'completed';
                    } else { showErr(d.message || '生成失败'); updateProg('失败'); finishProc('err'); }
                    setLoading(false); resolve(); return;
                }
                if (d.event_type === 'error') {
                    done = true; closeSSE();
                    showErr(d.message || d.error || '生成失败');
                    updateProg('失败'); finishProc('err'); setLoading(false);
                    reject(new Error(d.message || d.error || '生成失败')); return;
                }
                if (!progShown) { addProg(); progShown = true; }
                handleProgress(d);
            } catch(_){}
        };
        eventSource.onerror = () => {
            if (!done) { closeSSE(); setLoading(false); reject(new Error('连接服务器失败')); }
        };
    });
}
function closeSSE() { if (eventSource) { eventSource.close(); eventSource = null; } }

// ==================== Progress ====================
let procStepCount = 0;
let procLastAgent = '';

const STEP_ICONS = { waiting: '⏳', running: '⚙️', success: '✅', error: '❌' };

function handleProgress(d) {
    const { event_type, agent_name, message, progress, duration_ms, data: ed, error: err } = d;

    if (!currentProgressEl) return;
    const card = currentProgressEl.querySelector('.proc-card');
    if (!card) return;

    if (progress != null) {
        const fill = card.querySelector('.proc-bar-fill');
        if (fill) fill.style.width = progress + '%';
        const sub = card.querySelector('.proc-sub');
        if (sub) sub.textContent = Math.round(progress) + '%';
    }

    const title = card.querySelector('.proc-title');

    if (!event_type || event_type === 'complete' || event_type === 'error' || event_type === 'needs_clarification') return;

    if (event_type === 'agent_start') {
        procStepCount++;
        procLastAgent = agent_name || '';
        if (title) title.textContent = message || ('正在执行：' + agent_name);
        addStep(card, agent_name, message || ('正在执行：' + agent_name), 'running');
    } else if (event_type === 'agent_complete') {
        if (title) title.textContent = message || (agent_name + ' 完成');
        updateStep(card, agent_name, 'success', message, duration_ms, ed);
    } else if (event_type === 'agent_error') {
        if (title) title.textContent = message || (agent_name + ' 失败');
        updateStep(card, agent_name, 'error', message, duration_ms, { error: err });
    } else if (event_type === 'start') {
        if (title) title.textContent = message || '开始生成';
        addStep(card, '_sys', message || '开始生成', 'running');
    } else if (message) {
        if (title) title.textContent = message;
    }

    scroll();
}

const CHEVRON_SVG = '<svg class="step-chevron" width="12" height="12" viewBox="0 0 12 12"><path d="M4.5 2.5l3.5 3.5-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function addStep(card, agent, msg, status) {
    const list = card.querySelector('.proc-steps');
    if (!list) return;

    if (agent !== '_sys') {
        list.querySelectorAll('.proc-step.has-details:not(.collapsed)').forEach(s => s.classList.add('collapsed'));
    }

    const li = document.createElement('li');
    li.className = 'proc-step';
    li.dataset.agent = agent || '';
    li.innerHTML =
        '<div class="step-header">' +
            '<span class="step-icon ' + status + '">' + (STEP_ICONS[status] || '·') + '</span>' +
            '<span class="step-msg">' + esc(msg) + '</span>' +
            CHEVRON_SVG +
        '</div>' +
        '<div class="step-collapse"></div>';
    li.querySelector('.step-header')?.addEventListener('click', () => {
        if (li.classList.contains('has-details')) li.classList.toggle('collapsed');
    });
    list.appendChild(li);
}

function updateStep(card, agent, status, msg, dur, details) {
    const list = card.querySelector('.proc-steps');
    if (!list) return;
    const items = list.querySelectorAll('.proc-step[data-agent="' + (agent || '') + '"]');
    const li = items.length ? items[items.length - 1] : list.lastElementChild;
    if (!li) return;

    const icon = li.querySelector('.step-icon');
    if (icon) { icon.className = 'step-icon ' + status; icon.textContent = STEP_ICONS[status] || '·'; }
    if (msg) { const m = li.querySelector('.step-msg'); if (m) m.textContent = msg; }

    if (dur != null) {
        const hdr = li.querySelector('.step-header');
        let durEl = li.querySelector('.step-dur');
        if (!durEl && hdr) {
            durEl = document.createElement('span');
            durEl.className = 'step-dur';
            hdr.insertBefore(durEl, hdr.querySelector('.step-chevron'));
        }
        if (durEl) durEl.textContent = (dur / 1000).toFixed(1) + 's';
    }

    let detailHtml = '';
    if (details) {
        const lines = [];
        if (details.workflow_type) lines.push('类型: <span class="detail-names">' + esc(details.workflow_type) + '</span>');
        if (details.rewritten_input) lines.push('改写: ' + esc(details.rewritten_input));

        if (details.tools_count !== undefined) {
            let toolLine = '工具: <span class="detail-names">' + details.tools_count + ' 个</span>';
            if (details.selected_tools && details.selected_tools.length) {
                const names = details.selected_tools.map(t => t.name || t.description || '').filter(Boolean);
                if (names.length) toolLine += ' — ' + names.map(n => '<span class="detail-names">' + esc(n) + '</span>').join('、');
            }
            lines.push(toolLine);
        }

        if (details.knowledge_count !== undefined) {
            let kbLine = '知识库: <span class="detail-names">' + details.knowledge_count + ' 个</span>';
            if (details.matched_knowledge_bases && details.matched_knowledge_bases.length) {
                const names = details.matched_knowledge_bases.map(k => k.name || k.description || '').filter(Boolean);
                if (names.length) kbLine += ' — ' + names.map(n => '<span class="detail-names">' + esc(n) + '</span>').join('、');
            }
            lines.push(kbLine);
        }

        if (details.error) lines.push('错误: ' + esc(details.error));
        if (details.message && details.degraded) lines.push(esc(details.message));
        if (lines.length) detailHtml = lines.join('<br>');
    }

    const collapse = li.querySelector('.step-collapse');
    if (detailHtml && collapse) {
        let det = collapse.querySelector('.step-detail');
        if (!det) { det = document.createElement('div'); det.className = 'step-detail'; collapse.appendChild(det); }
        det.innerHTML = detailHtml;
        li.classList.add('has-details');
    }

    if (details && details.flow_sketch_mermaid && typeof window.mermaid !== 'undefined' && collapse) {
        let mwrap = collapse.querySelector('.step-mermaid');
        if (!mwrap) {
            mwrap = document.createElement('div');
            mwrap.className = 'step-mermaid res-mermaid-wrap mermaid-collapsible';
            mwrap.innerHTML =
                '<div class="mermaid-toggle-bar">' +
                    '<span class="mermaid-toggle-label">流程图草图</span>' +
                    '<svg class="mermaid-chevron" width="14" height="14" viewBox="0 0 14 14"><path d="M5.25 2.9l4.1 4.1-4.1 4.1" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
                '</div>' +
                '<div class="mermaid-content"><pre class="mermaid">' + esc(details.flow_sketch_mermaid) + '</pre></div>';
            collapse.appendChild(mwrap);
            li.classList.add('has-details');
            mwrap.querySelector('.mermaid-toggle-bar')?.addEventListener('click', function(e) {
                e.stopPropagation();
                mwrap.classList.toggle('collapsed');
            });
            var mNodes = mwrap.querySelectorAll('.mermaid');
            if (mNodes.length) {
                window.mermaid.run({ nodes: mNodes }).catch(function() {});
            }
        }
    }
}

function collapseProc() {
    if (!currentProgressEl) return;
    const card = currentProgressEl.querySelector('.proc-card');
    if (card) card.classList.add('collapsed');
}

function finishProc(status) {
    if (!currentProgressEl) return;
    const card = currentProgressEl.querySelector('.proc-card');
    if (!card) return;
    const icon = card.querySelector('.proc-icon');
    if (status === 'done') {
        card.classList.add('done');
        if (icon) { icon.className = 'proc-icon done'; icon.textContent = '✅'; }
    } else if (status === 'err') {
        if (icon) { icon.className = 'proc-icon err'; icon.textContent = '❌'; }
    }
}

// ==================== Chat Helpers ====================
function scroll() { if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight; }
function removeWelcome() { if (welcomeBlock && welcomeBlock.parentNode) welcomeBlock.remove(); }

function addUser(txt) {
    const el = document.createElement('div');
    el.className = 'msg msg-user';
    el.innerHTML = '<div class="bubble">' + esc(txt) + '</div>';
    chatMessages.appendChild(el); scroll();
}

function addProg() {
    procStepCount = 0; procLastAgent = '';
    const el = document.createElement('div');
    el.className = 'msg msg-progress';
    el.innerHTML =
        '<div class="proc-card">' +
            '<div class="proc-head">' +
                '<div class="proc-left">' +
                    '<span class="proc-icon">⚙️</span>' +
                    '<span class="proc-title">正在生成工作流…</span>' +
                    '<span class="proc-sub"></span>' +
                '</div>' +
                '<button class="proc-toggle" aria-label="折叠">▾</button>' +
            '</div>' +
            '<div class="proc-bar"><div class="proc-bar-fill"></div></div>' +
            '<div class="proc-body"><ul class="proc-steps"></ul></div>' +
        '</div>';
    chatMessages.appendChild(el);
    currentProgressEl = el;
    el.querySelector('.proc-head')?.addEventListener('click', () => {
        el.querySelector('.proc-card')?.classList.toggle('collapsed');
    });
    scroll();
}

function updateProg(txt) {
    if (!currentProgressEl) return;
    const title = currentProgressEl.querySelector('.proc-title');
    if (title) title.textContent = txt;
    scroll();
}

function addAssistantMessage(content) {
    if (!content) return;
    const el = document.createElement('div');
    el.className = 'msg msg-ast';
    el.innerHTML = '<div class="bubble">' + esc(content) + '</div>';
    chatMessages.appendChild(el);
    scroll();
}

function addClarify(p) {
    const msg = p.message || '请补充以下信息';
    const qs = p.questions || [];
    let h = '<div class="bubble"><div class="clarify-tag">需要补充</div>';
    h += '<div style="font-size:15px;margin-bottom:6px">' + esc(msg) + '</div>';
    if (qs.length) { h += '<ul class="clarify-list">'; qs.forEach(q => h += '<li>' + esc(q) + '</li>'); h += '</ul>'; }
    h += '</div>';
    const el = document.createElement('div');
    el.className = 'msg msg-ast msg-clarify';
    el.innerHTML = h;
    chatMessages.appendChild(el); scroll();
}

function addResult(data) {
    const ty = data.metadata?.intent?.workflow_type || '工作流';
    const m = data.metadata || {};
    const toolsCount = m.tools_count ?? 0;
    const kbCount = m.knowledge_count ?? 0;

    let h = '<div class="res-card-inline">';
    h += '<div class="res-header"><span class="res-icon">✅</span><span class="res-title">工作流已生成</span></div>';

    h += '<div class="res-meta-grid">';
    h += '<div class="res-meta-item"><span class="res-meta-label">类型</span><span class="res-meta-val">' + esc(ty) + '</span></div>';
    h += '<div class="res-meta-item"><span class="res-meta-label">工具</span><span class="res-meta-val">' + toolsCount + ' 个</span></div>';
    h += '<div class="res-meta-item"><span class="res-meta-label">知识库</span><span class="res-meta-val">' + kbCount + ' 个</span></div>';
    h += '</div>';

    if (data.flow_sketch_mermaid && data.flow_sketch_mermaid.trim()) {
        h += '<div class="res-mermaid-wrap mermaid-collapsible">' +
            '<div class="mermaid-toggle-bar">' +
                '<span class="mermaid-toggle-label">流程图草图</span>' +
                '<svg class="mermaid-chevron" width="14" height="14" viewBox="0 0 14 14"><path d="M5.25 2.9l4.1 4.1-4.1 4.1" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
            '</div>' +
            '<div class="mermaid-content"><pre class="mermaid">' + esc(data.flow_sketch_mermaid) + '</pre></div>' +
        '</div>';
    }

    const ir = data.import_result || {};
    const hasChat = ir.chat_url;
    const hasEdit = ir.flow_edit_url;
    h += '<div class="res-actions">';
    h += '<button class="btn btn-primary btn-sm _imp"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>导入到毕昇</button>';
    if (hasChat) h += '<a class="btn btn-sm _chat" href="' + esc(ir.chat_url) + '" target="_blank" rel="noopener">打开对话</a>';
    if (hasEdit) h += '<a class="btn btn-sm _edit" href="' + esc(ir.flow_edit_url) + '" target="_blank" rel="noopener">编辑工作流</a>';
    h += '<button class="btn btn-sm _dl"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>下载</button>';
    h += '<button class="btn btn-sm _cp"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>复制</button>';
    h += '<button class="btn btn-sm _json"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>查看 JSON</button>';
    h += '</div>';
    h += '</div>';

    const el = document.createElement('div');
    el.className = 'msg msg-result-card';
    el.innerHTML = h;
    el.querySelector('._imp')?.addEventListener('click', doImport);
    el.querySelector('._dl')?.addEventListener('click', doDownload);
    el.querySelector('._cp')?.addEventListener('click', doCopy);
    el.querySelector('._json')?.addEventListener('click', openJsonModal);
    chatMessages.appendChild(el);
    if (data.flow_sketch_mermaid && typeof window.mermaid !== 'undefined') {
        var mwrap = el.querySelector('.mermaid-collapsible');
        if (mwrap) {
            mwrap.querySelector('.mermaid-toggle-bar')?.addEventListener('click', function() {
                mwrap.classList.toggle('collapsed');
            });
        }
        var mermaidNodes = el.querySelectorAll('.mermaid');
        if (mermaidNodes.length) {
            window.mermaid.run({ nodes: mermaidNodes }).catch(function() {});
        }
    }
    scroll();
}

function addError(msg) {
    const el = document.createElement('div');
    el.className = 'msg msg-ast msg-error';
    el.innerHTML = '<div class="bubble">' + esc(msg) + '</div>';
    chatMessages.appendChild(el); scroll();
}

// ==================== Input state ====================
function setInputIdle() {
    if (queryInput) queryInput.placeholder = '描述你想创建的工作流...';
    if (inputHint) inputHint.textContent = 'Enter 发送 · Shift+Enter 换行';
}
function setInputClarify() {
    if (queryInput) { queryInput.placeholder = '请补充信息以继续…'; queryInput.focus(); }
    if (inputHint) inputHint.textContent = '输入补充信息后按 Enter 发送';
}
function newSession() {
    if (chatMessages) {
        chatMessages.innerHTML = '';
        const w = document.createElement('div');
        w.className = 'welcome'; w.id = 'welcomeBlock';
        w.innerHTML =
            '<div class="w-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>' +
            '<h1 class="w-title">你想创建什么工作流？</h1>' +
            '<p class="w-desc">描述你的需求，AI 将自动生成毕昇平台工作流。<br>支持多轮对话，模糊需求会先澄清再生成。</p>' +
            '<div class="w-chips">' +
            '<button type="button" class="chip" data-q="创建一个深汕招商政策查询助手">招商政策查询助手</button>' +
            '<button type="button" class="chip" data-q="做一个天气查询工作流">天气查询工作流</button>' +
            '<button type="button" class="chip" data-q="创建一个智能客服机器人">智能客服机器人</button>' +
            '</div>';
        chatMessages.appendChild(w);
        w.querySelectorAll('.chip').forEach(c => {
            c.addEventListener('click', () => { if (queryInput) { queryInput.value = c.dataset.q || ''; queryInput.focus(); } });
        });
    }
    currentSessionId = null; appState = 'idle'; pendingClarification = null; currentProgressEl = null;
    setInputIdle(); hideErr(); hideResult(); setLoading(false);
}

// ==================== UI Helpers ====================
function showErr(m) { if (errorBar) { errorBar.textContent = m; errorBar.style.display = 'block'; setTimeout(hideErr, 5000); } }
function hideErr() { if (errorBar) errorBar.style.display = 'none'; }

function showResult(data) {
    currentWorkflow = data.workflow;
    currentFilename = data.file_path ? data.file_path.split(/[\\/]/).pop() : null;
    if (data.workflow && jsonContent) jsonContent.textContent = JSON.stringify(data.workflow, null, 2);
    loadHistory();
}
function hideResult() { closeJsonModal(); currentWorkflow = null; currentFilename = null; }

function openJsonModal() {
    if (!currentWorkflow) { showErr('没有可查看的工作流'); return; }
    if (jsonContent) jsonContent.textContent = JSON.stringify(currentWorkflow, null, 2);
    if (jsonModal) { jsonModal.style.display = 'flex'; }
}
function closeJsonModal() {
    if (jsonModal) jsonModal.style.display = 'none';
}

// ==================== Import / Download / Copy ====================
async function doImport() {
    if (!currentWorkflow) { showErr('没有可导入的工作流'); return; }
    hideErr();
    try {
        const r = await fetch('/api/workflow/import', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
            body: JSON.stringify({ workflow: currentWorkflow, publish: true }),
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) { const det = d.detail || d.message || '导入失败'; showErr(typeof det === 'string' ? det : JSON.stringify(det)); return; }
        const ir = d.import_result || {};
        toast(d.message || '已导入到毕昇');
        if (ir.chat_url || ir.flow_edit_url) {
            const actions = document.querySelector('.msg-result-card:last-child .res-actions');
            if (actions && !actions.querySelector('._chat')) {
                const imp = actions.querySelector('._imp');
                const ref = imp ? imp.nextSibling : actions.firstChild;
                if (ir.chat_url) {
                    const a = document.createElement('a');
                    a.className = 'btn btn-sm _chat'; a.href = ir.chat_url; a.target = '_blank'; a.rel = 'noopener';
                    a.textContent = '打开对话';
                    actions.insertBefore(a, ref);
                }
                if (ir.flow_edit_url) {
                    const a = document.createElement('a');
                    a.className = 'btn btn-sm _edit'; a.href = ir.flow_edit_url; a.target = '_blank'; a.rel = 'noopener';
                    a.textContent = '编辑工作流';
                    const after = actions.querySelector('._chat') || actions.querySelector('._imp');
                    actions.insertBefore(a, after ? after.nextSibling : actions.firstChild);
                }
            }
        }
    } catch(e) { showErr('导入失败：' + e.message); }
}
function doDownload() {
    if (!currentWorkflow) { showErr('没有可下载的工作流'); return; }
    const b = new Blob([JSON.stringify(currentWorkflow, null, 2)], { type: 'application/json' });
    const u = URL.createObjectURL(b);
    const a = document.createElement('a'); a.href = u; a.download = currentFilename || 'workflow.json';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(u);
    toast('下载成功');
}
async function doCopy() {
    if (!currentWorkflow) { showErr('没有可复制的内容'); return; }
    try { await navigator.clipboard.writeText(JSON.stringify(currentWorkflow, null, 2)); toast('已复制到剪贴板'); }
    catch(_) { showErr('复制失败'); }
}

// ==================== History (会话列表 + 主区展示) ====================
function showHistoryList() {
    if (sessionDetail) sessionDetail.style.display = 'none';
    if (historyList) historyList.style.display = 'block';
    if (historyBackBtn) historyBackBtn.style.display = 'none';
    if (historyPanelTitle) historyPanelTitle.textContent = '历史会话';
}

function showSessionDetail() {
    if (historyList) historyList.style.display = 'none';
    if (sessionDetail) sessionDetail.style.display = 'block';
    if (historyBackBtn) historyBackBtn.style.display = 'inline-block';
    if (historyPanelTitle) historyPanelTitle.textContent = '会话详情';
}

/** 将时间线重放到主对话框，含完整结果卡片（导入/打开对话/编辑工作流） */
function renderTimelineIntoMainArea(timeline) {
    if (!chatMessages) return;
    chatMessages.innerHTML = '';
    if (!timeline.length) return;

    let lastCompleteData = null;
    for (const item of timeline) {
        const payload = item.payload || {};
        if (item.item_type === 'message') {
            const role = payload.role || 'user';
            const content = payload.content || '';
            if (role === 'user') addUser(content);
            else addAssistantMessage(content);
            continue;
        }
        if (item.item_type === 'progress_event') {
            const ev = payload;
            const eventType = ev.event_type || '';
            if (eventType === 'needs_clarification' && ev.data && ev.data.pending_clarification) {
                addClarify(ev.data.pending_clarification);
            } else if (eventType === 'complete' && ev.data && ev.data.workflow) {
                lastCompleteData = ev.data;
                addResult(ev.data);
            } else if (eventType === 'error' && ev.error) {
                addError(ev.error);
            } else if (eventType && eventType !== 'start' && eventType !== 'complete') {
                const el = document.createElement('div');
                el.className = 'msg msg-ast';
                el.innerHTML = '<div class="bubble tl-ev-inline">' +
                    '<span class="tl-ev-type">' + esc(eventType) + '</span>' +
                    (ev.agent_name ? ' <span class="tl-ev-agent">' + esc(ev.agent_name) + '</span>' : '') +
                    (ev.message ? ' — ' + esc(ev.message) : '') + '</div>';
                chatMessages.appendChild(el);
            }
        }
    }
    if (lastCompleteData) {
        currentWorkflow = lastCompleteData.workflow;
        currentFilename = lastCompleteData.file_path ? lastCompleteData.file_path.split(/[\\/]/).pop() : null;
        if (currentWorkflow && jsonContent) jsonContent.textContent = JSON.stringify(currentWorkflow, null, 2);
    }
    scroll();
}

async function loadHistory() {
    if (!historyList) return;
    showHistoryList();
    try {
        const r = await fetch('/api/sessions');
        if (!r.ok) throw new Error('加载失败');
        const list = await r.json();
        if (!list.length) {
            historyList.innerHTML = '<p class="hist-empty">暂无会话记录</p><p class="hist-hint">配置 MySQL 并生成工作流后，会话将在此展示</p>';
            return;
        }
        historyList.innerHTML = list.map(s => {
            const lastAt = s.last_at ? new Date(s.last_at).toLocaleString('zh-CN') : '';
            const preview = (s.preview || s.session_id || '').slice(0, 60);
            return '<div class="hist-item hist-session" data-session-id="' + esc(s.session_id) + '">' +
                '<div class="hist-left">' +
                '<div class="hist-name">' + esc(preview) + (preview.length >= 60 ? '…' : '') + '</div>' +
                '<div class="hist-meta">' + esc(lastAt) + '</div>' +
                '</div>' +
                '<div class="hist-right">' +
                '<button type="button" class="btn btn-sm btn-view-session">查看</button>' +
                '</div></div>';
        }).join('');
        historyList.querySelectorAll('.hist-session').forEach(item => {
            const sessionId = item.dataset.sessionId;
            if (!sessionId) return;
            const go = () => { loadSessionDetail(sessionId); };
            item.querySelector('.btn-view-session')?.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); go(); });
            item.addEventListener('click', e => { if (!e.target.closest('.btn-view-session')) go(); });
        });
    } catch (e) {
        historyList.innerHTML = '<p class="hist-error">' + esc(e.message) + '</p>';
    }
}

async function loadSessionDetail(sessionId) {
    try {
        const r = await fetch('/api/sessions/' + encodeURIComponent(sessionId));
        if (!r.ok) throw new Error('加载失败');
        const data = await r.json();
        const timeline = data.timeline || [];
        if (!timeline.length) {
            toast('该会话暂无记录', 'err');
            return;
        }
        currentSessionId = sessionId;
        appState = 'completed';
        hideErr();
        renderTimelineIntoMainArea(timeline);
        showHistoryList();
        if (sidebar) sidebar.classList.remove('open');
    } catch (e) {
        toast('加载失败：' + e.message, 'err');
    }
}

function renderTimelineItem(item) {
    const payload = item.payload || {};
    if (item.item_type === 'message') {
        const role = payload.role || 'user';
        const content = payload.content || '';
        const cls = role === 'user' ? 'msg msg-user' : 'msg msg-ast';
        return '<div class="tl-item tl-msg ' + cls + '"><div class="bubble">' + esc(content) + '</div></div>';
    }
    if (item.item_type === 'progress_event') {
        const ev = payload;
        const eventType = ev.event_type || '';
        const msg = ev.message || '';
        const agentName = ev.agent_name || '';
        const progress = ev.progress != null ? Math.round(ev.progress) + '%' : '';
        const duration = ev.duration_ms != null ? (ev.duration_ms / 1000).toFixed(1) + 's' : '';
        const err = ev.error ? '<div class="tl-ev-error">' + esc(ev.error) + '</div>' : '';
        let dataHtml = '';
        if (ev.data && typeof ev.data === 'object') {
            if (ev.data.workflow) dataHtml = '<span class="tl-ev-data">含工作流结果</span>';
            else if (ev.data.pending_clarification) dataHtml = '<span class="tl-ev-data">需澄清</span>';
            else if (Object.keys(ev.data).length) dataHtml = '<span class="tl-ev-data">' + esc(JSON.stringify(ev.data).slice(0, 80)) + '</span>';
        }
        return '<div class="tl-item tl-event" data-type="' + esc(eventType) + '">' +
            '<div class="tl-ev-head">' +
            '<span class="tl-ev-type">' + esc(eventType) + '</span>' +
            (agentName ? '<span class="tl-ev-agent">' + esc(agentName) + '</span>' : '') +
            (progress ? '<span class="tl-ev-progress">' + progress + '</span>' : '') +
            (duration ? '<span class="tl-ev-dur">' + duration + '</span>' : '') +
            '</div>' +
            '<div class="tl-ev-msg">' + esc(msg) + '</div>' +
            (dataHtml ? '<div class="tl-ev-detail">' + dataHtml + '</div>' : '') +
            err + '</div>';
    }
    return '';
}
async function viewWf(fn) {
    try {
        const r = await fetch('/api/workflow/' + fn);
        if (!r.ok) throw new Error('加载失败');
        const d = await r.json();
        currentWorkflow = d.workflow; currentFilename = d.filename;
        openJsonModal();
        toast('已加载');
    } catch(e) { showErr('查看失败：' + e.message); }
}
async function dlWf(fn) {
    try {
        const r = await fetch('/api/download/' + fn);
        if (!r.ok) throw new Error('下载失败');
        const b = await r.blob(); const u = URL.createObjectURL(b);
        const a = document.createElement('a'); a.href = u; a.download = fn;
        document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(u);
        toast('下载成功');
    } catch(e) { showErr('下载失败：' + e.message); }
}

// ==================== Toast ====================
function toast(msg, type) {
    let wrap = document.querySelector('.toast-wrap');
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'toast-wrap'; document.body.appendChild(wrap); }
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type === 'err' ? 'err' : 'ok');
    t.textContent = msg;
    wrap.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

window.viewWf = viewWf;
window.dlWf = dlWf;
