/**
 * Gestionnaire d'upload amélioré avec drag & drop multiple
 */

class EnhancedUploader {
    constructor(containerId, projectId) {
        this.container = document.getElementById(containerId);
        this.projectId = projectId;
        this.uploadQueue = [];
        this.activeUploads = 0;
        this.maxConcurrentUploads = 3;
        
        this.init();
    }
    
    init() {
        this.createUploadInterface();
        this.setupEventListeners();
    }
    
    createUploadInterface() {
        this.container.innerHTML = `
            <div class="upload-zone" id="uploadZone">
                <div class="upload-icon">📁</div>
                <h3>Glissez vos fichiers ici</h3>
                <p>ou cliquez pour sélectionner</p>
                <p class="file-types">PDF, PNG, JPG, JPEG • Max 50MB par fichier</p>
                <input type="file" id="fileInput" multiple accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                <button class="btn upload-btn" onclick="document.getElementById('fileInput').click()">
                    📂 Choisir les fichiers
                </button>
            </div>
            
            <div class="upload-progress" id="uploadProgress" style="display: none;">
                <div class="progress-header">
                    <h4>Upload en cours...</h4>
                    <button class="btn-cancel" onclick="uploader.cancelAll()">Annuler tout</button>
                </div>
                <div class="progress-list" id="progressList"></div>
                <div class="overall-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="overallProgress"></div>
                    </div>
                    <span id="progressText">0%</span>
                </div>
            </div>
            
            <div class="upload-results" id="uploadResults">
                <h4>📋 Fichiers uploadés</h4>
                <div class="files-list" id="filesList"></div>
            </div>
        `;
    }
    
    setupEventListeners() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        
        // Drag & drop
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
        
        uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // File input
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }
    
    handleFiles(files) {
        const validFiles = Array.from(files).filter(file => this.validateFile(file));
        
        if (validFiles.length === 0) {
            this.showError('Aucun fichier valide sélectionné');
            return;
        }
        
        // Ajouter à la queue
        validFiles.forEach(file => {
            const uploadItem = {
                id: Date.now() + Math.random(),
                file: file,
                status: 'pending',
                progress: 0
            };
            this.uploadQueue.push(uploadItem);
        });
        
        this.startUploads();
    }
    
    validateFile(file) {
        // Vérifier le type
        const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
        if (!allowedTypes.includes(file.type)) {
            this.showError(`Type de fichier non supporté: ${file.name}`);
            return false;
        }
        
        // Vérifier la taille (50MB max)
        const maxSize = 50 * 1024 * 1024; // 50MB
        if (file.size > maxSize) {
            this.showError(`Fichier trop volumineux: ${file.name} (max 50MB)`);
            return false;
        }
        
        return true;
    }
    
    startUploads() {
        document.getElementById('uploadProgress').style.display = 'block';
        
        while (this.activeUploads < this.maxConcurrentUploads && this.uploadQueue.length > 0) {
            const uploadItem = this.uploadQueue.shift();
            this.uploadFile(uploadItem);
        }
    }
    
    async uploadFile(uploadItem) {
        this.activeUploads++;
        uploadItem.status = 'uploading';
        
        // Créer l'élément de progression
        this.createProgressItem(uploadItem);
        
        const formData = new FormData();
        formData.append('file', uploadItem.file);
        
        try {
            const response = await fetch(`/upload/${this.projectId}`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                uploadItem.status = 'completed';
                uploadItem.progress = 100;
                this.updateProgressItem(uploadItem);
                this.addToFilesList(uploadItem.file.name);
            } else {
                uploadItem.status = 'error';
                uploadItem.error = result.error;
                this.updateProgressItem(uploadItem);
            }
            
        } catch (error) {
            uploadItem.status = 'error';
            uploadItem.error = error.message;
            this.updateProgressItem(uploadItem);
        }
        
        this.activeUploads--;
        this.updateOverallProgress();
        
        // Continuer avec les uploads en attente
        if (this.uploadQueue.length > 0) {
            this.startUploads();
        } else if (this.activeUploads === 0) {
            // Tous les uploads terminés
            setTimeout(() => {
                document.getElementById('uploadProgress').style.display = 'none';
                this.loadExistingFiles();
            }, 2000);
        }
    }
    
    createProgressItem(uploadItem) {
        const progressList = document.getElementById('progressList');
        const item = document.createElement('div');
        item.className = 'progress-item';
        item.id = `progress-${uploadItem.id}`;
        
        item.innerHTML = `
            <div class="file-info">
                <span class="file-name">${uploadItem.file.name}</span>
                <span class="file-size">${this.formatFileSize(uploadItem.file.size)}</span>
            </div>
            <div class="progress-bar-small">
                <div class="progress-fill-small" style="width: 0%"></div>
            </div>
            <span class="status">En attente...</span>
        `;
        
        progressList.appendChild(item);
    }
    
    updateProgressItem(uploadItem) {
        const item = document.getElementById(`progress-${uploadItem.id}`);
        if (!item) return;
        
        const progressFill = item.querySelector('.progress-fill-small');
        const status = item.querySelector('.status');
        
        progressFill.style.width = `${uploadItem.progress}%`;
        
        switch (uploadItem.status) {
            case 'completed':
                status.textContent = '✅ Terminé';
                status.className = 'status success';
                progressFill.style.backgroundColor = '#28a745';
                break;
            case 'error':
                status.textContent = `❌ ${uploadItem.error}`;
                status.className = 'status error';
                progressFill.style.backgroundColor = '#dc3545';
                break;
            case 'uploading':
                status.textContent = '⏳ Upload...';
                status.className = 'status uploading';
                break;
        }
    }
    
    updateOverallProgress() {
        const total = this.uploadQueue.length + this.activeUploads + 
                     document.querySelectorAll('.progress-item').length;
        const completed = document.querySelectorAll('.status.success').length;
        const errors = document.querySelectorAll('.status.error').length;
        
        const percentage = total > 0 ? ((completed + errors) / total) * 100 : 0;
        
        document.getElementById('overallProgress').style.width = `${percentage}%`;
        document.getElementById('progressText').textContent = 
            `${completed}/${total} fichiers • ${Math.round(percentage)}%`;
    }
    
    addToFilesList(filename) {
        const filesList = document.getElementById('filesList');
        const item = document.createElement('div');
        item.className = 'file-item';
        
        item.innerHTML = `
            <div class="file-info">
                <span class="file-icon">${this.getFileIcon(filename)}</span>
                <span class="file-name">${filename}</span>
            </div>
            <div class="file-actions">
                <button class="btn-small btn-danger" onclick="uploader.deleteFile('${filename}')">
                    🗑️ Supprimer
                </button>
            </div>
        `;
        
        filesList.appendChild(item);
    }
    
    async loadExistingFiles() {
        try {
            const response = await fetch(`/api/project/${this.projectId}/files`);
            const files = await response.json();
            
            const filesList = document.getElementById('filesList');
            filesList.innerHTML = '';
            
            files.forEach(filename => {
                this.addToFilesList(filename);
            });
            
        } catch (error) {
            console.error('Erreur chargement fichiers:', error);
        }
    }
    
    async deleteFile(filename) {
        if (!confirm(`Supprimer le fichier ${filename} ?`)) return;
        
        try {
            const response = await fetch(`/delete/${this.projectId}/${filename}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.loadExistingFiles();
                this.showSuccess(`Fichier ${filename} supprimé`);
            } else {
                this.showError(result.error);
            }
            
        } catch (error) {
            this.showError('Erreur lors de la suppression');
        }
    }
    
    cancelAll() {
        this.uploadQueue = [];
        document.getElementById('uploadProgress').style.display = 'none';
        this.showWarning('Uploads annulés');
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        switch (ext) {
            case 'pdf': return '📄';
            case 'png': case 'jpg': case 'jpeg': return '🖼️';
            default: return '📁';
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showWarning(message) {
        this.showNotification(message, 'warning');
    }
    
    showNotification(message, type) {
        // Créer une notification toast
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// CSS pour l'uploader
const uploaderStyles = `
<style>
.upload-zone {
    border: 2px dashed #667eea;
    border-radius: 15px;
    padding: 3rem;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
    background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
}

.upload-zone:hover, .upload-zone.drag-over {
    border-color: #5a6fd8;
    background: linear-gradient(135deg, #e8ecff 0%, #d1d9ff 100%);
    transform: translateY(-2px);
}

.upload-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    opacity: 0.7;
}

.file-types {
    color: #666;
    font-size: 0.9rem;
    margin: 1rem 0;
}

.upload-btn {
    margin-top: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.upload-progress {
    background: white;
    border-radius: 10px;
    padding: 1.5rem;
    margin-top: 1rem;
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.btn-cancel {
    background: #dc3545;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
}

.progress-item {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    align-items: center;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    background: #f8f9fa;
    border-radius: 8px;
}

.file-info {
    display: flex;
    flex-direction: column;
}

.file-name {
    font-weight: bold;
    margin-bottom: 0.25rem;
}

.file-size {
    color: #666;
    font-size: 0.9rem;
}

.progress-bar-small {
    width: 150px;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill-small {
    height: 100%;
    background: #667eea;
    transition: width 0.3s ease;
}

.overall-progress {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #e0e0e0;
}

.progress-bar {
    flex: 1;
    height: 12px;
    background: #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.3s ease;
}

.upload-results {
    margin-top: 2rem;
}

.file-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    margin-bottom: 0.5rem;
    background: #f8f9fa;
    border-radius: 8px;
    border-left: 4px solid #28a745;
}

.file-item .file-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.file-icon {
    font-size: 1.5rem;
}

.status.success { color: #28a745; }
.status.error { color: #dc3545; }
.status.uploading { color: #ffc107; }

.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    color: white;
    font-weight: bold;
    z-index: 1000;
    animation: slideIn 0.3s ease;
}

.notification.success { background: #28a745; }
.notification.error { background: #dc3545; }
.notification.warning { background: #ffc107; color: #333; }

@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
</style>
`;

// Injecter les styles
document.head.insertAdjacentHTML('beforeend', uploaderStyles);
