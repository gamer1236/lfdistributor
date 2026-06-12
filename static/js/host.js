document.addEventListener('DOMContentLoaded', () => {
    // State management
    let allFiles = [];
    let currentPickerPath = "";
    let selectedPickerFolder = "";

    // DOM Elements - Settings & Layout
    const sharedFolderText = document.getElementById('shared-folder-text');
    const btnBrowseFolder = document.getElementById('btn-browse-folder');
    const passwordEnableCheck = document.getElementById('password-enable-check');
    const passwordSettingFields = document.getElementById('password-setting-fields');
    const hostPwdInput = document.getElementById('host-pwd-input');
    const btnSaveConfig = document.getElementById('btn-save-config');
    const displayServerUrl = document.getElementById('display-server-url');
    const btnCopyUrl = document.getElementById('btn-copy-url');
    const copyToast = document.getElementById('copy-toast');
    const toastMessage = document.getElementById('toast-message');

    // DOM Elements - Files Stats and Controls
    const filesTableBody = document.getElementById('files-table-body');
    const filesEmptyState = document.getElementById('files-empty-state');
    const searchBar = document.getElementById('search-bar');
    const sortSelect = document.getElementById('sort-select');
    const btnRefreshFiles = document.getElementById('btn-refresh-files');
    const statFilesCount = document.getElementById('stat-files-count');
    const statFilesSize = document.getElementById('stat-files-size');
    const statDownloads = document.getElementById('stat-downloads');

    // DOM Elements - Folder Picker Modal
    const folderPickerModal = document.getElementById('folder-picker-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnCancelPicker = document.getElementById('btn-cancel-picker');
    const btnConfirmPicker = document.getElementById('btn-confirm-picker');
    const btnPickerUp = document.getElementById('btn-picker-up');
    const pickerPathInput = document.getElementById('picker-path-input');
    const pickerDirList = document.getElementById('picker-dir-list');

    // DOM Elements - File Upload Elements
    const uploadDropzone = document.getElementById('upload-dropzone');
    const uploadFileInput = document.getElementById('upload-file-input');
    const uploadProgressContainer = document.getElementById('upload-progress-container');
    const uploadFilenameDisplay = document.getElementById('upload-filename-display');
    const uploadPercentDisplay = document.getElementById('upload-percent-display');
    const uploadProgressFill = document.getElementById('upload-progress-fill');
    const uploadSpeedDisplay = document.getElementById('upload-speed-display');

    // --- HELPERS ---

    function showToast(message) {
        if (!copyToast) return;
        toastMessage.textContent = message;
        copyToast.classList.add('show');
        setTimeout(() => {
            copyToast.classList.remove('show');
        }, 3000);
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

    // --- HOST CONFIGURATIONS ---
    async function loadHostConfig() {
        try {
            const response = await fetch('/api/host/config');
            if (response.ok) {
                const config = await response.json();
                
                sharedFolderText.textContent = config.shared_folder;
                displayServerUrl.textContent = config.server_url;
                
                passwordEnableCheck.checked = config.password_enabled;
                if (config.password_enabled) {
                    passwordSettingFields.style.display = 'block';
                    hostPwdInput.value = config.password;
                } else {
                    passwordSettingFields.style.display = 'none';
                    hostPwdInput.value = '';
                }
            }
        } catch (err) {
            console.error("Error loading configuration settings:", err);
        }
    }

    if (passwordEnableCheck) {
        passwordEnableCheck.addEventListener('change', (e) => {
            if (e.target.checked) {
                passwordSettingFields.style.display = 'block';
            } else {
                passwordSettingFields.style.display = 'none';
            }
        });
    }

    const hostConfigForm = document.getElementById('host-config-form');
    if (hostConfigForm) {
        hostConfigForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const sharedFolder = sharedFolderText.textContent;
            const passwordEnabled = passwordEnableCheck.checked;
            const password = hostPwdInput.value.trim();
            
            if (passwordEnabled && !password) {
                alert("Password cannot be empty when password protection is enabled.");
                return;
            }
            
            try {
                const response = await fetch('/api/host/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        shared_folder: sharedFolder,
                        password_enabled: passwordEnabled,
                        password: password
                    })
                });
                
                const result = await response.json();
                if (response.ok && result.success) {
                    showToast("Configuration saved successfully!");
                    loadHostConfig();
                    fetchSharedFiles();
                } else {
                    alert(result.message || "Failed to update configuration.");
                }
            } catch (err) {
                alert("Error updating configuration.");
            }
        });
    }

    // --- HOST FOLDER PICKER MODAL ---

    function toggleModal(show) {
        if (show) {
            folderPickerModal.classList.add('active');
        } else {
            folderPickerModal.classList.remove('active');
        }
    }

    if (btnBrowseFolder) {
        btnBrowseFolder.addEventListener('click', () => {
            const currentPath = sharedFolderText.textContent;
            fetchDirectoryList(currentPath.includes("Loading") ? "" : currentPath);
            toggleModal(true);
        });
    }

    if (btnCloseModal) btnCloseModal.addEventListener('click', () => toggleModal(false));
    if (btnCancelPicker) btnCancelPicker.addEventListener('click', () => toggleModal(false));

    async function fetchDirectoryList(path) {
        try {
            const url = `/api/host/browse?path=${encodeURIComponent(path)}`;
            const response = await fetch(url);
            
            if (response.ok) {
                const data = await response.json();
                currentPickerPath = data.current_path;
                selectedPickerFolder = data.current_path;
                
                pickerPathInput.value = data.current_path || "System Root (Logical Drives)";
                
                if (data.parent_path !== null && data.current_path !== "") {
                    btnPickerUp.disabled = false;
                    btnPickerUp.style.opacity = 1;
                    btnPickerUp.dataset.parent = data.parent_path;
                } else {
                    btnPickerUp.disabled = true;
                    btnPickerUp.style.opacity = 0.4;
                }
                
                renderPickerDirectories(data.items);
            }
        } catch (err) {
            console.error("Error loading directory picker list:", err);
        }
    }

    btnPickerUp.addEventListener('click', () => {
        const parentPath = btnPickerUp.dataset.parent;
        fetchDirectoryList(parentPath || "");
    });

    function renderPickerDirectories(folders) {
        pickerDirList.innerHTML = '';
        
        if (folders.length === 0) {
            pickerDirList.innerHTML = `<div class="picker-item text-muted" style="cursor: default; justify-content: center;">No subdirectories found.</div>`;
            return;
        }
        
        folders.forEach(dir => {
            const item = document.createElement('div');
            item.className = 'picker-item';
            item.dataset.path = dir.path;
            
            item.innerHTML = `
                <span class="picker-item-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/>
                    </svg>
                </span>
                <span>${dir.name}</span>
            `;
            
            item.addEventListener('click', () => {
                document.querySelectorAll('.picker-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                selectedPickerFolder = dir.path;
            });
            
            item.addEventListener('dblclick', () => {
                fetchDirectoryList(dir.path);
            });
            
            pickerDirList.appendChild(item);
        });
    }

    if (btnConfirmPicker) {
        btnConfirmPicker.addEventListener('click', () => {
            if (selectedPickerFolder) {
                sharedFolderText.textContent = selectedPickerFolder;
                toggleModal(false);
                showToast("Folder selected! Click Save to confirm directory change.");
            }
        });
    }

    // --- HOST DRAG AND DROP FILE UPLOADER ---

    if (uploadDropzone) {
        // Trigger file select dialog on click
        uploadDropzone.addEventListener('click', () => uploadFileInput.click());
        
        // Dragover triggers
        uploadDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadDropzone.classList.add('dragover');
        });
        
        // Dragleave triggers
        uploadDropzone.addEventListener('dragleave', () => {
            uploadDropzone.classList.remove('dragover');
        });
        
        // Drop file handling
        uploadDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadDropzone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadFiles(files);
            }
        });
    }

    if (uploadFileInput) {
        uploadFileInput.addEventListener('change', () => {
            const files = uploadFileInput.files;
            if (files.length > 0) {
                uploadFiles(files);
            }
        });
    }

    function uploadFiles(files) {
        const formData = new FormData();
        
        // Format filenames listing for progress block
        let names = [];
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
            names.push(files[i].name);
        }
        
        uploadFilenameDisplay.textContent = files.length === 1 ? names[0] : `${files.length} files selected`;
        uploadPercentDisplay.textContent = '0%';
        uploadProgressFill.style.width = '0%';
        uploadSpeedDisplay.textContent = 'Preparing upload...';
        uploadProgressContainer.style.display = 'block';
        
        // Ajax request setup to track upload progress dynamically
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/host/upload', true);
        
        const startTime = Date.now();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadPercentDisplay.textContent = `${percent}%`;
                uploadProgressFill.style.width = `${percent}%`;
                
                // Speed calculation
                const elapsedSeconds = (Date.now() - startTime) / 1000;
                if (elapsedSeconds > 0) {
                    const bytesPerSecond = e.loaded / elapsedSeconds;
                    let speedStr = "";
                    if (bytesPerSecond > 1024 * 1024) {
                        speedStr = `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`;
                    } else {
                        speedStr = `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
                    }
                    uploadSpeedDisplay.textContent = `Uploading at ${speedStr} (${formatBytes(e.loaded)} / ${formatBytes(e.total)})`;
                }
            }
        });
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                uploadPercentDisplay.textContent = '100%';
                uploadProgressFill.style.width = '100%';
                uploadSpeedDisplay.textContent = 'Upload completed!';
                showToast(response.message || "Upload successful!");
                
                // Refresh listings
                setTimeout(() => {
                    uploadProgressContainer.style.display = 'none';
                    fetchSharedFiles();
                }, 1500);
            } else {
                let errorMsg = "Upload failed.";
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMsg = response.message || errorMsg;
                } catch(e) {}
                alert(`Error: ${errorMsg}`);
                uploadProgressContainer.style.display = 'none';
            }
            uploadFileInput.value = ""; // Reset
        };
        
        xhr.onerror = function() {
            alert("Connection error during upload.");
            uploadProgressContainer.style.display = 'none';
            uploadFileInput.value = "";
        };
        
        xhr.send(formData);
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // --- SHARE FILES LIST & DELETIONS ---

    async function fetchSharedFiles() {
        try {
            const response = await fetch('/api/files');
            if (response.ok) {
                const data = await response.json();
                allFiles = data.files;
                
                statFilesCount.textContent = data.count;
                statFilesSize.textContent = data.total_size_str;
                
                const totalDownloads = allFiles.reduce((acc, curr) => acc + (curr.download_count || 0), 0);
                statDownloads.textContent = totalDownloads;
                
                filterAndRenderFiles();
            }
        } catch (err) {
            console.error("Error loading shared files lists:", err);
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
                <td>
                    <div class="file-downloads-cell">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" x2="12" y1="15" y2="3"/>
                        </svg>
                        <span>${file.download_count || 0}</span>
                    </div>
                </td>
                <td style="text-align: center;">
                    <div style="display: inline-flex; gap: 0.5rem; justify-content: center; align-items: center; width: 100%;">
                        <!-- Host can also download to test -->
                        <a href="/download/${file.rel_path.split('/').map(encodeURIComponent).join('/')}" class="btn-download" title="Download File">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" x2="12" y1="15" y2="3"/>
                            </svg>
                        </a>
                        
                        <!-- Deletion action -->
                        <button class="btn-delete" data-path="${file.rel_path}" title="Delete File">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>
                            </svg>
                        </button>
                    </div>
                </td>
            `;
            
            // Delete action click hook
            const deleteBtn = tr.querySelector('.btn-delete');
            deleteBtn.addEventListener('click', () => {
                const relPath = deleteBtn.dataset.path;
                const filename = relPath.split('/').pop();
                if (confirm(`Are you sure you want to permanently delete "${filename}"?`)) {
                    deleteFile(relPath);
                }
            });
            
            filesTableBody.appendChild(tr);
        });
    }

    async function deleteFile(relPath) {
        try {
            const response = await fetch('/api/host/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rel_path: relPath })
            });
            
            const result = await response.json();
            if (response.ok && result.success) {
                showToast("File deleted successfully!");
                fetchSharedFiles();
            } else {
                alert(result.error || "Failed to delete file.");
            }
        } catch (err) {
            alert("Error connecting to server for file deletion.");
        }
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
    loadHostConfig();
    fetchSharedFiles();
});
