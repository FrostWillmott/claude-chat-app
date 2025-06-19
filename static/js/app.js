class ChatApp {
    constructor() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatForm = document.getElementById('chatForm');
        this.searchToggle = document.getElementById('searchToggle');
        this.searchQuery = document.getElementById('searchQuery');
        this.searchInputGroup = document.getElementById('searchInputGroup');
        this.fileInput = document.getElementById('fileInput');
        this.thinkingModeSelect = document.getElementById('thinkingMode');

        this.searchEnabled = false;
        this.uploadedFiles = [];

        this.init();
    }

    init() {
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.messageInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.messageInput.addEventListener('input', () => this.autoResize());

        // Configure marked for markdown rendering
        marked.setOptions({
            breaks: true,
            gfm: true
        });

        // Load existing conversation
        this.loadConversation();
    }

    handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    async handleSubmit(e) {
        e.preventDefault();

        const message = this.messageInput.value.trim();
        if (!message || this.sendBtn.disabled) return;

        // Add user message to UI
        this.addMessage('user', message);
        this.messageInput.value = '';
        this.autoResize();

        // Show loading state
        this.setLoading(true);

        try {
            const requestData = {
                message,
                use_search: this.searchEnabled,
                search_query: this.searchEnabled ? this.searchQuery.value.trim() || message : '',
                thinking_mode: this.thinkingModeSelect ? this.thinkingModeSelect.value : 'normal'
            };

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to send message');
            }

            const data = await response.json();
            this.addMessage('assistant', data.response, data.search_results);

            // Clear search query after use
            if (this.searchEnabled) {
                this.searchQuery.value = '';
            }

        } catch (error) {
            this.showError(error.message);
        } finally {
            this.setLoading(false);
        }
    }

    addMessage(role, content, searchResults = null) {
        // Remove empty state if it exists
        const emptyState = this.messagesContainer.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Render markdown for assistant messages
        if (role === 'assistant') {
            contentDiv.innerHTML = marked.parse(content);
        } else {
            contentDiv.textContent = content;
        }

        messageDiv.appendChild(contentDiv);

        // Add search results if available
        if (searchResults && searchResults.length > 0) {
            const searchDiv = document.createElement('div');
            searchDiv.className = 'search-results';
            searchDiv.innerHTML = `
                <h4>🔍 Search Results Used:</h4>
                ${searchResults.map(result => `
                    <div class="search-result">
                        <a href="${result.url}" target="_blank">${result.title}</a>
                        <div style="color: #64748b; font-size: 12px;">${result.snippet}</div>
                    </div>
                `).join('')}
            `;
            messageDiv.appendChild(searchDiv);
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        messageDiv.appendChild(timeDiv);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    setLoading(loading) {
        this.sendBtn.disabled = loading;

        if (loading) {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant loading';
            loadingDiv.innerHTML = `
                <div>
                    Claude is thinking
                    <span class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </span>
                </div>
            `;
            loadingDiv.id = 'loading-message';
            this.messagesContainer.appendChild(loadingDiv);
            this.sendBtn.textContent = 'Sending...';
        } else {
            const loadingMessage = document.getElementById('loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }
            this.sendBtn.textContent = 'Send';
        }

        this.scrollToBottom();
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = `Error: ${message}`;
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();

        // Remove error after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }

    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        this.messagesContainer.appendChild(successDiv);
        this.scrollToBottom();

        // Remove success message after 3 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 3000);
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async loadConversation() {
        try {
            const response = await fetch('/api/conversation');
            const data = await response.json();

            if (data.messages && data.messages.length > 0) {
                // Remove empty state
                const emptyState = this.messagesContainer.querySelector('.empty-state');
                if (emptyState) {
                    emptyState.remove();
                }

                // Add messages
                data.messages.forEach(msg => {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        this.addMessageFromHistory(msg.role, msg.content, msg.timestamp, msg.metadata);
                    } else if (msg.type === 'file') {
                        this.addFileMessageFromHistory(msg.content, msg.timestamp, msg.metadata);
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }

    addMessageFromHistory(role, content, timestamp, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Render markdown for assistant messages
        if (role === 'assistant') {
            contentDiv.innerHTML = marked.parse(content);
        } else {
            contentDiv.textContent = content;
        }

        messageDiv.appendChild(contentDiv);

        // Add search results if available
        if (metadata.search_results && metadata.search_results.length > 0) {
            const searchDiv = document.createElement('div');
            searchDiv.className = 'search-results';
            searchDiv.innerHTML = `
                <h4>🔍 Search Results Used:</h4>
                ${metadata.search_results.map(result => `
                    <div class="search-result">
                        <a href="${result.url}" target="_blank">${result.title}</a>
                        <div style="color: #64748b; font-size: 12px;">${result.snippet}</div>
                    </div>
                `).join('')}
            `;
            messageDiv.appendChild(searchDiv);
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date(timestamp).toLocaleTimeString();
        messageDiv.appendChild(timeDiv);

        this.messagesContainer.appendChild(messageDiv);
    }

    addFileMessageFromHistory(content, timestamp, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message file';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        if (metadata.filename && metadata.file_content) {
            const previewDiv = document.createElement('div');
            previewDiv.className = 'file-preview';
            previewDiv.innerHTML = `
                <div class="filename">${metadata.filename}</div>
                <div class="content">${metadata.file_content.substring(0, 200)}${metadata.file_content.length > 200 ? '...' : ''}</div>
            `;
            contentDiv.appendChild(previewDiv);
        }

        messageDiv.appendChild(contentDiv);

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date(timestamp).toLocaleTimeString();
        messageDiv.appendChild(timeDiv);

        this.messagesContainer.appendChild(messageDiv);
    }
}

// Initialize chat app
let chatApp;

document.addEventListener('DOMContentLoaded', () => {
    chatApp = new ChatApp();
});

// Toggle search functionality
function toggleSearch() {
    chatApp.searchEnabled = !chatApp.searchEnabled;
    chatApp.searchToggle.classList.toggle('active', chatApp.searchEnabled);
    chatApp.searchInputGroup.style.display = chatApp.searchEnabled ? 'flex' : 'none';
}

// Handle file upload
async function handleFileUpload(input) {
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
        chatApp.setLoading(true);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to upload file');
        }

        const data = await response.json();

        // Add file message to UI
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message file';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = `Uploaded file: ${data.filename}`;

        const previewDiv = document.createElement('div');
        previewDiv.className = 'file-preview';
        previewDiv.innerHTML = `
            <div class="filename">${data.filename}</div>
            <div class="content">${data.content_preview}</div>
        `;
        contentDiv.appendChild(previewDiv);

        messageDiv.appendChild(contentDiv);

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        messageDiv.appendChild(timeDiv);

        // Remove empty state if it exists
        const emptyState = chatApp.messagesContainer.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        chatApp.messagesContainer.appendChild(messageDiv);
        chatApp.scrollToBottom();

        chatApp.showSuccess(`File "${data.filename}" uploaded successfully!`);

    } catch (error) {
        chatApp.showError(error.message);
    } finally {
        chatApp.setLoading(false);
        input.value = ''; // Reset file input
    }
}

// Export conversation
async function exportConversation() {
    try {
        const response = await fetch('/api/conversation/export');
        const data = await response.json();

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `claude-conversation-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);

        chatApp.showSuccess('Conversation exported successfully!');
    } catch (error) {
        chatApp.showError('Failed to export conversation');
    }
}

// Clear conversation function
async function clearConversation() {
    if (!confirm('Are you sure you want to clear the conversation?')) {
        return;
    }

    try {
        const response = await fetch('/api/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            // Clear UI
            chatApp.messagesContainer.innerHTML = `
                <div class="empty-state">
                    <h3>👋 Hello!</h3>
                    <p>Start a conversation with Claude by typing a message below. You can also upload files and enable web search.</p>
                </div>
            `;
            chatApp.showSuccess('Conversation cleared successfully!');
        }
    } catch (error) {
        chatApp.showError('Failed to clear conversation');
    }
}