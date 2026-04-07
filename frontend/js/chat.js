/**
 * Chat controller
 * Handles message rendering, streaming updates, and conversation management
 */

class ChatController {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.sseClient = new SSEClient(baseUrl);
        this.currentSessionId = null;
        this.isStreaming = false;
        this.pendingFiles = [];
        this.messages = [];
        this.conversations = this.loadConversations();
        this.currentConversationId = null;

        // DOM elements
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageInput = document.getElementById('messageInput');
        this.btnSend = document.getElementById('btnSend');
        this.welcomeMessage = document.getElementById('welcomeMessage');
        this.conversationList = document.getElementById('conversationList');

        // Initialize conversation list
        this.renderConversationList();
    }

    /**
     * Load conversations from localStorage
     */
    loadConversations() {
        const saved = localStorage.getItem('easy-agent-conversations');
        return saved ? JSON.parse(saved) : [];
    }

    /**
     * Save conversations to localStorage
     */
    saveConversations() {
        localStorage.setItem('easy-agent-conversations', JSON.stringify(this.conversations));
    }

    /**
     * Save messages to localStorage
     */
    saveMessages() {
        if (!this.currentConversationId) return;
        const key = `easy-agent-conv-${this.currentConversationId}`;
        localStorage.setItem(key, JSON.stringify(this.messages));
    }

    /**
     * Add or update conversation
     */
    saveConversation(title, preview) {
        const id = this.currentConversationId || Date.now().toString();
        const existing = this.conversations.find(c => c.id === id);
        
        if (existing) {
            existing.title = title || existing.title;
            existing.preview = preview;
            existing.updatedAt = Date.now();
        } else {
            this.conversations.unshift({
                id: id,
                title: title || '新对话',
                preview: preview,
                createdAt: Date.now(),
                updatedAt: Date.now()
            });
            this.currentConversationId = id;
        }
        
        // 限制最多50条对话
        while (this.conversations.length > 50) {
            const oldest = this.conversations.pop();
            localStorage.removeItem(`easy-agent-conv-${oldest.id}`);
        }
        
        this.saveConversations();
        this.renderConversationList();
        return id;
    }

    /**
     * Render conversation list in sidebar
     */
    renderConversationList() {
        if (!this.conversationList) return;
        
        this.conversationList.innerHTML = '';
        
        this.conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'conversation-item' + (conv.id === this.currentConversationId ? ' active' : '');
            item.innerHTML = `
                <div class="conversation-title">${this.escapeHtml(conv.title)}</div>
                <div class="conversation-preview">${this.escapeHtml(conv.preview || '')}</div>
                <button class="conversation-delete" onclick="event.stopPropagation();" title="删除对话">×</button>
            `;
            item.addEventListener('click', () => this.loadConversation(conv.id));
            const deleteBtn = item.querySelector('.conversation-delete');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteConversation(conv.id);
            });
            this.conversationList.appendChild(item);
        });
    }

    /**
     * Load a conversation
     */
    loadConversation(id) {
        const conv = this.conversations.find(c => c.id === id);
        if (!conv) return;
        
        this.currentConversationId = id;
        this.currentSessionId = null;
        
        const key = `easy-agent-conv-${id}`;
        const savedMessages = localStorage.getItem(key);
        
        if (savedMessages) {
            this.messages = JSON.parse(savedMessages);
            this.messagesContainer.innerHTML = '';
            if (this.welcomeMessage) {
                this.welcomeMessage.style.display = 'none';
            }
            
            for (const msg of this.messages) {
                if (msg.role === 'user') {
                    this.addUserMessage(msg.content, []);
                } else if (msg.role === 'assistant') {
                    const assistantDiv = this.addAssistantMessagePlaceholder();
                    if (msg.thinking) {
                        const thinkingBlock = this.createThinkingBlock(assistantDiv);
                        const contentEl = thinkingBlock.querySelector('.thinking-content');
                        try {
                            contentEl.innerHTML = DOMPurify.sanitize(marked.parse(msg.thinking));
                        } catch(e) {
                            contentEl.textContent = msg.thinking;
                        }
                    }
                    if (msg.content) {
                        const textBlock = this.createTextBlock(assistantDiv);
                        try {
                            textBlock.innerHTML = DOMPurify.sanitize(marked.parse(msg.content));
                        } catch(e) {
                            textBlock.textContent = msg.content;
                        }
                    }
                    this.finalizeMessage(assistantDiv);
                }
            }
        }
        
        this.renderConversationList();
    }

    /**
     * Delete a conversation
     */
    deleteConversation(id) {
        this.conversations = this.conversations.filter(c => c.id !== id);
        localStorage.removeItem(`easy-agent-conv-${id}`);
        this.saveConversations();
        this.renderConversationList();
        
        if (this.currentConversationId === id) {
            this.clearChat();
        }
    }

    /**
     * Parse command from message (e.g., /web_search query)
     */
    parseCommand(message) {
        const cmdMatch = message.match(/^\/(\w+)(?:\s+(.*))?$/);
        if (cmdMatch) {
            return {
                isCommand: true,
                command: cmdMatch[1],
                args: cmdMatch[2] || ''
            };
        }
        return { isCommand: false };
    }

    /**
     * Execute a skill command directly
     */
    async executeSkillCommand(command, args) {
        // Find skill by command name
        const skillName = command;
        
        // Create a direct skill execution message
        const skillMsg = this.addAssistantMessagePlaceholder();
        const toolBlock = this.createToolBlock(skillMsg, skillName);
        this.updateToolStatus(toolBlock, 'running', { name: skillName });
        
        try {
            // Call skill execution API
            const response = await fetch(`${this.baseUrl}/api/skills/${skillName}/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: args })
            });
            
            if (!response.ok) {
                throw new Error(`Skill ${skillName} not found or failed`);
            }
            
            const result = await response.json();
            this.updateToolResult(toolBlock, result);
            
            // Add text response if any
            if (result.output || result.result) {
                const textBlock = this.createTextBlock(skillMsg);
                this.updateTextBlock(textBlock, result.output || result.result);
            }
            
            this.finalizeMessage(skillMsg);
            
            // Save conversation
            this.saveConversation(`/${skillName} ${args.substring(0, 20)}`, result.output?.substring(0, 50) || 'Skill executed');
            
        } catch (error) {
            this.updateToolStatus(toolBlock, 'error', { name: skillName });
            this.addErrorToMessage(skillMsg, error.message);
        }
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message && this.pendingFiles.length === 0) return;
        if (this.isStreaming) return;

        // Check for command
        const cmd = this.parseCommand(message);
        if (cmd.isCommand) {
            this.messageInput.value = '';
            await this.executeSkillCommand(cmd.command, cmd.args);
            return;
        }

        // Hide welcome message
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }

        // Add user message to UI
        this.addUserMessage(message, this.pendingFiles);

        // Save user message to messages array
        this.messages.push({
            role: 'user',
            content: message,
            files: this.pendingFiles.map(f => ({ type: f.type, name: f.name })),
            timestamp: new Date().toISOString()
        });

        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';

        // Create assistant message placeholder
        const assistantMsg = this.addAssistantMessagePlaceholder();

        // Build request
        const deepResearch = document.getElementById('deepResearchToggle').checked;
        const files = this.pendingFiles.map(f => ({
            type: f.type,
            base64: f.base64,
            mime_type: f.mime_type || f.mimeType
        }));

        const request = {
            session_id: this.currentSessionId,
            message: message,
            files: files,
            deep_research: deepResearch,
            persona: (typeof getPersona === 'function') ? getPersona() || null : null
        };

        // Clear pending files
        this.pendingFiles = [];
        this.updateFilePreview();

        // Start streaming
        this.isStreaming = true;
        this.btnSend.disabled = true;

        let thinkingBlock = null;
        let textBlock = null;
        let toolBlock = null;

        try {
            await this.sseClient.connect('/api/chat/stream', request, {
                thinking: (data) => {
                    if (!thinkingBlock) {
                        thinkingBlock = this.createThinkingBlock(assistantMsg);
                    }
                    this.updateThinkingBlock(thinkingBlock, data.thinking || data.content || data.text);
                },
                text: (data) => {
                    if (!textBlock) {
                        textBlock = this.createTextBlock(assistantMsg);
                    }
                    this.updateTextBlock(textBlock, data.text || data.content);
                },
                tool_use: (data) => {
                    if (!toolBlock) {
                        toolBlock = this.createToolBlock(assistantMsg, data.name);
                    }
                    this.updateToolStatus(toolBlock, 'running', data);
                },
                tool_result: (data) => {
                    if (toolBlock) {
                        this.updateToolResult(toolBlock, data);
                    }
                },
                done: (data) => {
                    this.currentSessionId = data.session_id;
                    this.isStreaming = false;
                    this.btnSend.disabled = false;
                    this.finalizeMessage(assistantMsg);
                    
                    // Save assistant message
                    const assistantContent = {
                        role: 'assistant',
                        content: textBlock ? textBlock._accumulatedText || '' : '',
                        thinking: thinkingBlock ? thinkingBlock.querySelector('.thinking-content')._accumulatedText || '' : '',
                        timestamp: new Date().toISOString()
                    };
                    this.messages.push(assistantContent);
                    this.saveMessages();
                    
                    // Save conversation with first message as title
                    const title = message.substring(0, 30) + (message.length > 30 ? '...' : '');
                    const preview = assistantMsg.textContent?.substring(0, 50) + '...' || '';
                    this.saveConversation(title, preview);
                },
                error: (data) => {
                    console.error('Stream error:', data);
                    this.addErrorToMessage(assistantMsg, data.error);
                    this.isStreaming = false;
                    this.btnSend.disabled = false;
                }
            });
        } catch (error) {
            console.error('Connection failed:', error);
            this.addErrorToMessage(assistantMsg, error.message);
            this.isStreaming = false;
            this.btnSend.disabled = false;
        }
    }

    /**
     * Add user message to UI
     */
    addUserMessage(message, files = []) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user';

        let content = '';
        if (message) {
            content += `<p>${this.escapeHtml(message)}</p>`;
        }

        // Add file previews
        for (const file of files) {
            if (file.type === 'image') {
                content += `
                    <div class="message-image">
                        <img src="data:${file.mime_type};base64,${file.base64}" alt="Uploaded image">
                    </div>
                `;
            } else if (file.type === 'video') {
                content += `
                    <div class="message-video">
                        <video controls>
                            <source src="data:${file.mime_type};base64,${file.base64}">
                        </video>
                    </div>
                `;
            }
        }

        msgDiv.innerHTML = `
            <div class="message-content">${content}</div>
            <div class="message-meta">${new Date().toLocaleTimeString()}</div>
        `;

        this.messagesContainer.appendChild(msgDiv);
        this.scrollToBottom();
    }

    /**
     * Add assistant message placeholder
     */
    addAssistantMessagePlaceholder() {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant';
        msgDiv.innerHTML = `
            <div class="message-content"></div>
            <div class="message-meta">${new Date().toLocaleTimeString()}</div>
        `;
        this.messagesContainer.appendChild(msgDiv);
        this.scrollToBottom();
        return msgDiv;
    }

    /**
     * Create thinking block
     */
    createThinkingBlock(parentMsg) {
        const content = parentMsg.querySelector('.message-content');
        const block = document.createElement('div');
        block.className = 'thinking-block';
        block.innerHTML = `
            <div class="thinking-header">
                <span>💭</span>
                <span>深度思考中...</span>
            </div>
            <div class="thinking-content"></div>
        `;
        content.appendChild(block);
        return block;
    }

    /**
     * Update thinking block content
     */
    updateThinkingBlock(block, content) {
        const contentEl = block.querySelector('.thinking-content');
        if (!contentEl._accumulatedText) {
            contentEl._accumulatedText = '';
        }
        contentEl._accumulatedText += content;
        try {
            const html = marked.parse(contentEl._accumulatedText);
            contentEl.innerHTML = DOMPurify.sanitize(html);
        } catch (e) {
            contentEl.textContent = contentEl._accumulatedText;
        }
        this.scrollToBottom();
    }

    /**
     * Create text block
     */
    createTextBlock(parentMsg) {
        const content = parentMsg.querySelector('.message-content');
        const block = document.createElement('div');
        block.className = 'text-block';
        content.appendChild(block);
        return block;
    }

    /**
     * Update text block content (streaming)
     */
    updateTextBlock(block, text) {
        if (!block._accumulatedText) {
            block._accumulatedText = '';
        }
        block._accumulatedText += text;
        try {
            const html = marked.parse(block._accumulatedText);
            // 在末尾添加光标元素
            block.innerHTML = DOMPurify.sanitize(html) + '<span class="typing-cursor-inline">▋</span>';
        } catch (e) {
            block.textContent = block._accumulatedText;
        }
        this.scrollToBottom();
    }

    /**
     * Create tool use block
     */
    createToolBlock(parentMsg, toolName) {
        const content = parentMsg.querySelector('.message-content');
        const block = document.createElement('div');
        block.className = 'tool-block';
        block.innerHTML = `
            <div class="tool-header">
                <span class="tool-spinner"></span>
                <span class="tool-name">${toolName}</span>
                <span class="tool-status">运行中...</span>
            </div>
            <div class="tool-result"></div>
        `;
        content.appendChild(block);
        return block;
    }

    /**
     * Update tool status
     */
    updateToolStatus(block, status, data) {
        const statusEl = block.querySelector('.tool-status');
        statusEl.textContent = status === 'running' ? '运行中...' : status;
    }

    /**
     * Update tool result
     */
    updateToolResult(block, data) {
        const resultEl = block.querySelector('.tool-result');
        const statusEl = block.querySelector('.tool-status');
        const spinnerEl = block.querySelector('.tool-spinner');

        statusEl.textContent = '完成';
        if (spinnerEl) {
            spinnerEl.style.display = 'none';
        }

        // Handle different result types
        if (data.output && Array.isArray(data.output)) {
            for (const item of data.output) {
                if (item.type === 'image' && item.source) {
                    if (item.source.url) {
                        resultEl.innerHTML += `<img src="${item.source.url}" alt="Tool result image">`;
                    } else if (item.source.base64) {
                        resultEl.innerHTML += `
                            <img src="data:${item.source.media_type};base64,${item.source.base64}" alt="Tool result image">
                        `;
                    }
                }
            }
        }
    }

    /**
     * Finalize message (remove typing cursor)
     */
    finalizeMessage(msgDiv) {
        // 移除所有打字光标
        const cursors = msgDiv.querySelectorAll('.typing-cursor-inline');
        cursors.forEach(c => c.remove());
        // 移除旧的 typing-cursor class（兼容）
        const textBlock = msgDiv.querySelector('.text-block');
        if (textBlock) {
            textBlock.classList.remove('typing-cursor');
        }
    }

    /**
     * Add error to message
     */
    addErrorToMessage(msgDiv, error) {
        const content = msgDiv.querySelector('.message-content');
        content.innerHTML += `<p style="color: var(--error); margin-top: 8px;">错误: ${this.escapeHtml(error)}</p>`;
    }

    /**
     * Scroll to bottom
     */
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Add pending file
     */
    addPendingFile(fileInfo) {
        this.pendingFiles.push(fileInfo);
        this.updateFilePreview();
    }

    /**
     * Remove pending file
     */
    removePendingFile(index) {
        this.pendingFiles.splice(index, 1);
        this.updateFilePreview();
    }

    /**
     * Update file preview
     */
    updateFilePreview() {
        // This will be implemented in app.js
        if (window.onFilePreviewUpdate) {
            window.onFilePreviewUpdate(this.pendingFiles);
        }
    }

    /**
     * Clear chat
     */
    clearChat() {
        this.messagesContainer.innerHTML = '';
        this.currentSessionId = null;
        this.currentConversationId = null;
        this.pendingFiles = [];
        this.messages = [];

        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'block';
        }
        
        this.renderConversationList();
    }

    /**
     * Abort current stream
     */
    abortStream() {
        this.sseClient.abort();
        this.isStreaming = false;
        this.btnSend.disabled = false;
    }
}

// Make it globally available
window.ChatController = ChatController;