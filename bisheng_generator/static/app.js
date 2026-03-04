// 毕昇工作流生成器 - 前端交互逻辑

// DOM 元素
const queryInput = document.getElementById('queryInput');
const generateBtn = document.getElementById('generateBtn');
const loading = document.getElementById('loading');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const progressLogs = document.getElementById('progressLogs');
const error = document.getElementById('error');
const result = document.getElementById('result');
const jsonContent = document.getElementById('jsonContent');
const metadata = document.getElementById('metadata');
const downloadBtn = document.getElementById('downloadBtn');
const copyBtn = document.getElementById('copyBtn');
const toggleJsonBtn = document.getElementById('toggleJsonBtn');
const historyList = document.getElementById('historyList');
const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

// 当前生成的工作流
let currentWorkflow = null;
let currentFilename = null;

// SSE 连接
let eventSource = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    setupEventListeners();
});

// 设置事件监听
function setupEventListeners() {
    generateBtn.addEventListener('click', handleGenerate);
    downloadBtn.addEventListener('click', handleDownload);
    copyBtn.addEventListener('click', handleCopy);
    toggleJsonBtn.addEventListener('click', handleToggleJson);
    refreshHistoryBtn.addEventListener('click', loadHistory);
}

// 处理生成请求
async function handleGenerate() {
    const query = queryInput.value.trim();

    if (!query) {
        showError('请输入工作流需求描述');
        return;
    }

    // 重置状态
    hideError();
    hideResult();
    hideProgress();
    showLoading();
    disableGenerateBtn(true);

    try {
        // 使用 SSE 流式生成
        await generateWithSSE(query);
    } catch (err) {
        console.error('生成失败:', err);
        showError(`生成失败：${err.message}`);
        hideLoading();
        hideProgress();
        disableGenerateBtn(false);
    }
}

// 使用 SSE 进行流式生成
async function generateWithSSE(query) {
    return new Promise((resolve, reject) => {
        // 如果已有连接，强行关闭
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }

        // 使用 URL 查询参数传递 query（EventSource 不支持自定义 headers）
        const url = `/api/generate/stream?query=${encodeURIComponent(query)}`;
        eventSource = new EventSource(url);

        let isComplete = false;

        // 统一消息处理器
        const handleMessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('收到 SSE 消息:', data.event_type, data.message);

                // 根据事件类型处理
                if (data.event_type === 'complete') {
                    // 完成事件
                    isComplete = true;
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                    hideLoading();
                    hideProgress();

                    if (data.data && data.data.status === 'success') {
                        showResult(data.data);
                    } else {
                        showError(data.message || '生成失败');
                    }
                    disableGenerateBtn(false);
                    resolve();
                } else if (data.event_type === 'error') {
                    // 错误事件
                    isComplete = true;
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                    hideLoading();
                    hideProgress();
                    showError(data.message || data.error || '生成失败');
                    disableGenerateBtn(false);
                    reject(new Error(data.message || data.error || '生成失败'));
                } else {
                    // 进度事件（start, agent_start, agent_complete 等）
                    handleProgressEvent(data);
                }
            } catch (err) {
                console.error('解析 SSE 消息失败:', err);
                // 这里暂时不 reject，避免意外干扰进度推送
            }
        };

        // 监听所有消息
        eventSource.onmessage = handleMessage;

        // 连接错误处理
        eventSource.onerror = (err) => {
            console.error('SSE 连接错误:', err);
            // 只有在未完成的情况下才处理连接错误报错
            if (!isComplete) {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                hideLoading();
                hideProgress();
                disableGenerateBtn(false);
                reject(new Error('连接服务器失败'));
            }
        };
    });
}

// 处理进度事件
function handleProgressEvent(data) {
    const { event_type, agent_name, message, progress, data: eventData, duration_ms, error } = data;

    // 显示进度区域
    progressSection.style.display = 'block';

    // 更新进度条
    if (progress !== undefined && progress !== null) {
        updateProgressBar(progress);
    }

    // 添加日志项
    if (event_type === 'agent_start') {
        addProgressLog(message, 'running', agent_name);
    } else if (event_type === 'agent_complete') {
        updateLog(agent_name, 'success', message, eventData, duration_ms);
    } else if (event_type === 'agent_error') {
        updateLog(agent_name, 'error', message, { error }, duration_ms);
    } else if (event_type === 'start') {
        addProgressLog(message, 'running', 'system_start');
    } else if (event_type === 'complete') {
        updateLog('system_start', 'success', message, eventData);
    } else if (event_type === 'error') {
        updateLog(null, 'error', message, { error });
    }
}

// 更新进度条
function updateProgressBar(percent) {
    progressBar.style.width = `${percent}%`;
    progressPercent.textContent = `${Math.round(percent)}%`;
}

