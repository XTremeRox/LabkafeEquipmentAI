<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Document - AI Quotation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            text-align: center;
        }
        
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 60px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #f8f9ff;
        }
        
        .upload-area:hover {
            border-color: #764ba2;
            background: #f0f2ff;
        }
        
        .upload-area.dragover {
            border-color: #764ba2;
            background: #e8ebff;
            transform: scale(1.02);
        }
        
        .upload-icon {
            font-size: 64px;
            color: #667eea;
            margin-bottom: 20px;
        }
        
        .upload-text {
            font-size: 18px;
            color: #333;
            margin-bottom: 10px;
        }
        
        .upload-hint {
            font-size: 14px;
            color: #999;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .file-info {
            margin-top: 20px;
            padding: 15px;
            background: #f0f2ff;
            border-radius: 10px;
            display: none;
        }
        
        .file-info.show {
            display: block;
        }
        
        .file-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .file-size {
            font-size: 14px;
            color: #666;
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s ease;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .progress {
            margin-top: 20px;
            display: none;
        }
        
        .progress.show {
            display: block;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .error {
            margin-top: 20px;
            padding: 15px;
            background: #fee;
            border-left: 4px solid #f44;
            border-radius: 5px;
            color: #c33;
            display: none;
        }
        
        .error.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Upload Document</h1>
        <p class="subtitle">Upload images, PDFs, Excel, or Word documents</p>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📎</div>
            <div class="upload-text">Drag & drop your file here</div>
            <div class="upload-hint">or click to browse</div>
            <input type="file" id="fileInput" accept=".jpg,.jpeg,.png,.pdf,.xlsx,.xls,.docx,.csv">
        </div>
        
        <div class="file-info" id="fileInfo">
            <div class="file-name" id="fileName"></div>
            <div class="file-size" id="fileSize"></div>
        </div>
        
        <div class="error" id="error"></div>
        
        <div class="progress" id="progress">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
        </div>
        
        <button class="btn" id="uploadBtn" disabled>Upload & Process</button>
    </div>
    
    <script>
        const API_BASE_URL = 'http://localhost:8000/api';
        
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const uploadBtn = document.getElementById('uploadBtn');
        const error = document.getElementById('error');
        const progress = document.getElementById('progress');
        const progressFill = document.getElementById('progressFill');
        
        let selectedFile = null;
        
        // Click to upload
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        function handleFileSelect(file) {
            selectedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.add('show');
            uploadBtn.disabled = false;
            error.classList.remove('show');
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            uploadBtn.disabled = true;
            progress.classList.add('show');
            error.classList.remove('show');
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            try {
                // Upload file
                progressFill.style.width = '30%';
                const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!uploadResponse.ok) {
                    throw new Error('Upload failed');
                }
                
                const uploadData = await uploadResponse.json();
                const fileId = uploadData.file_id;
                
                // Extract line items
                progressFill.style.width = '60%';
                const extractResponse = await fetch(`${API_BASE_URL}/extract`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ file_id: fileId })
                });
                
                if (!extractResponse.ok) {
                    throw new Error('Extraction failed');
                }
                
                const extractData = await extractResponse.json();
                
                progressFill.style.width = '100%';
                
                // Store data in sessionStorage and redirect
                sessionStorage.setItem('fileId', fileId);
                sessionStorage.setItem('lineItems', JSON.stringify(extractData.line_items));
                
                setTimeout(() => {
                    window.location.href = 'edit_items.php';
                }, 500);
                
            } catch (err) {
                error.textContent = 'Error: ' + err.message;
                error.classList.add('show');
                uploadBtn.disabled = false;
                progress.classList.remove('show');
            }
        });
    </script>
</body>
</html>
