/**
 * RAG 知识库问答系统 - Vue 3 应用
 * 功能：知识库管理、文档管理、问答对话
 */

const { createApp, ref, computed, onMounted, nextTick } = Vue;

// 注册所有 Element Plus 图标
const icons = ElementPlusIconsVue || {};

const app = createApp({
  setup() {
    // ==================== 状态管理 ====================
    const currentView = ref('knowledge-base');
    const knowledgeBases = ref([]);
    const documents = ref([]);
    const selectedKbId = ref(null);
    const selectedKbDetail = ref(null); // 当前选中的知识库详情
    const selectedChatKbIds = ref([]);
    const chatMode = ref('normal');
    const messages = ref([]);
    const userInput = ref('');
    const isStreaming = ref(false);
    const streamingContent = ref('');
    const showCreateKbDialog = ref(false);
    const newKbForm = ref({
      name: '',
      description: '',
    });
    const messagesContainer = ref(null);
    
    // 主题管理
    const isDarkTheme = ref(true);
    
    // 移动端菜单管理
    const isMobileMenuOpen = ref(false);

    // ==================== API 基础 URL ====================
    const API_BASE = '';

    // ==================== 工具函数 ====================
    const formatDate = (dateString) => {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    };

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getStatusType = (status) => {
      const types = {
        pending: 'info',
        processing: 'warning',
        completed: 'success',
        failed: 'danger',
      };
      return types[status] || 'info';
    };

    const getStatusText = (status) => {
      const texts = {
        pending: '待处理',
        processing: '处理中',
        completed: '已完成',
        failed: '失败',
      };
      return texts[status] || status;
    };

    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
      });
    };

    // ==================== Markdown 渲染 ====================
    const renderMarkdown = (text) => {
      if (!text) return '';
      // 使用 marked.js 渲染 Markdown
      if (typeof marked === 'undefined') {
        console.warn('marked library not loaded, returning plain text');
        return text;
      }
      
      try {
        // 配置 marked 选项
        marked.setOptions({
          breaks: true,        // 支持 GFM 换行
          gfm: true,          // GitHub Flavored Markdown
          headerIds: false,   // 不为标题添加 ID（避免冲突）
          mangle: false,      // 不转义 HTML 实体
          smartLists: true,   // 智能列表
          smartypants: false, // 不使用智能标点（避免中文问题）
          pedantic: false,    // 不严格遵循 Markdown 规范
        });
        
        return marked.parse(text);
      } catch (error) {
        console.error('Markdown 渲染失败:', error);
        return text; // 渲染失败时返回原文本
      }
    };

    // ==================== 主题管理 ====================
    const toggleTheme = () => {
      isDarkTheme.value = !isDarkTheme.value;
      if (isDarkTheme.value) {
        document.documentElement.removeAttribute('data-theme');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
      }
      localStorage.setItem('theme', isDarkTheme.value ? 'dark' : 'light');
    };
    
    // 移动端菜单控制
    const toggleMobileMenu = () => {
      isMobileMenuOpen.value = !isMobileMenuOpen.value;
    };
    
    const closeMobileMenu = () => {
      isMobileMenuOpen.value = false;
    };
    
    // 监听视图切换时关闭移动端菜单
    const switchView = (view) => {
      currentView.value = view;
      if (window.innerWidth <= 767) {
        closeMobileMenu();
      }
    };

    const initTheme = () => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'light') {
        isDarkTheme.value = false;
        document.documentElement.setAttribute('data-theme', 'light');
      }
    };

    // ==================== 知识库详情 ====================
    const openKbDetail = (kbId) => {
      const kb = knowledgeBases.value.find(k => k.id === kbId);
      if (kb) {
        selectedKbDetail.value = kb;
        currentView.value = 'kb-detail';
        selectedKbId.value = kbId;
        loadDocuments();
      }
    };

    // ==================== API 调用 ====================
    const apiRequest = async (url, options = {}) => {
      const defaultOptions = {
        headers: {
          'Content-Type': 'application/json',
        },
      };

      if (options.body && !(options.body instanceof FormData)) {
        options.body = JSON.stringify(options.body);
      }

      const response = await fetch(`${API_BASE}${url}`, {
        ...defaultOptions,
        ...options,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(error.detail || '请求失败');
      }

      return response;
    };

    // ==================== 知识库管理 ====================
    const loadKnowledgeBases = async () => {
      try {
        const response = await apiRequest('/api/kb');
        const data = await response.json();
        knowledgeBases.value = data.items || [];
      } catch (error) {
        ElementPlus.ElMessage.error(`加载知识库失败：${error.message}`);
      }
    };

    const createKb = async () => {
      if (!newKbForm.value.name.trim()) {
        ElementPlus.ElMessage.warning('请输入知识库名称');
        return;
      }

      try {
        await apiRequest('/api/kb', {
          method: 'POST',
          body: newKbForm.value,
        });

        ElementPlus.ElMessage.success('知识库创建成功');
        showCreateKbDialog.value = false;
        newKbForm.value = { name: '', description: '' };
        await loadKnowledgeBases();
      } catch (error) {
        ElementPlus.ElMessage.error(`创建知识库失败：${error.message}`);
      }
    };

    const deleteKb = async (kbId) => {
      try {
        await ElementPlus.ElMessageBox.confirm('确定要删除此知识库吗？此操作不可恢复。', '确认删除', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        });

        await apiRequest(`/api/kb/${kbId}`, {
          method: 'DELETE',
        });

        ElementPlus.ElMessage.success('知识库删除成功');
        await loadKnowledgeBases();

        if (selectedKbId.value === kbId) {
          selectedKbId.value = null;
          documents.value = [];
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElementPlus.ElMessage.error(`删除知识库失败：${error.message}`);
        }
      }
    };

    const selectKbForDoc = (kbId) => {
      selectedKbId.value = kbId;
      currentView.value = 'document';
      loadDocuments();
    };

    // ==================== 文档管理 ====================
    const loadDocuments = async () => {
      if (!selectedKbId.value) return;

      try {
        const response = await apiRequest(`/api/kb/${selectedKbId.value}/documents`);
        const data = await response.json();
        documents.value = data.items || [];
      } catch (error) {
        ElementPlus.ElMessage.error(`加载文档失败：${error.message}`);
      }
    };

    const handleUploadSuccess = (response, file) => {
      ElementPlus.ElMessage.success('文档上传成功，正在处理...');
      // 3 秒后刷新文档列表
      setTimeout(() => {
        loadDocuments();
      }, 3000);
    };

    const handleUploadError = (error) => {
      ElementPlus.ElMessage.error(`上传失败：${error.message}`);
    };

    const deleteDocument = async (docId) => {
      try {
        await ElementPlus.ElMessageBox.confirm('确定要删除此文档吗？', '确认删除', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        });

        await apiRequest(`/api/kb/documents/${docId}`, {
          method: 'DELETE',
        });

        ElementPlus.ElMessage.success('文档删除成功');
        await loadDocuments();
      } catch (error) {
        if (error !== 'cancel') {
          ElementPlus.ElMessage.error(`删除文档失败：${error.message}`);
        }
      }
    };

    // ==================== 问答对话 ====================
    const sendMessage = async () => {
      const question = userInput.value.trim();
      if (!question || isStreaming.value) return;

      // 添加用户消息
      messages.value.push({
        role: 'user',
        content: question,
      });

      userInput.value = '';
      isStreaming.value = true;
      streamingContent.value = '';
      scrollToBottom();

      try {
        if (chatMode.value === 'normal') {
          await sendNormalChat(question);
        } else {
          await sendRagChat(question);
        }
      } catch (error) {
        ElementPlus.ElMessage.error(`问答失败：${error.message}`);
        messages.value.push({
          role: 'assistant',
          content: `抱歉，出现错误：${error.message}`,
        });
      } finally {
        isStreaming.value = false;
        streamingContent.value = '';
        scrollToBottom();
      }
    };

    const sendNormalChat = async (question) => {
      const response = await apiRequest('/api/chat', {
        method: 'POST',
        body: {
          question,
          stream: true,
        },
      });

      await handleStreamResponse(response);
    };

    const sendRagChat = async (question) => {
      if (selectedChatKbIds.value.length === 0) {
        ElementPlus.ElMessage.warning('请选择至少一个知识库');
        isStreaming.value = false;
        return;
      }

      const response = await apiRequest('/api/chat/rag', {
        method: 'POST',
        body: {
          question,
          kb_ids: selectedChatKbIds.value,
          top_k: 3,
          stream: true,
        },
      });

      await handleStreamResponse(response);
    };

    const handleStreamResponse = async (response) => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        streamingContent.value += chunk;
        scrollToBottom();
      }

      // 将流式内容添加到消息列表
      messages.value.push({
        role: 'assistant',
        content: streamingContent.value,
      });
    };

    // ==================== 生命周期 ====================
    onMounted(() => {
      // 验证 marked.js 是否加载
      if (typeof marked === 'undefined') {
        console.error('marked.js 未加载，Markdown 渲染将不可用');
      } else {
        console.log('marked.js 加载成功');
      }
      initTheme();
      loadKnowledgeBases();
    });

    // ==================== 返回 ====================
    return {
      currentView,
      knowledgeBases,
      documents,
      selectedKbId,
      selectedKbDetail,
      selectedChatKbIds,
      chatMode,
      messages,
      userInput,
      isStreaming,
      streamingContent,
      showCreateKbDialog,
      newKbForm,
      messagesContainer,
      isDarkTheme,
      isMobileMenuOpen,
      formatDate,
      formatFileSize,
      getStatusType,
      getStatusText,
      renderMarkdown,
      loadKnowledgeBases,
      createKb,
      deleteKb,
      selectKbForDoc,
      openKbDetail,
      loadDocuments,
      handleUploadSuccess,
      handleUploadError,
      deleteDocument,
      sendMessage,
      toggleTheme,
      toggleMobileMenu,
      closeMobileMenu,
      switchView,
    };
  },
});

// 注册所有图标
Object.keys(icons).forEach((key) => {
  app.component(key, icons[key]);
});

// 使用 Element Plus
app.use(ElementPlus);

// 挂载应用
app.mount('#app');
