<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Suggestions - AI Quotation</title>
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
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        
        .item-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 25px;
            margin-bottom: 25px;
        }
        
        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .item-description {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        
        .item-quantity {
            color: #666;
            font-size: 14px;
        }
        
        .suggestions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .suggestion-card {
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .suggestion-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        
        .suggestion-card.selected {
            border-color: #667eea;
            background: #f0f2ff;
        }
        
        .suggestion-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        
        .suggestion-name {
            font-weight: 600;
            color: #333;
            font-size: 16px;
            flex: 1;
        }
        
        .confidence-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .confidence-high {
            background: #4caf50;
            color: white;
        }
        
        .confidence-medium {
            background: #ff9800;
            color: white;
        }
        
        .confidence-low {
            background: #f44;
            color: white;
        }
        
        .suggestion-details {
            font-size: 14px;
            color: #666;
            margin-top: 10px;
        }
        
        .quote-history {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
        }
        
        .quote-history-title {
            font-size: 12px;
            font-weight: 600;
            color: #999;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .quote-item {
            font-size: 12px;
            color: #666;
            padding: 5px 0;
            display: flex;
            justify-content: space-between;
        }
        
        .quote-item:not(:last-child) {
            border-bottom: 1px solid #f0f0f0;
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
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .no-suggestions {
            text-align: center;
            padding: 40px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💡 Suggestions</h1>
        <p style="color: #666; margin-bottom: 30px;">Select the best match for each line item. Last 3 quoted values are shown for reference.</p>
        
        <div id="suggestionsContainer">
            <div class="loading">Loading suggestions...</div>
        </div>
        
        <div class="actions">
            <button class="btn btn-secondary" onclick="window.location.href='edit_items.php'">← Back to Edit</button>
            <button class="btn btn-primary" onclick="proceedToSubmit()">Submit Quotation →</button>
        </div>
    </div>
    
    <script>
        const API_BASE_URL = 'http://localhost:8000/api';
        let lineItems = [];
        let suggestionsData = {};
        let selectedMappings = {};
        
        async function loadSuggestions() {
            // Load line items from sessionStorage
            const stored = sessionStorage.getItem('lineItems');
            if (!stored) {
                window.location.href = 'upload.php';
                return;
            }
            
            lineItems = JSON.parse(stored);
            
            // Get suggestions from API
            try {
                const response = await fetch(`${API_BASE_URL}/suggest`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        line_items: lineItems
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to get suggestions');
                }
                
                const data = await response.json();
                suggestionsData = data.suggestions;
                
                // Store suggestions in sessionStorage for later use
                sessionStorage.setItem('suggestionsData', JSON.stringify(suggestionsData));
                
                // Initialize selected mappings with first suggestion
                Object.keys(suggestionsData).forEach(itemId => {
                    const suggs = suggestionsData[itemId];
                    if (suggs && suggs.length > 0) {
                        selectedMappings[itemId] = suggs[0].sku_id;
                    }
                });
                
                renderSuggestions();
                
            } catch (error) {
                document.getElementById('suggestionsContainer').innerHTML = 
                    `<div class="no-suggestions">Error loading suggestions: ${error.message}</div>`;
            }
        }
        
        function renderSuggestions() {
            const container = document.getElementById('suggestionsContainer');
            
            if (lineItems.length === 0) {
                container.innerHTML = '<div class="no-suggestions">No line items found</div>';
                return;
            }
            
            container.innerHTML = lineItems.map((item, idx) => {
                const itemId = item.id || idx;
                const suggestions = suggestionsData[itemId] || [];
                const selectedSku = selectedMappings[itemId];
                
                return `
                    <div class="item-card">
                        <div class="item-header">
                            <div>
                                <div class="item-description">${escapeHtml(item.description || item.text)}</div>
                                ${item.quantity ? `<div class="item-quantity">Quantity: ${item.quantity} ${item.unit || ''}</div>` : ''}
                            </div>
                        </div>
                        
                        ${suggestions.length > 0 ? `
                            <div class="suggestions-grid">
                                ${suggestions.map(sugg => {
                                    const isSelected = sugg.sku_id === selectedSku;
                                    const confidenceClass = 
                                        sugg.confidence_score >= 0.85 ? 'confidence-high' :
                                        sugg.confidence_score >= 0.60 ? 'confidence-medium' : 'confidence-low';
                                    
                                    return `
                                        <div class="suggestion-card ${isSelected ? 'selected' : ''}" 
                                             onclick="selectSuggestion(${itemId}, ${sugg.sku_id})">
                                            <div class="suggestion-header">
                                                <div class="suggestion-name">${escapeHtml(sugg.item_name)}</div>
                                                <span class="confidence-badge ${confidenceClass}">
                                                    ${Math.round(sugg.confidence_score * 100)}%
                                                </span>
                                            </div>
                                            
                                            <div class="suggestion-details">
                                                ${sugg.historical_frequency ? `Used ${sugg.historical_frequency} times before<br>` : ''}
                                                ${sugg.vector_similarity ? `Similarity: ${Math.round(sugg.vector_similarity * 100)}%` : ''}
                                            </div>
                                            
                                            ${sugg.last_3_quotes && sugg.last_3_quotes.length > 0 ? `
                                                <div class="quote-history">
                                                    <div class="quote-history-title">Last 3 Quotes</div>
                                                    ${sugg.last_3_quotes.map(quote => `
                                                        <div class="quote-item">
                                                            <span>${quote.date || 'N/A'}</span>
                                                            <span>${quote.price ? '₹' + quote.price : ''} ${quote.quantity ? 'x' + quote.quantity : ''}</span>
                                                        </div>
                                                    `).join('')}
                                                </div>
                                            ` : ''}
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        ` : `
                            <div class="no-suggestions">No suggestions available for this item</div>
                        `}
                    </div>
                `;
            }).join('');
        }
        
        function selectSuggestion(itemId, skuId) {
            selectedMappings[itemId] = skuId;
            renderSuggestions();
        }
        
        async function proceedToSubmit() {
            // Save selected mappings
            sessionStorage.setItem('selectedMappings', JSON.stringify(selectedMappings));
            window.location.href = 'submit.php';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load on page load
        loadSuggestions();
    </script>
</body>
</html>