// 添加进度日志
function addProgressLog(message, status = 'waiting', agentName = null) {
    const logItem = document.createElement('div');
    logItem.className = `progress-log-item ${status}`;
    logItem.dataset.agent = agentName || 'unknown';

    const icon = getIconForStatus(status);

    logItem.innerHTML = `
        <div class="progress-log-icon">${icon}</div>
        <div class="progress-log-content">
            <div class="progress-log-message">${escapeHtml(message)}</div>
        </div>
    `;

    progressLogs.appendChild(logItem);
    scrollToBottom();
}

// 更新指定的日志项（支持并行定位）
function updateLog(agentName, status, message, details = null, durationMs = null) {
    let targetLog = null;

    if (agentName) {
        // 查找属于该 agent 且处于非完成状态的最后一条日志
        const agentLogs = Array.from(progressLogs.querySelectorAll(`.progress-log-item[data-agent="${agentName}"]`));
        targetLog = agentLogs[agentLogs.length - 1];
    }

    // 如果找不到指定的，或者没有 agentName，则回退到最后一条
    if (!targetLog) {
        targetLog = progressLogs.lastElementChild;
    }

    if (!targetLog) return;

    // 更新状态类
    targetLog.className = `progress-log-item ${status}`;

    // 更新图标
    const iconEl = targetLog.querySelector('.progress-log-icon');
    if (iconEl) {
        iconEl.textContent = getIconForStatus(status);
    }

    // 更新消息
    const messageEl = targetLog.querySelector('.progress-log-message');
    if (messageEl) {
        messageEl.textContent = message;
    }

    // 添加详情
    if (details || durationMs) {
        // 先检查是否已经存在详情区域，如果有则追加或替换（防止并行数据堆叠在同一个 DOM 里）
        let detailsDiv = targetLog.querySelector('.progress-log-details');
        if (!detailsDiv) {
            detailsDiv = document.createElement('div');
            detailsDiv.className = 'progress-log-details';
            targetLog.querySelector('.progress-log-content').appendChild(detailsDiv);
        }

        let detailsHtml = '';

        // 如果是追加模式，保留旧内容（可选，这里我们根据 agent_complete 的逻辑覆盖）
        // 但为了防止并行时数据被覆盖，我们重新构建

        // 添加耗时
        if (durationMs !== null && durationMs !== undefined) {
            detailsHtml += `<span class="progress-log-duration">耗时：${(durationMs / 1000).toFixed(1)}s</span>`;
        }

        // 添加详情数据
        if (details) {
            const detailItems = [];
            if (details.workflow_type) {
                detailItems.push(`类型：${details.workflow_type}`);
            }
            if (details.tools_count !== undefined) {
                detailItems.push(`工具数：${details.tools_count}`);
            }
            if (details.knowledge_count !== undefined) {
                detailItems.push(`知识库数：${details.knowledge_count}`);
            }
            if (details.selected_tools && details.selected_tools.length > 0) {
                const toolNames = details.selected_tools.map(t => t.name).join(', ');
                detailItems.push(`工具：${toolNames}`);
            }
            if (details.matched_knowledge_bases && details.matched_knowledge_bases.length > 0) {
                const kbNames = details.matched_knowledge_bases.map(k => k.name).join(', ');
                detailItems.push(`知识库：${kbNames}`);
            }
            if (details.error) {
                detailItems.push(`错误：${details.error}`);
            }

            if (detailItems.length > 0) {
                detailsHtml += (detailsHtml ? ' | ' : '') + detailItems.join(' | ');
            }
        }

        // 注意：这里用 innerHTML 可能会覆盖之前的 details，
        // 在并行场景下，我们需要确保每个 Agent 只更新自己的 row。
        detailsDiv.innerHTML = detailsHtml;
    }

    scrollToBottom();
}

// 获取状态图标
function getIconForStatus(status) {
    const icons = {
        'waiting': '⏳',
        'running': '⚙️',
        'success': '✅',
        'error': '❌'
    };
    return icons[status] || '•';
}

