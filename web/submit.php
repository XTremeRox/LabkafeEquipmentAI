<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Submit Quotation - AI Quotation</title>
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
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 40px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        
        .review-section {
            margin-bottom: 30px;
        }
        
        .review-item {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        
        .review-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .item-description {
            font-weight: 600;
            color: #333;
        }
        
        .selected-sku {
            color: #667eea;
            font-weight: 600;
        }
        
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 30px;
            justify-content: flex-end;
        }
        
        .btn {
            padding: 12px 24px;
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
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
        }
        
        .success-message.show {
            display: block;
        }
        
        .error-message {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
        }
        
        .error-message.show {
            display: block;
        }
        
        .todo-note {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 20px;
            border-radius: 5px;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Submit Quotation</h1>
        <p class="subtitle">Review your final selections before submitting</p>
        
        <div id="reviewContainer">
            <!-- Review items will be populated by JavaScript -->
        </div>
        
        <div class="actions">
            <button class="btn btn-secondary" onclick="window.location.href='suggestions.php'">← Back to Suggestions</button>
            <button class="btn btn-primary" id="submitBtn" onclick="submitQuotation()">Submit Quotation</button>
        </div>
        
        <div class="success-message" id="successMessage">
            <strong>Success!</strong> Quotation submitted successfully.
        </div>
        
        <div class="error-message" id="errorMessage">
            <strong>Error!</strong> <span id="errorText"></span>
        </div>
        
        <div class="todo-note">
            <strong>Note:</strong> The learning mechanism to update sku_mapping_history is pending implementation. 
            This will be added to increment frequencies for matched items and improve future suggestions.
        </div>
    </div>
    
    <script>
        const API_BASE_URL = 'http://localhost:8000/api';
        let lineItems = [];
        let selectedMappings = {};
        let skuNames = {};
        
        function loadReviewData() {
            // Load line items
            const storedItems = sessionStorage.getItem('lineItems');
            if (!storedItems) {
                window.location.href = 'upload.php';
                return;
            }
            lineItems = JSON.parse(storedItems);
            
            // Load selected mappings
            const storedMappings = sessionStorage.getItem('selectedMappings');
            if (!storedMappings) {
                window.location.href = 'suggestions.php';
                return;
            }
            selectedMappings = JSON.parse(storedMappings);
            
            // Load SKU names from suggestions
            const storedSuggestions = sessionStorage.getItem('suggestionsData');
            if (storedSuggestions) {
                const suggestions = JSON.parse(storedSuggestions);
                Object.values(suggestions).forEach(suggList => {
                    suggList.forEach(sugg => {
                        skuNames[sugg.sku_id] = sugg.item_name;
                    });
                });
            }
            
            renderReview();
        }
        
        function renderReview() {
            const container = document.getElementById('reviewContainer');
            
            container.innerHTML = lineItems.map((item, idx) => {
                const itemId = item.id || idx;
                const skuId = selectedMappings[itemId];
                const skuName = skuNames[skuId] || `SKU #${skuId}`;
                
                return `
                    <div class="review-item">
                        <div class="review-item-header">
                            <div class="item-description">${escapeHtml(item.description || item.text)}</div>
                            <div class="selected-sku">→ ${escapeHtml(skuName)}</div>
                        </div>
                        ${item.quantity ? `<div style="color: #666; font-size: 14px;">Quantity: ${item.quantity} ${item.unit || ''}</div>` : ''}
                    </div>
                `;
            }).join('');
        }
        
        async function submitQuotation() {
            const submitBtn = document.getElementById('submitBtn');
            const successMessage = document.getElementById('successMessage');
            const errorMessage = document.getElementById('errorMessage');
            
            submitBtn.disabled = true;
            successMessage.classList.remove('show');
            errorMessage.classList.remove('show');
            
            try {
                const response = await fetch(`${API_BASE_URL}/submit`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        line_items: lineItems,
                        selected_mappings: selectedMappings
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Submission failed');
                }
                
                const data = await response.json();
                
                successMessage.classList.add('show');
                submitBtn.style.display = 'none';
                
                // Clear session storage after successful submission
                setTimeout(() => {
                    sessionStorage.clear();
                }, 3000);
                
            } catch (error) {
                document.getElementById('errorText').textContent = error.message;
                errorMessage.classList.add('show');
                submitBtn.disabled = false;
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load on page load
        loadReviewData();
    </script>
</body>
</html>
