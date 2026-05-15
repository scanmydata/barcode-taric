
        function switchTab(tab, button) {
            document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
            document.getElementById(tab).classList.add('active');
            if (button && button.classList) {
                button.classList.add('active');
            }
            
            // Load stored products when switching to stored tab
            if (tab === 'stored') {
                loadStoredProducts();
            }
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
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    resultsDiv.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + data.error + '</div>';
                    return;
                }
                displayResults(data.results);
            })
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
        
        function loadStoredProducts() {
            const container = document.getElementById('storedProductsContainer');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Φόρτωση αποθηκευμένων εγγραφών...</div>';
            
            fetch('/api/stored-products')
                .then(r => r.json())
                .then(data => displayStoredProductsTable(data.products))
                .catch(e => {
                    container.innerHTML = '<div class="result error"><strong>Σφάλμα:</strong> ' + e.message + '</div>';
                });
        }
        
        function displayStoredProductsTable(products) {
            const container = document.getElementById('storedProductsContainer');
            
            if (!products || products.length === 0) {
                container.innerHTML = '<div class="no-data">📭 Δεν υπάρχουν αποθηκευμένες εγγραφές</div>';
                return;
            }
            
            // Store products data globally for filtering/sorting
            window.allProducts = products;
            window.sortConfig = { key: 'barcode', direction: 'asc' };
            
            let html = '<div class="table-container"><table id="productsTable"><thead><tr>' +
                '<th class="sortable" onclick="sortTable(\'barcode\', event)">Barcode</th>' +
                '<th class="sortable" onclick="sortTable(\'taric_code\', event)">TARIC</th>' +
                '<th class="sortable" onclick="sortTable(\'hs4\', event)">HS4</th>' +
                '<th class="sortable" onclick="sortTable(\'product_name\', event)">Προϊόν</th>' +
                '<th class="sortable" onclick="sortTable(\'description\', event)">Περιγραφή (ΕΛ)</th>' +
                '<th class="sortable" onclick="sortTable(\'commercial_text\', event)">Περιγραφή (EN)</th>' +
                '<th class="sortable" onclick="sortTable(\'source\', event)">Πηγή</th>' +
                '</tr></thead><tbody id="productsTableBody">';
            
            products.forEach(p => {
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
        
        function sortTable(column, event) {
            event.preventDefault();
            
            const currentDirection = window.sortConfig.direction;
            const isAsc = currentDirection === 'asc';
            
            // Toggle direction if same column
            if (window.sortConfig.key === column) {
                window.sortConfig.direction = isAsc ? 'desc' : 'asc';
            } else {
                window.sortConfig.key = column;
                window.sortConfig.direction = 'asc';
            }
            
            // Update header styling
            document.querySelectorAll('table th').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
                th.classList.add('sortable');
            });
            
            const headers = document.querySelectorAll('table th');
            const columnIndex = Array.from(headers).findIndex(h => {
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
            
            // Sort the data
            window.allProducts.sort((a, b) => {
                let aVal = a[column] || '';
                let bVal = b[column] || '';
                
                // Handle numeric comparisons
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
            
            // Re-render table
            const tbody = document.getElementById('productsTableBody');
            tbody.innerHTML = '';
            
            window.allProducts.forEach(p => {
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
            
            Array.from(rows).forEach(row => {
                const cells = row.getElementsByTagName('td');
                let matches = false;
                
                // Search in all cells
                Array.from(cells).forEach(cell => {
                    if (cell.textContent.toLowerCase().includes(searchInput)) {
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
        
        function updateTableInfo(visibleCount) {
            const totalRecords = window.allProducts ? window.allProducts.length : 0;
            const visible = visibleCount !== undefined ? visibleCount : totalRecords;
            
            const infoSpan = document.getElementById('tableInfo');
            if (infoSpan) {
                infoSpan.textContent = `Εμφανιζόμενες: ${visible} / Σύνολο: ${totalRecords}`;
            }
            
            const visibleSpan = document.getElementById('visibleRecords');
            if (visibleSpan) {
                visibleSpan.textContent = visible;
            }
        }
        
        function clearTableFilters() {
            document.getElementById('tableSearch').value = '';
            filterTable();
            
            // Reset sort
            window.sortConfig = { key: 'barcode', direction: 'asc' };
            document.querySelectorAll('table th').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
                th.classList.add('sortable');
            });
            
            if (window.allProducts) {
                displayStoredProductsTable(window.allProducts);
            }
        }
        
        function exportStoredProducts() {
            fetch('/api/stored-products')
                .then(r => r.json())
                .then(data => {
                    let products = data.products;
                    if (!products || products.length === 0) {
                        alert('Δεν υπάρχουν αποθηκευμένες εγγραφές για εξαγωγή');
                        return;
                    }
                    
                    // Filter based on search if needed
                    const searchInput = document.getElementById('tableSearch').value.toLowerCase();
                    if (searchInput) {
                        products = products.filter(p => {
                            const barcode = p.barcode ? String(p.barcode).toLowerCase() : '';
                            const taric = p.taric_code ? String(p.taric_code).toLowerCase() : '';
                            const hs4 = p.hs4 ? String(p.hs4).toLowerCase() : '';
                            const name = p.product_name ? String(p.product_name).toLowerCase() : '';
                            const desc = p.description ? String(p.description).toLowerCase() : '';
                            const comm = p.commercial_text ? String(p.commercial_text).toLowerCase() : '';
                            const source = p.source ? String(p.source).toLowerCase() : '';
                            
                            return barcode.includes(searchInput) || 
                                   taric.includes(searchInput) ||
                                   hs4.includes(searchInput) ||
                                   name.includes(searchInput) ||
                                   desc.includes(searchInput) ||
                                   comm.includes(searchInput) ||
                                   source.includes(searchInput);
                        });
                    }
                    
                    if (products.length === 0) {
                        alert('Κανένα αποτέλεσμα για εξαγωγή με το τρέχον φίλτρο');
                        return;
                    }
                    
                    // Create CSV content
                    let csv = 'Barcode,TARIC,HS4,Προϊόν,Περιγραφή (ΕΛ),Περιγραφή (EN),Πηγή\n';
                    products.forEach(p => {
                        const row = [
                            p.barcode || '',
                            p.taric_code || '',
                            p.hs4 || '',
                            p.product_name || '',
                            p.description || '',
                            p.commercial_text || '',
                            p.source || ''
                        ].map(cell => '"' + (cell + '').replace(/"/g, '""') + '"').join(',');
                        csv += row + '\n';
                    });
                    
                    // Download CSV
                    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = 'stored_products_' + new Date().toISOString().split('T')[0] + '.csv';
                    link.click();
                    
                    alert('Εξαγωγή ' + products.length + ' εγγραφών ολοκληρώθηκε!');
                })
                .catch(e => alert('Σφάλμα κατά την εξαγωγή: ' + e.message));
        }
    