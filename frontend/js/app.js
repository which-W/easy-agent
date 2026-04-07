/**
 * Application initialization
 * Sets up event listeners and initializes components
 */

// Configuration
const API_BASE_URL = '';

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

    // Update header label
    const label = document.getElementById('personaLabel');
    if (label) {
        label.textContent = currentPersona
            ? currentPersona.substring(0, 12) + (currentPersona.length > 12 ? '…' : '')
            : '默认助手';
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

/**
 * Initialize application
 */
function init() {
    // Configure marked.js
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

    // Setup event listeners
    setupEventListeners();

    // Auto-resize textarea
    setupTextareaAutoResize();

    console.log('Easy-Agent initialized');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Send message
    btnSend.addEventListener('click', () => chat.sendMessage());

    // Enter to send (Shift+Enter for newline)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chat.sendMessage();
        }
    });

    // Sidebar toggle
    if (btnMenu) {
        btnMenu.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    if (btnToggleSidebar) {
        btnToggleSidebar.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
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
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);