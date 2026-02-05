<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Line Items - AI Quotation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        
        .actions {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-secondary {
            background: #e0e0e0;
            color: #333;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        input, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        textarea {
            resize: vertical;
            min-height: 60px;
        }
        
        .delete-btn {
            background: #f44;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .delete-btn:hover {
            background: #c33;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✏️ Edit Line Items</h1>
        <p style="color: #666; margin-bottom: 20px;">Review and edit the extracted line items before getting suggestions.</p>
        
        <div class="actions">
            <button class="btn btn-secondary" onclick="addNewItem()">+ Add Item</button>
            <button class="btn btn-primary" onclick="proceedToSuggestions()" style="margin-left: auto;">Get Suggestions →</button>
        </div>
        
        <table id="itemsTable">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Original Text</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Unit</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="itemsBody">
                <!-- Items will be populated by JavaScript -->
            </tbody>
        </table>
        
        <div class="empty-state" id="emptyState" style="display: none;">
            <p>No line items found. Please add items or go back to upload.</p>
        </div>
    </div>
    
    <script>
        let lineItems = [];
        let nextId = 1;
        
        // Load line items from sessionStorage
        function loadLineItems() {
            const stored = sessionStorage.getItem('lineItems');
            if (stored) {
                lineItems = JSON.parse(stored);
                // Assign IDs if missing
                lineItems.forEach((item, idx) => {
                    if (!item.id) {
                        item.id = idx + 1;
                    }
                });
                nextId = Math.max(...lineItems.map(i => i.id || 0)) + 1;
            }
            renderTable();
        }
        
        function renderTable() {
            const tbody = document.getElementById('itemsBody');
            const emptyState = document.getElementById('emptyState');
            
            if (lineItems.length === 0) {
                tbody.innerHTML = '';
                emptyState.style.display = 'block';
                return;
            }
            
            emptyState.style.display = 'none';
            tbody.innerHTML = lineItems.map((item, idx) => `
                <tr>
                    <td>${item.id || idx + 1}</td>
                    <td><textarea onchange="updateItem(${idx}, 'text', this.value)">${escapeHtml(item.text || '')}</textarea></td>
                    <td><textarea onchange="updateItem(${idx}, 'description', this.value)">${escapeHtml(item.description || '')}</textarea></td>
                    <td><input type="number" step="0.01" value="${item.quantity || ''}" onchange="updateItem(${idx}, 'quantity', parseFloat(this.value) || null)"></td>
                    <td><input type="text" value="${escapeHtml(item.unit || '')}" onchange="updateItem(${idx}, 'unit', this.value)"></td>
                    <td><button class="delete-btn" onclick="deleteItem(${idx})">Delete</button></td>
                </tr>
            `).join('');
        }
        
        function updateItem(index, field, value) {
            if (lineItems[index]) {
                lineItems[index][field] = value;
                saveLineItems();
            }
        }
        
        function deleteItem(index) {
            if (confirm('Are you sure you want to delete this item?')) {
                lineItems.splice(index, 1);
                saveLineItems();
                renderTable();
            }
        }
        
        function addNewItem() {
            lineItems.push({
                id: nextId++,
                text: '',
                description: '',
                quantity: null,
                unit: null
            });
            saveLineItems();
            renderTable();
        }
        
        function saveLineItems() {
            sessionStorage.setItem('lineItems', JSON.stringify(lineItems));
        }
        
        function proceedToSuggestions() {
            if (lineItems.length === 0) {
                alert('Please add at least one line item');
                return;
            }
            
            // Validate that all items have descriptions
            const invalidItems = lineItems.filter(item => !item.description || !item.description.trim());
            if (invalidItems.length > 0) {
                alert('Please ensure all items have a description');
                return;
            }
            
            window.location.href = 'suggestions.php';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load on page load
        loadLineItems();
    </script>
</body>
</html>
