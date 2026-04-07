/**
 * SSE Client for streaming responses
 * Uses fetch + ReadableStream since EventSource doesn't support POST
 */

class SSEClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.controller = null;
    }

    /**
     * Connect to SSE endpoint
     * @param {string} endpoint - API endpoint
     * @param {Object} body - Request body
     * @param {Object} handlers - Event handlers {thinking, text, tool_use, tool_result, done, error}
     */
    async connect(endpoint, body, handlers) {
        this.controller = new AbortController();

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body),
                signal: this.controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body
                .pipeThrough(new TextDecoderStream())
                .getReader();

            let buffer = '';
            let currentEvent = null;

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                buffer += value;
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line

                for (const line of lines) {
                    const trimmedLine = line.trim();

                    if (trimmedLine.startsWith('event: ')) {
                        currentEvent = trimmedLine.slice(7);
                    } else if (trimmedLine.startsWith('data: ') && currentEvent) {
                        try {
                            const data = JSON.parse(trimmedLine.slice(6));
                            if (handlers[currentEvent]) {
                                handlers[currentEvent](data);
                            }
                        } catch (e) {
                            console.error('Failed to parse SSE data:', e, trimmedLine);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('SSE connection aborted');
            } else if (handlers.error) {
                handlers.error({ error: error.message });
            }
        }
    }

    /**
     * Abort the current connection
     */
    abort() {
        if (this.controller) {
            this.controller.abort();
            this.controller = null;
        }
    }
}

// Make it globally available
window.SSEClient = SSEClient;
