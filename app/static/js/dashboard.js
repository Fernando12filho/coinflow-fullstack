// Dashboard JavaScript

let currentPrice = 0;

// Fetch current Bitcoin price
async function fetchCurrentPrice() {
    const loadingEl = document.getElementById('current-price-loading');
    const displayEl = document.getElementById('current-price-display');
    const priceEl = document.getElementById('current-btc-price');
    const timestampEl = document.getElementById('price-timestamp');

    try {
        const result = await apiRequest('/api/bitcoin/price');
        
        if (result.ok && result.data.success) {
            currentPrice = result.data.price;
            priceEl.textContent = currentPrice.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            timestampEl.textContent = new Date().toLocaleTimeString();
            loadingEl.style.display = 'none';
            displayEl.style.display = 'block';
        } else {
            loadingEl.textContent = 'Unable to load price';
        }
    } catch (error) {
        console.error('Error fetching price:', error);
        loadingEl.textContent = 'Error loading price';
    }
}

// Fetch user's holdings
async function fetchHoldings() {
    const loadingEl = document.getElementById('portfolio-loading');
    const displayEl = document.getElementById('portfolio-display');
    const emptyEl = document.getElementById('holdings-empty');
    const tableContainer = document.getElementById('holdings-table-container');

    try {
        const result = await apiRequest('/api/bitcoin/holdings');
        
        if (result.ok && result.data.success) {
            const { holdings, summary } = result.data;
            
            // Update summary
            document.getElementById('total-btc').textContent = formatBTC(summary.total_amount);
            document.getElementById('total-invested').textContent = formatCurrency(summary.total_invested);
            document.getElementById('current-value').textContent = formatCurrency(summary.current_value);
            document.getElementById('profit-loss').textContent = formatCurrency(summary.total_profit_loss);
            document.getElementById('profit-loss-percent').textContent =
                formatPercent(summary.total_profit_loss_percent);
            
            // Update profit/loss card color
            const profitLossCard = document.getElementById('profit-loss-card');
            profitLossCard.classList.remove('positive', 'negative');
            if (summary.total_profit_loss > 0) {
                profitLossCard.classList.add('positive');
            } else if (summary.total_profit_loss < 0) {
                profitLossCard.classList.add('negative');
            }
            
            loadingEl.style.display = 'none';
            displayEl.style.display = 'block';
            
            // Update holdings table
            if (holdings.length === 0) {
                emptyEl.style.display = 'block';
                tableContainer.style.display = 'none';
            } else {
                emptyEl.style.display = 'none';
                tableContainer.style.display = 'block';
                renderHoldingsTable(holdings);
            }
        } else {
            loadingEl.textContent = 'Error loading portfolio';
        }
    } catch (error) {
        console.error('Error fetching holdings:', error);
        loadingEl.textContent = 'Error loading portfolio';
    }
}

// Render holdings table
function renderHoldingsTable(holdings) {
    const tbody = document.getElementById('holdings-tbody');
    tbody.innerHTML = '';
    
    holdings.forEach(holding => {
        const row = document.createElement('tr');
        let profitLossClass = '';
        if (holding.profit_loss !== null) {
            profitLossClass = holding.profit_loss >= 0 ? 'profit' : 'loss';
        }
        
        row.innerHTML = `
            <td>${formatDate(holding.purchase_date)}</td>
            <td>${formatBTC(holding.amount)}</td>
            <td>${formatCurrency(holding.purchase_price)}</td>
            <td>${formatCurrency(holding.invested)}</td>
            <td>${formatCurrency(holding.current_value)}</td>
            <td class="${profitLossClass}">
                ${formatCurrency(holding.profit_loss)}<br>
                <small>${formatPercent(holding.profit_loss_percent)}</small>
            </td>
            <td>${holding.notes ? escapeHtml(holding.notes) : '-'}</td>
            <td>
                <button class="btn-delete" onclick="deleteHolding(${holding.id})">Delete</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Add new holding
document.getElementById('add-holding-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const amount = document.getElementById('amount').value;
    const purchasePrice = document.getElementById('purchase-price').value;
    const notes = document.getElementById('notes').value;
    
    const result = await apiRequest('/api/bitcoin/holdings', {
        method: 'POST',
        body: JSON.stringify({
            amount: parseFloat(amount),
            purchase_price: parseFloat(purchasePrice),
            notes
        })
    });
    
    if (result.ok && result.data.success) {
        showMessage('add-holding-message', 'Holding added successfully!', 'success');
        
        // Clear form
        document.getElementById('amount').value = '';
        document.getElementById('purchase-price').value = '';
        document.getElementById('notes').value = '';
        
        // Refresh holdings
        fetchHoldings();
    } else {
        const errorMsg = result.data?.error || 'Failed to add holding';
        showMessage('add-holding-message', errorMsg, 'error');
    }
});

// Delete holding
async function deleteHolding(holdingId) {
    if (!confirm('Are you sure you want to delete this holding?')) {
        return;
    }
    
    const result = await apiRequest(`/api/bitcoin/holdings/${holdingId}`, {
        method: 'DELETE'
    });
    
    if (result.ok && result.data.success) {
        fetchHoldings();
    } else {
        alert('Failed to delete holding');
    }
}

// Check newsletter subscription status
async function checkNewsletterStatus() {
    const loadingEl = document.getElementById('newsletter-status-loading');
    const subscribedEl = document.getElementById('newsletter-subscribed');
    const notSubscribedEl = document.getElementById('newsletter-not-subscribed');

    try {
        const result = await apiRequest('/api/newsletter/status');
        
        if (result.ok && result.data.success) {
            loadingEl.style.display = 'none';
            
            if (result.data.subscribed) {
                document.getElementById('subscribed-email').textContent = result.data.email;
                subscribedEl.style.display = 'block';
                notSubscribedEl.style.display = 'none';
            } else {
                subscribedEl.style.display = 'none';
                notSubscribedEl.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error checking newsletter status:', error);
        loadingEl.textContent = 'Error loading status';
    }
}

// Handle newsletter subscription from dashboard
document.getElementById('dashboard-newsletter-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('dashboard-newsletter-email').value;
    
    const result = await apiRequest('/api/newsletter/subscribe', {
        method: 'POST',
        body: JSON.stringify({ email })
    });
    
    if (result.ok && result.data.success) {
        showMessage('newsletter-dashboard-message', result.data.message, 'success');
        checkNewsletterStatus();
    } else {
        const errorMsg = result.data?.error || 'Subscription failed';
        showMessage('newsletter-dashboard-message', errorMsg, 'error');
    }
});

// Handle unsubscribe
document.getElementById('unsubscribe-btn')?.addEventListener('click', async function() {
    if (!confirm('Are you sure you want to unsubscribe from the newsletter?')) {
        return;
    }
    
    const result = await apiRequest('/api/newsletter/unsubscribe', {
        method: 'POST'
    });
    
    if (result.ok && result.data.success) {
        showMessage('newsletter-dashboard-message', result.data.message, 'success');
        checkNewsletterStatus();
    } else {
        const errorMsg = result.data?.error || 'Unsubscribe failed';
        showMessage('newsletter-dashboard-message', errorMsg, 'error');
    }
});

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    fetchCurrentPrice();
    fetchHoldings();
    checkNewsletterStatus();
    
    // Refresh data every 60 seconds
    setInterval(() => {
        fetchCurrentPrice();
        fetchHoldings();
    }, 60000);
});