// 滚动到底部
function scrollToBottom() {
    progressLogs.scrollTop = progressLogs.scrollHeight;
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 隐藏进度区域
function hideProgress() {
    progressSection.style.display = 'none';
    progressLogs.innerHTML = '';
    progressBar.style.width = '0%';
    progressPercent.textContent = '0%';
}

// 显示加载动画
function showLoading() {
    loading.style.display = 'block';
    generateBtn.querySelector('.btn-text').style.display = 'none';
    generateBtn.querySelector('.btn-loading').style.display = 'inline';
}

// 隐藏加载动画
function hideLoading() {
    loading.style.display = 'none';
    generateBtn.querySelector('.btn-text').style.display = 'inline';
    generateBtn.querySelector('.btn-loading').style.display = 'none';
}

// 禁用生成按钮
function disableGenerateBtn(disabled) {
    generateBtn.disabled = disabled;
}

// 显示错误
function showError(message) {
    error.textContent = message;
    error.style.display = 'block';
}

// 隐藏错误
function hideError() {
    error.style.display = 'none';
}

// 显示结果
function showResult(data) {
    currentWorkflow = data.workflow;
    currentFilename = data.file_path ? data.file_path.split('/').pop() : null;

    // 显示元数据
    if (data.metadata) {
        let metadataHtml = '';

        if (data.metadata.intent) {
            metadataHtml += `
                <div class="metadata-item">
                    <span class="metadata-label">工作流类型:</span>
                    <span class="metadata-value">${data.metadata.intent.workflow_type || '未知'}</span>
                </div>
            `;
        }

        if (data.metadata.tools_count !== undefined) {
            metadataHtml += `
                <div class="metadata-item">
                    <span class="metadata-label">选中工具数:</span>
                    <span class="metadata-value">${data.metadata.tools_count}</span>
                </div>
            `;
        }

        if (data.metadata.knowledge_count !== undefined) {
            metadataHtml += `
                <div class="metadata-item">
                    <span class="metadata-label">匹配知识库数:</span>
                    <span class="metadata-value">${data.metadata.knowledge_count}</span>
                </div>
            `;
        }

        metadata.innerHTML = metadataHtml;
    }

    // 显示 JSON
    if (data.workflow) {
        jsonContent.textContent = JSON.stringify(data.workflow, null, 2);
    }

    // 显示结果区域
    result.style.display = 'block';

    // 滚动到结果区域
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // 刷新历史列表
    loadHistory();
}

// 隐藏结果
function hideResult() {
    result.style.display = 'none';
    currentWorkflow = null;
    currentFilename = null;
}

// 处理下载
function handleDownload() {
    if (!currentWorkflow || !currentFilename) {
        showError('没有可下载的工作流');
        return;
    }

    // 创建下载链接
    const blob = new Blob([JSON.stringify(currentWorkflow, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('下载成功！');
}

// 处理复制
async function handleCopy() {
    if (!currentWorkflow) {
        showError('没有可复制的内容');
        return;
    }

    try {
        await navigator.clipboard.writeText(JSON.stringify(currentWorkflow, null, 2));
        showToast('已复制到剪贴板！');
    } catch (err) {
        console.error('复制失败:', err);
        showError('复制失败，请手动复制');
    }
}

// 处理切换 JSON 显示
function handleToggleJson() {
    jsonContent.parentElement.classList.toggle('collapsed');
}

// 加载历史工作流列表
async function loadHistory() {
    try {
        const response = await fetch('/api/workflows');
        if (!response.ok) {
            throw new Error('加载失败');
        }

        const workflows = await response.json();

        if (workflows.length === 0) {
            historyList.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">暂无历史工作流</p>';
            return;
        }

        historyList.innerHTML = workflows.map(wf => {
            const date = new Date(wf.created_at * 1000);
            const dateStr = date.toLocaleString('zh-CN');
            const sizeStr = (wf.size / 1024).toFixed(2) + ' KB';

            return `
                <div class="history-item">
                    <div class="history-info">
                        <div class="history-filename">${wf.filename}</div>
                        <div class="history-meta">
                            创建时间：${dateStr} | 大小：${sizeStr}
                        </div>
                    </div>
                    <div class="history-actions">
                        <button class="btn btn-sm btn-secondary" onclick="viewWorkflow('${wf.filename}')">查看</button>
                        <button class="btn btn-sm btn-success" onclick="downloadWorkflow('${wf.filename}')">下载</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('加载历史失败:', err);
        historyList.innerHTML = `<p style="color: var(--error-color); text-align: center; padding: 2rem;">加载失败：${err.message}</p>`;
    }
}

// 查看工作流（全局函数）
async function viewWorkflow(filename) {
    try {
        const response = await fetch(`/api/workflow/${filename}`);
        if (!response.ok) {
            throw new Error('加载失败');
        }

        const data = await response.json();

        // 显示工作流
        currentWorkflow = data.workflow;
        currentFilename = data.filename;

        jsonContent.textContent = JSON.stringify(data.workflow, null, 2);
        result.style.display = 'block';
        result.scrollIntoView({ behavior: 'smooth', block: 'start' });

        showToast('工作流加载成功！');
    } catch (err) {
        console.error('查看失败:', err);
        showError(`查看失败：${err.message}`);
    }
}

// 下载工作流（全局函数）
async function downloadWorkflow(filename) {
    try {
        const response = await fetch(`/api/download/${filename}`);
        if (!response.ok) {
            throw new Error('下载失败');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('下载成功！');
    } catch (err) {
        console.error('下载失败:', err);
        showError(`下载失败：${err.message}`);
    }
}

// 显示成功提示
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// 将函数暴露到全局作用域
window.viewWorkflow = viewWorkflow;
window.downloadWorkflow = downloadWorkflow;
