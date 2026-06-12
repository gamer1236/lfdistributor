document.addEventListener('DOMContentLoaded', () => {
    // State
    let allFiles = [];

    // DOM Elements
    const filesTableBody = document.getElementById('files-table-body');
    const filesEmptyState = document.getElementById('files-empty-state');
    const searchBar = document.getElementById('search-bar');
    const sortSelect = document.getElementById('sort-select');
    const btnRefreshFiles = document.getElementById('btn-refresh-files');
    const statFilesCount = document.getElementById('stat-files-count');
    const statFilesSize = document.getElementById('stat-files-size');
    const displayServerUrl = document.getElementById('display-server-url');
    const btnCopyUrl = document.getElementById('btn-copy-url');
    const copyToast = document.getElementById('copy-toast');
    const toastMessage = document.getElementById('toast-message');

    // Password Wall Elements
    const authForm = document.getElementById('auth-form');
    const authPassword = document.getElementById('auth-password');
    const authFeedback = document.getElementById('auth-feedback');

    // --- HELPERS ---

    function showToast(message) {
        if (!copyToast) return;
        toastMessage.textContent = message;
        copyToast.classList.add('show');
        setTimeout(() => {
            copyToast.classList.remove('show');
        }, 3000);
    }

    // --- CLIENT PASSWORD AUTHENTICATION ---
    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = authPassword.value;
            
            try {
                const response = await fetch('/api/auth', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password })
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    authFeedback.className = "auth-feedback success";
                    authFeedback.textContent = "Access granted! Redirecting...";
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    authFeedback.className = "auth-feedback error";
                    authFeedback.textContent = result.message || "Invalid password.";
                }
            } catch (err) {
                authFeedback.className = "auth-feedback error";
                authFeedback.textContent = "Error connecting to server.";
            }
        });
    }

    // --- COPY SERVER CONNECTION LINK ---
    if (btnCopyUrl) {
        btnCopyUrl.addEventListener('click', () => {
            const serverUrl = displayServerUrl.textContent;
            navigator.clipboard.writeText(serverUrl)
                .then(() => showToast("Copied server URL to clipboard!"))
                .catch(() => showToast("Failed to copy URL."));
        });
    }

    // --- FILE LIST & VIEW ENUMERATION ---
    async function fetchSharedFiles() {
        if (window.FLASK_CONFIG.authNeeded) return;
        
        try {
            const response = await fetch('/api/files');
            if (response.ok) {
                const data = await response.json();
                allFiles = data.files;
                
                // Update stats
                statFilesCount.textContent = data.count;
                statFilesSize.textContent = data.total_size_str;
                
                filterAndRenderFiles();
            } else if (response.status === 401) {
                window.location.reload();
            }
        } catch (err) {
            console.error("Error loading files lists:", err);
        }
    }

    function getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        
        const audio = ['mp3', 'wav', 'ogg', 'm4a', 'flac'];
        const video = ['mp4', 'mkv', 'avi', 'mov', 'webm'];
        const image = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp'];
        const doc = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'md'];
        const archive = ['zip', 'rar', 'tar', 'gz', '7z'];
        const code = ['html', 'css', 'js', 'py', 'java', 'cpp', 'c', 'json', 'sh', 'bat'];

        let iconSvg = '';
        
        if (audio.includes(ext)) {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`;
        } else if (video.includes(ext)) {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2" ry="2"/></svg>`;
        } else if (image.includes(ext)) {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>`;
        } else if (doc.includes(ext)) {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>`;
        } else if (archive.includes(ext)) {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M12 3v18"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>`;
        } else if (code.includes(ext)) {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>`;
        } else {
            iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>`;
        }
        return iconSvg;
    }

    function filterAndRenderFiles() {
        const query = searchBar.value.toLowerCase().trim();
        const sortType = sortSelect.value;
        
        let filtered = allFiles.filter(file => {
            return file.name.toLowerCase().includes(query) || file.rel_path.toLowerCase().includes(query);
        });
        
        filtered.sort((a, b) => {
            switch (sortType) {
                case 'name_asc':
                    return a.name.localeCompare(b.name);
                case 'name_desc':
                    return b.name.localeCompare(a.name);
                case 'size_desc':
                    return b.size_bytes - a.size_bytes;
                case 'size_asc':
                    return a.size_bytes - b.size_bytes;
                case 'date_desc':
                    return b.mtime - a.mtime;
                case 'date_asc':
                    return a.mtime - b.mtime;
                default:
                    return 0;
            }
        });
        
        renderFilesList(filtered);
    }

    function renderFilesList(files) {
        filesTableBody.innerHTML = '';
        
        if (files.length === 0) {
            document.getElementById('files-table').style.display = 'none';
            filesEmptyState.style.display = 'block';
            
            if (searchBar.value.trim()) {
                document.getElementById('empty-title-text').textContent = "No matching files";
                document.getElementById('empty-desc-text').textContent = "Try refining your search keyword.";
            } else {
                document.getElementById('empty-title-text').textContent = "No files found";
                document.getElementById('empty-desc-text').textContent = "The shared folder is currently empty.";
            }
            return;
        }
        
        document.getElementById('files-table').style.display = 'table';
        filesEmptyState.style.display = 'none';
        
        files.forEach(file => {
            const tr = document.createElement('tr');
            
            const hasSubfolder = file.rel_path.includes('/');
            const subfolderHtml = hasSubfolder 
                ? `<span class="file-relpath-text">${file.rel_path.substring(0, file.rel_path.lastIndexOf('/'))}/</span>` 
                : `<span class="file-relpath-text">/</span>`;
                
            tr.innerHTML = `
                <td>
                    <div class="file-info-cell">
                        <div class="file-icon">
                            ${getFileIcon(file.name)}
                        </div>
                        <div class="file-name-meta">
                            <span class="file-name-text" title="${file.name}">${file.name}</span>
                            ${subfolderHtml}
                        </div>
                    </div>
                </td>
                <td>
                    <span class="file-size-cell">${file.size_str}</span>
                </td>
                <td>
                    <span class="file-date-cell">${file.date_added}</span>
                </td>
                <td style="text-align: center;">
                    <a href="/download/${file.rel_path.split('/').map(encodeURIComponent).join('/')}" class="btn-download dl-trigger-link" title="Download File">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" x2="12" y1="15" y2="3"/>
                        </svg>
                    </a>
                </td>
            `;
            
            // Set up a listener on download link to automatically refresh counts in the UI after a delay
            const downloadBtn = tr.querySelector('.dl-trigger-link');
            downloadBtn.addEventListener('click', () => {
                setTimeout(() => {
                    fetchSharedFiles();
                }, 1000);
            });
            
            filesTableBody.appendChild(tr);
        });
    }

    if (searchBar) searchBar.addEventListener('input', filterAndRenderFiles);
    if (sortSelect) sortSelect.addEventListener('change', filterAndRenderFiles);
    if (btnRefreshFiles) {
        btnRefreshFiles.addEventListener('click', () => {
            fetchSharedFiles();
            showToast("Rescanned shared files!");
        });
    }

    // --- INITIALIZATION ---
    if (displayServerUrl && displayServerUrl.textContent.includes('Detecting')) {
        displayServerUrl.textContent = window.location.origin;
    }
    fetchSharedFiles();
});
