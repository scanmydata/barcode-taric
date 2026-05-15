#!/usr/bin/env python3
"""Web-based TARIC lookup interface (works without X11 display)."""

from flask import Flask, render_template_string, request, jsonify
from taric_lookup import resolve_item
import json
import sys

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TARIC Lookup - Ευρωπαϊκή Ταξινόμηση</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: system-ui, -apple-system, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            padding: 30px;
        }
        h1 { color: #333; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #666; font-size: 14px; margin-bottom: 25px; }
        
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input { 
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #667eea; }
        button { 
            padding: 12px 25px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.3s;
        }
        button:hover { background: #764ba2; }
        button:active { transform: scale(0.98); }
        
        textarea {
            width: 100%;
            height: 80px;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            margin: 10px 0;
        }
        
        .section { margin: 30px 0; }
        .section h2 { font-size: 16px; color: #333; margin-bottom: 15px; }
        
        .results { display: grid; gap: 15px; }
        .result {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background: #f9f9f9;
        }
        .result.success {
            border-left: 4px solid #28a745;
            background: #f0fff4;
        }
        .result.error {
            border-left: 4px solid #dc3545;
            background: #fff5f5;
        }
        
        .product-name { font-weight: bold; color: #333; margin-bottom: 10px; }
        .taric-code { font-size: 24px; font-weight: bold; color: #667eea; font-family: monospace; }
        .hs4 { color: #666; font-size: 12px; }
        .description { color: #555; font-size: 13px; margin-top: 8px; }
        .source { color: #999; font-size: 11px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; }
        
        .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
        .stat-box { 
            padding: 15px;
            background: #f0f0f0;
            border-radius: 5px;
            text-align: center;
        }
        .stat-number { font-size: 24px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #666; margin-top: 5px; }
        
        .loading { text-align: center; padding: 20px; }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .tab-buttons { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #ddd; }
        .tab-btn { 
            padding: 10px 20px;
            background: none;
            border: none;
            cursor: pointer;
            color: #666;
            font-weight: bold;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        .tab-btn.active { color: #667eea; border-bottom-color: #667eea; }
        .tab-btn:hover { color: #667eea; }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .export-btn {
            background: #28a745;
            margin-top: 20px;
        }
        .export-btn:hover { background: #218838; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 TARIC Lookup</h1>
        <p class="subtitle">Ευρωπαϊκή Ταξινόμηση - European Product Classification</p>
        
        <div style="margin: 15px 0; padding: 10px; background: #f0f0f0; border-radius: 5px; display: flex; gap: 10px; align-items: center;">
            <label style="font-weight: bold; color: #333;">🤖 AI Provider:</label>
            <select id="aiProvider" style="padding: 8px; border: 1px solid #ccc; border-radius: 3px; font-weight: bold;">
                <option value="openrouter" selected>⚡ OpenRouter (Fast)</option>
                <option value="pollinations">🌊 Pollinations (Free)</option>
                <option value="none">❌ No AI (Direct Match)</option>
            </select>
            <span id="aiStatus" style="font-size: 12px; color: #666; margin-left: 10px;">✅ Ready</span>
        </div>
        
        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('single')">📦 Single</button>
            <button class="tab-btn" onclick="switchTab('batch')">📊 Batch</button>
        </div>
        
        <div id="single" class="tab-content active">
            <div class="input-group">
                <input type="text" id="singleInput" placeholder="Barcode ή προϊόν (Enter barcode or product description)" onkeypress="if(event.key==='Enter') singleLookup()">
                <button onclick="singleLookup()">🔍 Αναζήτηση</button>
            </div>
        </div>
        
        <div id="batch" class="tab-content">
            <textarea id="batchInput" placeholder="Ένα ανά γραμμή (One per line)..."></textarea>
            <button onclick="batchLookup()" style="width: 100%;">📊 Αποστολή</button>
        </div>
        
        <div id="stats" class="stats" style="display: none;">
            <div class="stat-box">
                <div class="stat-number" id="totalCount">0</div>
                <div class="stat-label">Αποτελέσματα</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="matchCount">0</div>
                <div class="stat-label">Αντιστοίχηση</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="successRate">0%</div>
                <div class="stat-label">Επιτυχία</div>
            </div>
        </div>
        
        <div id="results" class="results"></div>
    </div>
    
    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
            document.getElementById(tab).classList.add('active');
            event.target.classList.add('active');
        }
        
        function singleLookup() {
            const input = document.getElementById('singleInput').value.trim();
            if (!input) { alert('Παρακαλώ εισάγετε κάτι'); return; }
            batchLookupInternal([input]);
        }
        
        function batchLookup() {
            const text = document.getElementById('batchInput').value.trim();
            if (!text) { alert('Παρακαλώ εισάγετε items'); return; }
            const items = text.split('\\n').map(s => s.trim()).filter(s => s);
            batchLookupInternal(items);
        }
        
        function batchLookupInternal(items) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Επεξεργασία...</div>';
            
            const aiProvider = document.getElementById('aiProvider').value;
            document.getElementById('aiStatus').textContent = '⏳ Processing with ' + aiProvider + '...';
            
            fetch('/api/lookup', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({items: items, ai_provider: aiProvider})
            })
            .then(r => r.json())
            .then(data => displayResults(data.results))
            .catch(e => {
                resultsDiv.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + e.message + '</div>';
            });
        }
        
        function displayResults(results) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '';
            
            let matchCount = 0;
            results.forEach(r => {
                if (r.match && r.match.taric_code) matchCount++;
                
                const card = document.createElement('div');
                card.className = 'result' + (r.match && r.match.taric_code ? ' success' : ' error');
                
                let html = '<div class="product-name">' + escapeHtml(r.input) + '</div>';
                
                if (r.match && r.match.taric_code) {
                    html += '<div class="taric-code">' + r.match.taric_code + '</div>';
                    html += '<div class="hs4">HS4: ' + r.match.hs4 + '</div>';
                    html += '<div class="description">' + escapeHtml(r.match.description) + '</div>';
                } else {
                    html += '<div class="description" style="color: #dc3545;">❌ Δεν βρέθηκε</div>';
                }
                
                if (r.source && r.source.source) {
                    html += '<div class="source">📊 ' + escapeHtml(r.source.source) + '</div>';
                }
                
                card.innerHTML = html;
                resultsDiv.appendChild(card);
            });
            
            const total = results.length;
            const rate = total > 0 ? Math.round((matchCount / total) * 100) : 0;
            
            document.getElementById('stats').style.display = 'grid';
            document.getElementById('totalCount').textContent = total;
            document.getElementById('matchCount').textContent = matchCount;
            document.getElementById('successRate').textContent = rate + '%';
                    document.getElementById('aiStatus').textContent = '✅ Complete (' + matchCount + '/' + total + ' matched)';
        }
        
        function escapeHtml(text) {
            const map = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'};
            return String(text).replace(/[&<>"']/g, m => map[m]);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/lookup', methods=['POST'])
def api_lookup():
    """API endpoint for TARIC lookup."""
    data = request.json
    items = data.get('items', [])
    ai_provider = data.get('ai_provider', 'openrouter')  # Default to OpenRouter
    
    results = []
    for item in items:
        try:
            result = resolve_item(item, ai_provider=ai_provider)
            # result is already a dict from resolve_item
            results.append(result)
        except Exception as e:
            results.append({
                'input': item,
                'error': str(e),
                'match': None
            })
    
    return jsonify({'results': results})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌐 TARIC Web Interface Starting...")
    print("="*60)
    print("\n✅ Open your browser to:")
    print("   → http://localhost:5000")
    print("\nGreek/English support enabled for all EU TARIC chapters")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
