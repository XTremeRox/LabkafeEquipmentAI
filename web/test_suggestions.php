<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Suggestions - AI Quotation</title>
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
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        
        .input-section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            min-height: 150px;
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .hint {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
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
        
        .results-section {
            margin-top: 30px;
        }
        
        .item-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .item-description {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        
        .suggestions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .suggestion-card {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            transition: all 0.3s ease;
        }
        
        .suggestion-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        
        .suggestion-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        
        .suggestion-name {
            font-weight: 600;
            color: #333;
            font-size: 15px;
            flex: 1;
        }
        
        .confidence-badge {
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 11px;
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
            font-size: 13px;
            color: #666;
            margin-top: 8px;
        }
        
        .suggestion-price {
            font-weight: 600;
            color: #667eea;
            margin-top: 5px;
        }
        
        .quote-history {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
        }
        
        .quote-history-title {
            font-size: 11px;
            font-weight: 600;
            color: #999;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        
        .quote-item {
            font-size: 11px;
            color: #666;
            padding: 3px 0;
            display: flex;
            justify-content: space-between;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error {
            padding: 15px;
            background: #fee;
            border-left: 4px solid #f44;
            border-radius: 5px;
            color: #c33;
            margin-top: 20px;
        }
        
        .no-results {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        .timing-bar {
            margin-bottom: 20px;
            padding: 12px 16px;
            background: #f0f4ff;
            border-radius: 8px;
            font-size: 13px;
            color: #555;
        }
        .timing-bar strong { color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Test Suggestion Algorithm</h1>
        <p class="subtitle">Manually input items to test the hybrid matching algorithm</p>
        
        <div class="input-section">
            <div class="input-group">
                <label for="itemsInput">Enter Items (one per line)</label>
                <textarea id="itemsInput" placeholder="Test Tube 10ml - 50 pieces
Beaker 100ml
Pipette 5ml
..."></textarea>
                <div class="hint">Enter each item on a new line. You can include quantities and units.</div>
            </div>
            
            <button class="btn btn-primary" id="getSuggestionsBtn" onclick="getSuggestions()">Get Suggestions</button>
            <button class="btn btn-secondary" onclick="clearResults()" style="margin-left: 10px;">Clear</button>
        </div>
        
        <div class="error" id="errorMessage" style="display: none;"></div>
        
        <div class="results-section" id="resultsSection" style="display: none;">
            <div class="timing-bar" id="timingBar" style="display: none;"></div>
            <h2 style="margin-bottom: 20px;">Suggestions</h2>
            <div id="resultsContainer"></div>
        </div>
    </div>
    
    <script>
        const API_BASE_URL = 'http://localhost:8000/api';
        
        function parseItems(input) {
            const lines = input.split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0);
            
            return lines.map((line, idx) => ({
                id: idx + 1,
                text: line,
                description: line,
                quantity: null,
                unit: null
            }));
        }
        
        async function getSuggestions() {
            const input = document.getElementById('itemsInput').value.trim();
            const btn = document.getElementById('getSuggestionsBtn');
            const errorDiv = document.getElementById('errorMessage');
            const resultsSection = document.getElementById('resultsSection');
            const resultsContainer = document.getElementById('resultsContainer');
            
            if (!input) {
                errorDiv.textContent = 'Please enter at least one item';
                errorDiv.style.display = 'block';
                return;
            }
            
            errorDiv.style.display = 'none';
            btn.disabled = true;
            btn.textContent = 'Loading...';
            resultsSection.style.display = 'block';
            resultsContainer.innerHTML = '<div class="loading">Getting suggestions...</div>';
            
            try {
                const lineItems = parseItems(input);
                
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
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to get suggestions');
                }
                
                const timingHeader = response.headers.get('X-Suggest-Timing');
                const data = await response.json();
                renderResults(lineItems, data.suggestions, timingHeader ? JSON.parse(timingHeader) : null);
                
            } catch (error) {
                errorDiv.textContent = 'Error: ' + error.message;
                errorDiv.style.display = 'block';
                resultsContainer.innerHTML = '';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Get Suggestions';
            }
        }
        
        function renderResults(lineItems, suggestionsData, timing) {
            const container = document.getElementById('resultsContainer');
            const timingBar = document.getElementById('timingBar');
            
            if (timing) {
                const s = timing.steps || {};
                let detail = '';
                if (s._matching_detail) {
                    const d = s._matching_detail;
                    const v = (d.vector_search_batch != null ? d.vector_search_batch : d.vector_search) || 0;
                    detail = ' <span style="color:#888">(history:' + (d.historical_mappings||0) + 'ms, vector:' + v + 'ms)</span>';
                }
                timingBar.innerHTML = '<strong>⏱ Timing:</strong> Total ' + timing.total_ms + 'ms' +
                    (s.embeddings_api ? ' | Embeddings: ' + s.embeddings_api + 'ms' : '') +
                    (s.matching ? ' | Matching: ' + s.matching + 'ms' + detail : '') +
                    (s.batch_db != null ? ' | Batch DB: ' + s.batch_db + 'ms' : (s.quote_history ? ' | Quote history: ' + s.quote_history + 'ms' : '')) +
                    ' (' + (timing.items_count || 0) + ' items)';
                timingBar.style.display = 'block';
            } else {
                timingBar.style.display = 'none';
            }
            
            if (Object.keys(suggestionsData).length === 0) {
                container.innerHTML = '<div class="no-results">No suggestions found</div>';
                return;
            }
            
            container.innerHTML = lineItems.map((item, idx) => {
                const itemId = item.id || idx;
                const suggestions = suggestionsData[itemId] || [];
                
                return `
                    <div class="item-card">
                        <div class="item-header">
                            <div class="item-description">${escapeHtml(item.description || item.text)}</div>
                        </div>
                        
                        ${suggestions.length > 0 ? `
                            <div class="suggestions-grid">
                                ${suggestions.map(sugg => {
                                    const confidenceClass = 
                                        sugg.confidence_score >= 0.85 ? 'confidence-high' :
                                        sugg.confidence_score >= 0.60 ? 'confidence-medium' : 'confidence-low';
                                    
                                    return `
                                        <div class="suggestion-card">
                                            <div class="suggestion-header">
                                                <div class="suggestion-name">${escapeHtml(sugg.item_name)}</div>
                                                <span class="confidence-badge ${confidenceClass}">
                                                    ${Math.round(sugg.confidence_score * 100)}%
                                                </span>
                                            </div>
                                            
                                            <div class="suggestion-details">
                                                <div><strong>SKU:</strong> ${escapeHtml(sugg.sku)}</div>
                                                ${sugg.historical_frequency ? `<div>Used ${sugg.historical_frequency} times before</div>` : ''}
                                                ${sugg.vector_similarity ? `<div>Similarity: ${Math.round(sugg.vector_similarity * 100)}%</div>` : ''}
                                                ${sugg.price ? `<div class="suggestion-price">Price: ₹${sugg.price}</div>` : ''}
                                            </div>
                                            
                                            ${sugg.image ? `
                                                <div style="margin-top: 10px;">
                                                    <img src="${escapeHtml(sugg.image)}" alt="${escapeHtml(sugg.item_name)}" 
                                                         style="max-width: 100%; height: auto; border-radius: 5px;">
                                                </div>
                                            ` : ''}
                                            
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
                            <div class="no-results">No suggestions available for this item</div>
                        `}
                    </div>
                `;
            }).join('');
        }
        
        function clearResults() {
            document.getElementById('itemsInput').value = '';
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
