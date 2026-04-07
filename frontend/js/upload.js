/**
 * File upload handler
 */

class UploadHandler {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.uploadEndpoint = `${baseUrl}/api/upload`;
        this.onFilesSelected = null;
        this.onUploadComplete = null;
        this.onUploadError = null;
    }

    /**
     * Handle file selection
     * @param {FileList} files - Selected files
     * @returns {Promise<Array>} - Array of file info objects
     */
    async handleFiles(files) {
        const results = [];

        for (const file of files) {
            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch(this.uploadEndpoint, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Upload failed');
                }

                const data = await response.json();
                results.push(data);

                if (this.onUploadComplete) {
                    this.onUploadComplete(data);
                }
            } catch (error) {
                console.error('Upload failed:', error);
                if (this.onUploadError) {
                    this.onUploadError(error, file);
                }
            }
        }

        if (this.onFilesSelected && results.length > 0) {
            this.onFilesSelected(results);
        }

        return results;
    }

    /**
     * Convert file to base64 (for direct sending without server upload)
     * @param {File} file - File to convert
     * @returns {Promise<{base64: string, mimeType: string}>}
     */
    static fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(',')[1];
                resolve({
                    base64: base64,
                    mimeType: file.type
                });
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    /**
     * Create preview URL for file
     * @param {File} file - File to preview
     * @returns {string} - Object URL
     */
    static createPreviewUrl(file) {
        return URL.createObjectURL(file);
    }

    /**
     * Revoke preview URL
     * @param {string} url - URL to revoke
     */
    static revokePreviewUrl(url) {
        if (url) {
            URL.revokeObjectURL(url);
        }
    }
}

// Make it globally available
window.UploadHandler = UploadHandler;
