/**
 * Application initialization
 * Sets up event listeners and initializes components
 */

// Configuration
const API_BASE_URL = '';

// ── Persona preset mapping (short names for UI display) ──────────────────
const PERSONA_PRESET_NAMES = {
    '': '默认助手',
    '你是一位严谨的专业代码审查专家，精通多种编程语言。请用简洁精准的语言分析代码问题，指出潜在风险，并给出最佳实践建议。': '代码专家',
    '你是一位耐心温和的教学导师，善于用通俗易懂的语言解释复杂概念，多用类比和例子，引导学生主动思考而非直接给出答案。': '学习导师',
    '你是一位创意写作顾问，文笔优美，想象力丰富。协助用户构建故事情节、塑造人物、打磨文字，风格可根据需求调整。': '创意写作',
    '你是一位专业的商业分析师，擅长数据解读、市场分析和战略规划。回答时注重逻辑严密、数据支撑，并提供可执行的建议。': '商业分析',
    '你是一位幽默风趣的对话伙伴，语言轻松活泼，善用比喻和玩笑，但不失真诚。在轻松氛围中提供实质性帮助。': '轻松聊天',
    '你是一位专业的多语言翻译和语言学习助手，精通中、英、日、韩、法、德等多种语言，能提供准确翻译并解释语言差异。': '翻译助手',
    '你是一位知识渊博的历史与文化研究者，能深度解析历史事件、文化背景和社会现象，善于在历史与现实之间建立联系。': '历史文化'
};

/** Get display name from persona content */
function getPersonaDisplayName(personaContent) {
    if (!personaContent) return '默认助手';
    return PERSONA_PRESET_NAMES[personaContent] || '自定义人格';
}
// ──────────────────────────────────────────────────────────────────────────

// Initialize components
const chat = new ChatController(API_BASE_URL);
const uploadHandler = new UploadHandler(API_BASE_URL);

// ── Persona state ──────────────────────────────────────────────────────────
let currentPersona = localStorage.getItem('easy-agent-persona') || '';

/** Return the active persona string (empty = default) */
function getPersona() { return currentPersona; }

/** Persist and update UI label after applying a persona */
function applyPersona(text) {
    currentPersona = text ? text.trim() : '';
    localStorage.setItem('easy-agent-persona', currentPersona);

    // Update header label with short name
    const label = document.getElementById('personaLabel');
    if (label) {
        label.textContent = getPersonaDisplayName(currentPersona);
    }

    // Reset session so next message uses the new persona
    chat.currentSessionId = null;
}
// ──────────────────────────────────────────────────────────────────────────

// DOM elements
const sidebar = document.getElementById('sidebar');
const btnMenu = document.getElementById('btnMenu');
const btnToggleSidebar = document.getElementById('btnToggleSidebar');
const btnNewChat = document.getElementById('btnNewChat');
const btnSend = document.getElementById('btnSend');
const messageInput = document.getElementById('messageInput');
const btnAttach = document.getElementById('btnAttach');
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
const filePreviewList = document.getElementById('filePreviewList');

// Sidebar state
let sidebarHoverTimeout = null;

/**
 * Initialize application
 */
function init() {
    // Configure marked.js
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });
    }

    // Setup event listeners
    setupEventListeners();

    // Setup sidebar hover detection
    setupSidebarHover();

    // Auto-resize textarea
    setupTextareaAutoResize();

    console.log('Easy-Agent initialized');
}

/**
 * Setup sidebar hover detection
 */
function setupSidebarHover() {
    // 创建用于检测鼠标位置的透明区域
    const hoverZone = document.createElement('div');
    hoverZone.className = 'sidebar-hover-zone';
    document.body.appendChild(hoverZone);
    
    // 鼠标进入 hover 区域时打开侧边栏
    hoverZone.addEventListener('mouseenter', () => {
        if (sidebar && sidebar.classList.contains('collapsed')) {
            // 清除之前的定时器
            if (sidebarHoverTimeout) {
                clearTimeout(sidebarHoverTimeout);
            }
            sidebar.classList.remove('collapsed');
            // 设置定时器，5秒后如果鼠标不在侧边栏上则自动收起
            startAutoCollapseTimer();
        }
    });
    
    // 鼠标离开侧边栏时，延迟收起
    if (sidebar) {
        sidebar.addEventListener('mouseleave', () => {
            // 只有当侧边栏不是通过菜单按钮固定打开时才自动收起
            // 这里我们简化：离开后自动收起
            startAutoCollapseTimer();
        });
        
        // 鼠标进入侧边栏时，取消自动收起
        sidebar.addEventListener('mouseenter', () => {
            if (sidebarHoverTimeout) {
                clearTimeout(sidebarHoverTimeout);
                sidebarHoverTimeout = null;
            }
        });
    }
}

/**
 * 启动自动收起侧边栏的定时器
 */
