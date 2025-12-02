// Home page JavaScript

// Fetch and display Bitcoin price
async function fetchBitcoinPrice() {
    const loadingEl = document.getElementById('btc-price-loading');
    const displayEl = document.getElementById('btc-price-display');
    const priceEl = document.getElementById('btc-price');

    try {
        const result = await apiRequest('/api/bitcoin/price');
        
        if (result.ok && result.data.success) {
            priceEl.textContent = formatCurrency(result.data.price);
            loadingEl.style.display = 'none';
            displayEl.style.display = 'block';
        } else {
            loadingEl.textContent = 'Unable to load price';
        }
    } catch (error) {
        console.error('Error fetching Bitcoin price:', error);
        loadingEl.textContent = 'Error loading price';
    }
}

// Handle newsletter subscription
document.getElementById('newsletter-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const emailInput = document.getElementById('newsletter-email');
    const email = emailInput.value;
    
    const result = await apiRequest('/api/newsletter/subscribe', {
        method: 'POST',
        body: JSON.stringify({ email })
    });
    
    if (result.ok && result.data.success) {
        showMessage('newsletter-message', result.data.message, 'success');
        emailInput.value = '';
    } else {
        const errorMsg = result.data?.error || 'Subscription failed';
        showMessage('newsletter-message', errorMsg, 'error');
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    fetchBitcoinPrice();
    
    // Refresh price every 60 seconds
    setInterval(fetchBitcoinPrice, 60000);
});
