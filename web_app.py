#!/usr/bin/env python3
"""Web-based TARIC lookup interface (works without X11 display)."""

from flask import Flask, Response, request, jsonify
import importlib
import subprocess
from datetime import date

import taric_lookup
from product_database import (
    create_product,
    delete_product_by_id,
    get_all_products_with_id,
    update_product_by_id,
)
import json
import os
import sys
import tempfile
from pathlib import Path

app = Flask(__name__)
UI_TEMPLATE_PATH = Path(__file__).with_name("web_app_ui.html")
TARIC_REFRESH_STATE_PATH = Path(__file__).with_name("db") / "taric_refresh_state.json"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
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
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
        }
        table thead {
            background: #667eea;
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
        }
        table th {
            padding: 12px;
            text-align: left;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }
        table th:hover {
            background: #764ba2;
        }
        table th.sortable::after {
            content: ' ⇅';
            opacity: 0.5;
            font-size: 12px;
        }
        table th.sort-asc::after {
            content: ' ↑';
            opacity: 1;
            color: #ffd700;
        }
        table th.sort-desc::after {
            content: ' ↓';
            opacity: 1;
            color: #ffd700;
        }
        table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
            max-width: 300px;
            word-wrap: break-word;
        }
        table tr:hover { background: #f5f5f5; }
        table tbody tr:nth-child(even) { background: #f9f9f9; }
        table tbody tr.hidden { display: none; }
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
            max-height: 600px;
            overflow-y: auto;
        }
        .no-data {
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 16px;
        }
        .table-controls {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 15px;
            margin-bottom: 15px;
            align-items: center;
        }
        .search-box {
            display: flex;
            gap: 10px;
        }
        .search-box input {
            flex: 1;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .search-box input:focus {
            outline: none;
            border-color: #667eea;
        }
        .table-info {
            text-align: right;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 TARIC Lookup</h1>
        <p class="subtitle">Ευρωπαϊκή Ταξινόμηση - European Product Classification</p>
        
        <div style="margin: 15px 0; padding: 10px; background: #f0f0f0; border-radius: 5px; display: flex; gap: 10px; align-items: center;">
            <label style="font-weight: bold; color: #333;">🤖 AI Provider:</label>
            <select id="aiProvider" style="padding: 8px; border: 1px solid #ccc; border-radius: 3px; font-weight: bold;">
                <option value="auto" selected>🧠 Auto (OpenRouter if available, otherwise Pollinations)</option>
                <option value="openrouter">⚡ OpenRouter (Fast, requires OPENROUTER_API_KEY)</option>
                <option value="deepinfra">🌐 DeepInfra (Serverless / demo endpoint)</option>
                <option value="duckduckgo">🦆 DuckDuckGo AI (VQD endpoint)</option>
                <option value="nerve">🔌 Nerve / WebUI endpoint</option>
                <option value="pollinations">🌊 Pollinations (Free fallback)</option>
                <option value="none">❌ No AI (Direct Match)</option>
            </select>
            <span id="aiStatus" style="font-size: 12px; color: #666; margin-left: 10px;">✅ Ready</span>
        </div>
        
        <div class="tab-buttons">
            <button id="btnSingleTab" class="tab-btn active" type="button" onclick="switchTab('single', this)">📦 Single</button>
            <button id="btnBatchTab" class="tab-btn" type="button" onclick="switchTab('batch', this)">📊 Batch</button>
            <button id="btnStoredTab" class="tab-btn" type="button" onclick="switchTab('stored', this)">💾 Αποθηκευμένα</button>
        </div>
        
        <div id="single" class="tab-content active">
            <div class="input-group">
                <input type="text" id="singleInput" placeholder="Barcode ή προϊόν (Enter barcode or product description)">
                <button id="btnSingleSearch" type="button" onclick="singleLookup()">🔍 Αναζήτηση</button>
            </div>
        </div>
        
        <div id="batch" class="tab-content">
            <div style="margin-bottom: 15px; display: grid; gap: 10px;">
                <label style="font-weight: bold; color: #333;">📁 Φόρτωση αρχείου:</label>
                <input type="file" id="uploadFile" accept=".txt,.csv,.tsv,.xlsx" />
                <button id="btnUploadFile" type="button" style="width: 100%;" onclick="uploadFile()">⬆️ Φόρτωση και Επεξεργασία</button>
            </div>
            <textarea id="batchInput" placeholder="Ένα ανά γραμμή (One per line)..."></textarea>
            <button id="btnBatchSubmit" type="button" style="width: 100%;" onclick="batchLookup()">📊 Αποστολή</button>
        </div>
        
        <div id="stored" class="tab-content">
            <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                <button id="btnLoadStored" type="button" style="flex: 1; background: #667eea;" onclick="loadStoredProducts()">🔄 Φόρτωση δεδομένων</button>
                <button id="btnExportStored" type="button" style="flex: 1; background: #28a745;" onclick="exportStoredProducts()">💾 Εξαγωγή CSV</button>
                <button id="btnClearFilters" type="button" style="flex: 1; background: #ff6b6b;" onclick="clearTableFilters()">🔄 Ξεκαθάρισμα φίλτρων</button>
            </div>
            <div class="table-controls">
                <div class="search-box">
                    <input type="text" id="tableSearch" placeholder="🔍 Αναζήτηση σε όλες τις στήλες..." onkeyup="filterTable()">
                </div>
                <div class="table-info">
                    <span id="tableInfo">Φόρτωση...</span>
                </div>
            </div>
            <div id="storedProductsContainer">
                <div class="loading"><div class="spinner"></div>Φόρτωση...</div>
            </div>
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
        // =====================================================
        // UTILITY FUNCTIONS
        // =====================================================
        function escapeHtml(text) {
            const map = {'&': '&', '<': '<', '>': '>', '"': '"', "'": '&#039;'};
            return String(text).replace(/[&<>"']/g, m => map[m]);
        }
        
        function updateTableInfo(visibleCount) {
            const totalRecords = window.allProducts ? window.allProducts.length : 0;
            const visible = visibleCount !== undefined ? visibleCount : totalRecords;
            
            const infoSpan = document.getElementById('tableInfo');
            if (infoSpan) {
                infoSpan.textContent = 'Εμφανιζόμενες: ' + visible + ' / Σύνολο: ' + totalRecords;
            }
            
            const visibleSpan = document.getElementById('visibleRecords');
            if (visibleSpan) {
                visibleSpan.textContent = visible;
            }
        }
        
        // =====================================================
        // TAB SWITCHING
        // =====================================================
        function switchTab(tab, button) {
            console.log('switchTab called: ' + tab);
            document.querySelectorAll('.tab-content').forEach(function(e) { e.classList.remove('active'); });
            document.querySelectorAll('.tab-btn').forEach(function(e) { e.classList.remove('active'); });
            document.getElementById(tab).classList.add('active');
            if (button && button.classList) {
                button.classList.add('active');
            }
            
            if (tab === 'stored') {
                loadStoredProducts();
            }
        }
        
        // =====================================================
        // LOOKUP FUNCTIONS
        // =====================================================
        function singleLookup() {
            const input = document.getElementById('singleInput').value.trim();
            if (!input) { alert('Παρακαλώ εισάγετε κάτι'); return; }
            batchLookupInternal([input]);
        }
        
        function batchLookup() {
            const text = document.getElementById('batchInput').value.trim();
            if (!text) { alert('Παρακαλώ εισάγετε items'); return; }
            const items = text.split('\n').map(function(s) { return s.trim(); }).filter(function(s) { return s; });
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
            .then(function(r) { return r.json(); })
            .then(function(data) { displayResults(data.results); })
            .catch(function(e) {
                resultsDiv.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + e.message + '</div>';
            });
        }
        
        function displayResults(results) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '';
            
            let matchCount = 0;
            results.forEach(function(r) {
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
        
        // =====================================================
        // FILE UPLOAD
        // =====================================================
        function uploadFile() {
            const fileInput = document.getElementById('uploadFile');
            if (!fileInput.files.length) { alert('Παρακαλώ επιλέξτε ένα αρχείο'); return; }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('ai_provider', document.getElementById('aiProvider').value);

            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Μεταφόρτωση αρχείου...</div>';
            document.getElementById('aiStatus').textContent = '⏳ Uploading file...';

            fetch('/api/lookup-file', {
                method: 'POST',
                body: formData
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    resultsDiv.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + data.error + '</div>';
                    return;
                }
                displayResults(data.results);
            })
            .catch(function(e) {
                resultsDiv.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + e.message + '</div>';
            });
        }
        
        // =====================================================
        // STORED PRODUCTS
        // =====================================================
        function loadStoredProducts() {
            const container = document.getElementById('storedProductsContainer');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Φόρτωση αποθηκευμένων εγγραφών...</div>';
            
            fetch('/api/stored-products')
                .then(function(r) { return r.json(); })
                .then(function(data) { displayStoredProductsTable(data.products); })
                .catch(function(e) {
                    container.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + e.message + '</div>';
                });
        }
        
        function displayStoredProductsTable(products) {
            const container = document.getElementById('storedProductsContainer');
            
            if (!products || products.length === 0) {
                container.innerHTML = '<div class="no-data">📭 Δεν υπάρχουν αποθηκευμένες εγγραφές</div>';
                return;
            }
            
            window.allProducts = products;
            window.sortConfig = { key: 'barcode', direction: 'asc' };
            
            let html = '<div class="table-container"><table id="productsTable"><thead><tr>' +
                '<th class="sortable" onclick="sortTable(event, \'barcode\')">Barcode</th>' +
                '<th class="sortable" onclick="sortTable(event, \'taric_code\')">TARIC</th>' +
                '<th class="sortable" onclick="sortTable(event, \'hs4\')">HS4</th>' +
                '<th class="sortable" onclick="sortTable(event, \'product_name\')">Προϊόν</th>' +
                '<th class="sortable" onclick="sortTable(event, \'description\')">Περιγραφή (ΕΛ)</th>' +
                '<th class="sortable" onclick="sortTable(event, \'commercial_text\')">Περιγραφή (EN)</th>' +
                '<th class="sortable" onclick="sortTable(event, \'source\')">Πηγή</th>' +
                '</tr></thead><tbody id="productsTableBody">';
            
            products.forEach(function(p) {
                const barcode = p.barcode ? escapeHtml(p.barcode) : '-';
                const taric = p.taric_code ? escapeHtml(p.taric_code) : '-';
                const hs4 = p.hs4 ? escapeHtml(p.hs4) : '-';
                const productName = escapeHtml(p.product_name || '');
                const desc = escapeHtml(p.description || '');
                const commercialText = escapeHtml(p.commercial_text || '');
                const source = escapeHtml(p.source || '');
                
                html += '<tr>' +
                    '<td style="font-family: monospace; font-weight: bold;">' + barcode + '</td>' +
                    '<td style="font-family: monospace; color: #667eea; font-weight: bold;">' + taric + '</td>' +
                    '<td>' + hs4 + '</td>' +
                    '<td>' + productName + '</td>' +
                    '<td>' + desc + '</td>' +
                    '<td>' + commercialText + '</td>' +
                    '<td style="font-size: 12px; color: #666;">' + source + '</td>' +
                    '</tr>';
            });
            
            html += '</tbody></table></div>';
            html += '<div style="margin-top: 15px; padding: 10px; background: #f0f0f0; border-radius: 5px;">' +
                '📊 Σύνολο εγγραφών: <strong id="totalRecords">' + products.length + '</strong>' +
                ' | Εμφανιζόμενες: <strong id="visibleRecords">' + products.length + '</strong>' +
                '</div>';
            
            container.innerHTML = html;
            updateTableInfo();
        }
        
        function sortTable(event, column) {
            event.preventDefault();
            
            const currentDirection = window.sortConfig.direction;
            const isAsc = currentDirection === 'asc';
            
            if (window.sortConfig.key === column) {
                window.sortConfig.direction = isAsc ? 'desc' : 'asc';
            } else {
                window.sortConfig.key = column;
                window.sortConfig.direction = 'asc';
            }
            
            document.querySelectorAll('table th').forEach(function(th) {
                th.classList.remove('sort-asc', 'sort-desc');
                th.classList.add('sortable');
            });
            
            const headers = document.querySelectorAll('table th');
            const columnIndex = Array.from(headers).findIndex(function(h) {
                const colName = h.textContent.trim();
                return (column === 'barcode' && colName === 'Barcode') ||
                       (column === 'taric_code' && colName === 'TARIC') ||
                       (column === 'hs4' && colName === 'HS4') ||
                       (column === 'product_name' && colName === 'Προϊόν') ||
                       (column === 'description' && colName === 'Περιγραφή (ΕΛ)') ||
                       (column === 'commercial_text' && colName === 'Περιγραφή (EN)') ||
                       (column === 'source' && colName === 'Πηγή');
            });
            
            if (columnIndex >= 0) {
                headers[columnIndex].classList.add(window.sortConfig.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
            
            window.allProducts.sort(function(a, b) {
                let aVal = a[column] || '';
                let bVal = b[column] || '';
                
                if (!isNaN(aVal) && !isNaN(bVal) && aVal !== '' && bVal !== '') {
                    aVal = parseFloat(aVal);
                    bVal = parseFloat(bVal);
                } else {
                    aVal = String(aVal).toLowerCase();
                    bVal = String(bVal).toLowerCase();
                }
                
                if (aVal < bVal) return window.sortConfig.direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return window.sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
            
            const tbody = document.getElementById('productsTableBody');
            tbody.innerHTML = '';
            
            window.allProducts.forEach(function(p) {
                const barcode = p.barcode ? escapeHtml(p.barcode) : '-';
                const taric = p.taric_code ? escapeHtml(p.taric_code) : '-';
                const hs4 = p.hs4 ? escapeHtml(p.hs4) : '-';
                const productName = escapeHtml(p.product_name || '');
                const desc = escapeHtml(p.description || '');
                const commercialText = escapeHtml(p.commercial_text || '');
                const source = escapeHtml(p.source || '');
                
                const row = document.createElement('tr');
                row.innerHTML = '<td style="font-family: monospace; font-weight: bold;">' + barcode + '</td>' +
                    '<td style="font-family: monospace; color: #667eea; font-weight: bold;">' + taric + '</td>' +
                    '<td>' + hs4 + '</td>' +
                    '<td>' + productName + '</td>' +
                    '<td>' + desc + '</td>' +
                    '<td>' + commercialText + '</td>' +
                    '<td style="font-size: 12px; color: #666;">' + source + '</td>';
                tbody.appendChild(row);
            });
            
            updateTableInfo();
        }
        
        function filterTable() {
            const searchInput = document.getElementById('tableSearch').value.toLowerCase();
            const tbody = document.getElementById('productsTableBody');
            
            if (!tbody) return;
            
            const rows = tbody.getElementsByTagName('tr');
            let visibleCount = 0;
            
            Array.from(rows).forEach(function(row) {
                const cells = row.getElementsByTagName('td');
                let matches = false;
                
                Array.from(cells).forEach(function(cell) {
                    if (cell.textContent.toLowerCase().indexOf(searchInput) !== -1) {
                        matches = true;
                    }
                });
                
                if (matches || searchInput === '') {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            updateTableInfo(visibleCount);
        }
        
        function clearTableFilters() {
            document.getElementById('tableSearch').value = '';
            filterTable();
            
            window.sortConfig = { key: 'barcode', direction: 'asc' };
            document.querySelectorAll('table th').forEach(function(th) {
                th.classList.remove('sort-asc', 'sort-desc');
                th.classList.add('sortable');
            });
            
            if (window.allProducts) {
                displayStoredProductsTable(window.allProducts);
            }
        }
        
        function exportStoredProducts() {
            fetch('/api/stored-products')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    let products = data.products;
                    if (!products || products.length === 0) {
                        alert('Δεν υπάρχουν αποθηκευμένες εγγραφές για εξαγωγή');
                        return;
                    }
                    
                    const searchInput = document.getElementById('tableSearch').value.toLowerCase();
                    if (searchInput) {
                        products = products.filter(function(p) {
                            const barcode = p.barcode ? String(p.barcode).toLowerCase() : '';
                            const taric = p.taric_code ? String(p.taric_code).toLowerCase() : '';
                            const hs4 = p.hs4 ? String(p.hs4).toLowerCase() : '';
                            const name = p.product_name ? String(p.product_name).toLowerCase() : '';
                            const desc = p.description ? String(p.description).toLowerCase() : '';
                            const comm = p.commercial_text ? String(p.commercial_text).toLowerCase() : '';
                            const source = p.source ? String(p.source).toLowerCase() : '';
                            
                            return barcode.indexOf(searchInput) !== -1 || 
                                   taric.indexOf(searchInput) !== -1 ||
                                   hs4.indexOf(searchInput) !== -1 ||
                                   name.indexOf(searchInput) !== -1 ||
                                   desc.indexOf(searchInput) !== -1 ||
                                   comm.indexOf(searchInput) !== -1 ||
                                   source.indexOf(searchInput) !== -1;
                        });
                    }
                    
                    if (products.length === 0) {
                        alert('Κανένα αποτέλεσμα για εξαγωγή με το τρέχον φίλτρο');
                        return;
                    }
                    
                    let csv = 'Barcode,TARIC,HS4,Προϊόν,Περιγραφή (ΕΛ),Περιγραφή (EN),Πηγή\\n';
                    products.forEach(function(p) {
                        const row = [
                            p.barcode || '',
                            p.taric_code || '',
                            p.hs4 || '',
                            p.product_name || '',
                            p.description || '',
                            p.commercial_text || '',
                            p.source || ''
                        ].map(function(cell) { return '"' + (cell + '').replace(/"/g, '""') + '"'; }).join(',');
                        csv += row + '\\n';
                    });
                    
                    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = 'stored_products_' + new Date().toISOString().split('T')[0] + '.csv';
                    link.click();
                    
                    alert('Εξαγωγή ' + products.length + ' εγγραφών ολοκληρώθηκε!');
                })
                .catch(function(e) { alert('Σφάλμα κατά την εξαγωγή: ' + e.message); });
        }
        
        // =====================================================
        // INITIALIZATION - Run when DOM is ready
        // =====================================================
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM Content Loaded - Initializing...');
            
            // Tab buttons
            document.getElementById('btnSingleTab').addEventListener('click', function() { switchTab('single', this); });
            document.getElementById('btnBatchTab').addEventListener('click', function() { switchTab('batch', this); });
            document.getElementById('btnStoredTab').addEventListener('click', function() { switchTab('stored', this); });
            
            // Action buttons
            document.getElementById('btnSingleSearch').addEventListener('click', singleLookup);
            document.getElementById('btnUploadFile').addEventListener('click', uploadFile);
            document.getElementById('btnBatchSubmit').addEventListener('click', batchLookup);
            document.getElementById('btnLoadStored').addEventListener('click', loadStoredProducts);
            document.getElementById('btnExportStored').addEventListener('click', exportStoredProducts);
            document.getElementById('btnClearFilters').addEventListener('click', clearTableFilters);
            
            // Enter key on single input
            document.getElementById('singleInput').addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    singleLookup();
                }
            });
            
            // Table search
            document.getElementById('tableSearch').addEventListener('input', filterTable);
            
            console.log('All event listeners attached successfully!');
        });
    </script>
</body>
</html>
"""


def _read_taric_refresh_state() -> dict[str, str]:
    if not TARIC_REFRESH_STATE_PATH.is_file():
        return {}

    try:
        return json.loads(TARIC_REFRESH_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_taric_refresh_state(state: dict[str, str]) -> None:
    TARIC_REFRESH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARIC_REFRESH_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def refresh_taric_catalog_if_needed(*, force: bool = False) -> bool:
    today = date.today().isoformat()
    state = _read_taric_refresh_state()
    if not force and state.get("last_successful_refresh") == today:
        print(f"TARIC catalog already refreshed for {today}")
        return False

    generator_script = Path(__file__).with_name("generate_taric_catalog.py")
    print("Refreshing TARIC catalog from the local EU-derived generator...")

    try:
        completed = subprocess.run(
            [sys.executable, str(generator_script)],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except OSError as exc:
        print(f"TARIC refresh failed to start: {exc}")
        return False

    if completed.returncode != 0:
        print("TARIC refresh failed:")
        if completed.stderr:
            print(completed.stderr)
        return False

    importlib.reload(taric_lookup)
    _write_taric_refresh_state(
        {
            "last_successful_refresh": today,
            "source": "generate_taric_catalog.py",
        }
    )
    print(f"TARIC catalog refreshed for {today}")
    return True

@app.route('/')
def index():
    return Response(UI_TEMPLATE_PATH.read_text(encoding='utf-8'), mimetype='text/html')

@app.route('/api/lookup', methods=['POST'])
def api_lookup():
    """API endpoint for TARIC lookup."""
    data = request.json
    items = data.get('items', [])
    ai_provider = data.get('ai_provider', 'auto')
    
    results = []
    for item in items:
        try:
            result = taric_lookup.resolve_item(item, ai_provider=ai_provider)
            results.append(result)
        except Exception as e:
            results.append({
                'input': item,
                'error': str(e),
                'match': None
            })
    
    return jsonify({'results': results})


@app.route('/api/lookup-file', methods=['POST'])
def api_lookup_file():
    """API endpoint for TARIC lookup from uploaded file."""
    uploaded = request.files.get('file')
    ai_provider = request.form.get('ai_provider', 'auto')

    if not uploaded:
        return jsonify({'error': 'No file was uploaded'}), 400

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in {'.txt', '.csv', '.tsv', '.xlsx'}:
        return jsonify({'error': 'Unsupported file type. Use .txt, .csv, .tsv, or .xlsx'}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = Path(tmp.name)

    try:
        items = taric_lookup.load_inputs(tmp_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        tmp_path.unlink(missing_ok=True)

    results = []
    for item in items:
        try:
            results.append(taric_lookup.resolve_item(item, ai_provider=ai_provider))
        except Exception as e:
            results.append({
                'input': item,
                'error': str(e),
                'match': None
            })

    return jsonify({'results': results})


@app.route('/api/stored-products', methods=['GET'])
def api_stored_products():
    """API endpoint to fetch all stored products from database."""
    try:
        return jsonify({'products': get_all_products_with_id()})
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500


@app.route('/api/stored-products', methods=['POST'])
def api_create_stored_product():
    payload = request.json or {}
    if not payload.get('product_name_en') and payload.get('product_name'):
        translated_name = taric_lookup.ai_translate_text(
            str(payload.get('product_name')),
            target_language='en',
            provider='auto',
        )
        if translated_name and not taric_lookup._contains_greek(translated_name):
            payload['product_name_en'] = translated_name
        else:
            payload['product_name_en'] = taric_lookup.parser_rewrite_to_customs_text(str(payload.get('product_name')))
    created_id = create_product(payload)
    if created_id is None:
        return jsonify({'error': 'Failed to create product'}), 400
    return jsonify({'ok': True, 'id': created_id})


@app.route('/api/stored-products/<int:product_id>', methods=['PUT'])
def api_update_stored_product(product_id: int):
    payload = request.json or {}
    if not payload.get('product_name_en') and payload.get('product_name'):
        translated_name = taric_lookup.ai_translate_text(
            str(payload.get('product_name')),
            target_language='en',
            provider='auto',
        )
        if translated_name and not taric_lookup._contains_greek(translated_name):
            payload['product_name_en'] = translated_name
        else:
            payload['product_name_en'] = taric_lookup.parser_rewrite_to_customs_text(str(payload.get('product_name')))
    updated = update_product_by_id(product_id, payload)
    if not updated:
        return jsonify({'error': 'Product not found or update failed'}), 404
    return jsonify({'ok': True})


@app.route('/api/stored-products/<int:product_id>', methods=['DELETE'])
def api_delete_stored_product(product_id: int):
    deleted = delete_product_by_id(product_id)
    if not deleted:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify({'ok': True})

if __name__ == '__main__':
    import sys
    # Enable UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    
    print("\n" + "="*60)
    print("TARIC Web Interface Starting...")
    print("="*60)
    print("\nOpen your browser to:")
    print("   -> http://localhost:5000")
    print("\nGreek/English support enabled for all EU TARIC chapters")
    refresh_taric_catalog_if_needed()
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False, use_debugger=True)