function startAutoCollapseTimer() {
    if (sidebarHoverTimeout) {
        clearTimeout(sidebarHoverTimeout);
    }
    sidebarHoverTimeout = setTimeout(() => {
        if (sidebar && !sidebar.classList.contains('collapsed')) {
            // 检查鼠标是否在侧边栏或 hover 区域内
            const hoverZone = document.querySelector('.sidebar-hover-zone');
            const isHoveringSidebar = sidebar.matches(':hover');
            const isHoveringZone = hoverZone ? hoverZone.matches(':hover') : false;
            
            if (!isHoveringSidebar && !isHoveringZone) {
                sidebar.classList.add('collapsed');
            }
        }
        sidebarHoverTimeout = null;
    }, 3000); // 3秒后自动收起
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Send message
    if (btnSend) {
        btnSend.addEventListener('click', () => chat.sendMessage());
    }

    // Enter to send (Shift+Enter for newline)
    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chat.sendMessage();
            }
        });
    }

    // Sidebar toggle (汉堡菜单按钮 - 固定打开/关闭)
    if (btnMenu) {
        btnMenu.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            // 手动点击时取消自动收起定时器
            if (sidebarHoverTimeout) {
                clearTimeout(sidebarHoverTimeout);
                sidebarHoverTimeout = null;
            }
        });
    }

    // 底部关闭侧边栏按钮 - 切换而不是只关闭
    if (btnToggleSidebar) {
        btnToggleSidebar.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            // 更新按钮文字
            const isCollapsed = sidebar.classList.contains('collapsed');
            btnToggleSidebar.textContent = isCollapsed ? '关闭侧边栏' : '关闭侧边栏';
            // 手动点击时取消自动收起定时器
            if (sidebarHoverTimeout) {
                clearTimeout(sidebarHoverTimeout);
                sidebarHoverTimeout = null;
            }
        });
    }

    // New chat
    if (btnNewChat) {
        btnNewChat.addEventListener('click', () => {
            chat.clearChat();
            sidebar.classList.remove('open');
        });
    }

    // File attach
    if (btnAttach) {
        btnAttach.addEventListener('click', () => {
            fileInput.click();
        });
    }

    // File selection
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                await handleFileSelection(e.target.files);
                fileInput.value = ''; // Reset to allow selecting same file again
            }
        });
    }

    // File preview update handler
    window.onFilePreviewUpdate = updateFilePreview;

    // ── Persona modal ──────────────────────────────────────────────────────
    const personaModal   = document.getElementById('personaModal');
    const personaInput   = document.getElementById('personaInput');
    const personaCharCount = document.getElementById('personaCharCount');
    const btnPersona     = document.getElementById('btnPersona');
    const btnPersonaClose  = document.getElementById('btnPersonaClose');
    const btnPersonaCancel = document.getElementById('btnPersonaCancel');
    const btnPersonaApply  = document.getElementById('btnPersonaApply');

    function openPersonaModal() {
        personaInput.value = currentPersona;
        updateCharCount();
        highlightActivePreset();
        personaModal.style.display = 'flex';
        personaInput.focus();
    }

    function closePersonaModal() {
        personaModal.style.display = 'none';
    }

    function updateCharCount() {
        const len = personaInput.value.length;
        personaCharCount.textContent = `${len} / 500`;
    }

    function highlightActivePreset() {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.persona === currentPersona);
        });
    }

    if (btnPersona)       btnPersona.addEventListener('click', openPersonaModal);
    if (btnPersonaClose)  btnPersonaClose.addEventListener('click', closePersonaModal);
    if (btnPersonaCancel) btnPersonaCancel.addEventListener('click', closePersonaModal);

    // Click outside to close
    if (personaModal) {
        personaModal.addEventListener('click', (e) => {
            if (e.target === personaModal) closePersonaModal();
        });
    }

    // Char counter
    if (personaInput) {
        personaInput.addEventListener('input', () => {
            updateCharCount();
            // Clear preset highlight when user types custom text
            document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
        });
    }

    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            personaInput.value = btn.dataset.persona;
            updateCharCount();
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Apply button
    if (btnPersonaApply) {
        btnPersonaApply.addEventListener('click', () => {
            applyPersona(personaInput.value);
            closePersonaModal();
        });
    }

    // Restore persona label on page load
    applyPersona(currentPersona);
    // ──────────────────────────────────────────────────────────────────────
}

/**
 * Handle file selection
 */
async function handleFileSelection(files) {
    for (const file of files) {
        try {
            const { base64, mimeType } = await UploadHandler.fileToBase64(file);
            const fileInfo = {
                type: file.type.startsWith('image') ? 'image' : 'video',
                base64: base64,
                mime_type: mimeType,
                name: file.name,
                previewUrl: UploadHandler.createPreviewUrl(file)
            };

            chat.addPendingFile(fileInfo);
        } catch (error) {
            console.error('Failed to process file:', error);
            alert(`处理文件失败: ${error.message}`);
        }
    }
}

/**
 * Update file preview display
 */
function updateFilePreview(files) {
    if (!filePreview || !filePreviewList) return;

    if (files.length === 0) {
        filePreview.style.display = 'none';
        filePreviewList.innerHTML = '';
        return;
    }

    filePreview.style.display = 'block';
    filePreviewList.innerHTML = '';

    files.forEach((file, index) => {
        const previewItem = document.createElement('div');
        previewItem.className = 'file-preview-item';

        if (file.type === 'image') {
            previewItem.innerHTML = `
                <img src="${file.previewUrl}" alt="${file.name}">
                <button class="file-remove" onclick="removePendingFile(${index})">×</button>
            `;
        } else if (file.type === 'video') {
            previewItem.innerHTML = `
                <video src="${file.previewUrl}" muted></video>
                <button class="file-remove" onclick="removePendingFile(${index})">×</button>
            `;
        }

        filePreviewList.appendChild(previewItem);
    });
}

/**
 * Remove pending file (called from inline onclick)
 */
window.removePendingFile = function(index) {
    const files = chat.pendingFiles;
    if (files[index] && files[index].previewUrl) {
        UploadHandler.revokePreviewUrl(files[index].previewUrl);
    }
    chat.removePendingFile(index);
};

/**
 * Setup textarea auto-resize
 */
function setupTextareaAutoResize() {
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);