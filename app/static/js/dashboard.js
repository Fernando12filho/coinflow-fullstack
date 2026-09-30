// Dashboard JavaScript

const EYE_OPEN = '/static/img/open-eye.svg';
const EYE_CLOSED = '/static/img/closed-eye.svg';

// Hero values, shown only when their eye toggle is open
const heroVisible = { 'total-btc': false, 'total-invested': false };
let latestSummary = null;

const MASK = '********';

function renderHero() {
    const summary = latestSummary;
    const showBtc = heroVisible['total-btc'];
    const showTotal = heroVisible['total-invested'];

    document.querySelector('[data-value-id="total-btc"]').textContent =
        showBtc && summary ? formatBTC(summary.total_amount) : MASK;
    document.querySelector('[data-value-id="total-invested"]').textContent =
        showTotal && summary ? formatCurrency(summary.total_invested) : MASK;

    // Profit/loss reveals the portfolio size, so it follows the "Total" toggle
    const profitLossEl = document.getElementById('total-profit-loss');
    profitLossEl.classList.remove('profit', 'loss');
    if (!summary || summary.total_profit_loss === null) {
        profitLossEl.textContent = 'Profit / Loss: --';
    } else if (!showTotal) {
        profitLossEl.textContent = `Profit / Loss: ${MASK}`;
    } else {
        profitLossEl.textContent = `Profit / Loss: ${formatCurrency(summary.total_profit_loss)} ` +
            formatPercent(summary.total_profit_loss_percent);
        if (summary.total_profit_loss > 0) profitLossEl.classList.add('profit');
        if (summary.total_profit_loss < 0) profitLossEl.classList.add('loss');
    }

    // The asset card's value follows the "BTC" toggle
    let worth = '--';
    if (summary && summary.current_value !== null) {
        worth = showBtc ? `Worth ${formatCurrency(summary.current_value)}` : `Worth ${MASK}`;
    }
    document.getElementById('asset-value').textContent = worth;

    Object.keys(heroVisible).forEach(id => {
        const toggle = document.querySelector(`[data-toggle="${id}"]`);
        toggle.querySelector('img').src = heroVisible[id] ? EYE_OPEN : EYE_CLOSED;
        toggle.setAttribute('aria-pressed', heroVisible[id]);
    });
}

// ---------- Portfolio ----------

async function fetchHoldings() {
    const result = await apiRequest('/api/bitcoin/holdings');
    if (!result.ok || !result.data.success) {
        showError('Could not load your portfolio', 'Please refresh the page.');
        return;
    }

    const { holdings, summary } = result.data;

    latestSummary = summary;
    document.getElementById('btc-price').textContent =
        `BTC price: ${formatCurrency(summary.current_price)}`;

    renderAssets(summary);
    renderHero();
    renderTransactions(holdings);
}

function renderAssets(summary) {
    const card = document.getElementById('bitcoin-asset-card');
    card.classList.toggle('hidden', summary.total_amount <= 0);
    document.getElementById('asset-price').textContent = formatCurrency(summary.current_price);
}

function renderTransactions(holdings) {
    const tbody = document.getElementById('transactions-body');
    tbody.replaceChildren();
    document.getElementById('transactions-empty').classList.toggle('hidden', holdings.length > 0);

    holdings.forEach(holding => {
        const row = document.createElement('tr');
        const cells = [
            'Bitcoin',
            holding.id,
            formatDate(holding.purchase_date),
            formatBTC(holding.amount),
            formatCurrency(holding.invested),
            `${formatCurrency(holding.profit_loss)} ${formatPercent(holding.profit_loss_percent)}`
        ];
        cells.forEach(text => {
            const td = document.createElement('td');
            td.textContent = text;
            row.appendChild(td);
        });

        const profitLossCell = row.children[5];
        if (holding.profit_loss > 0) profitLossCell.classList.add('profit');
        if (holding.profit_loss < 0) profitLossCell.classList.add('loss');

        const actionCell = document.createElement('td');
        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'delete-button';
        deleteButton.textContent = 'Delete';
        deleteButton.addEventListener('click', () => deleteHolding(holding.id));
        actionCell.appendChild(deleteButton);
        row.appendChild(actionCell);

        tbody.appendChild(row);
    });
}

async function deleteHolding(holdingId) {
    if (!await confirmAction('Delete this transaction?', 'Delete')) {
        return;
    }

    showLoading('Deleting transaction...');
    const result = await apiRequest(`/api/bitcoin/holdings/${holdingId}`, { method: 'DELETE' });

    if (result.ok && result.data.success) {
        showSuccess('Transaction has been deleted');
        fetchHoldings();
    } else {
        showError('Error deleting transaction', result.data.error);
    }
}

// ---------- Tabs ----------

function showTab(name) {
    document.querySelectorAll('[data-tab]').forEach(button => {
        const active = button.dataset.tab === name;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active);
    });
    document.getElementById('tab-assets').classList.toggle('hidden', name !== 'assets');
    document.getElementById('tab-transactions').classList.toggle('hidden', name !== 'transactions');
}

// ---------- Add investment popup ----------

const popup = document.getElementById('investment-popup');
const investmentForm = document.getElementById('investment-form');

function todayLocal() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function openPopup() {
    investmentForm.reset();
    investmentForm.investment_date.value = todayLocal();
    investmentForm.investment_date.max = todayLocal();
    updatePriceHint();
    popup.classList.remove('hidden');
    investmentForm.investment_amount.focus();
}

function closePopup() {
    popup.classList.add('hidden');
}

function updatePriceHint() {
    const invested = parseFloat(investmentForm.investment_amount.value);
    const btc = parseFloat(investmentForm.crypto_amount.value);
    document.getElementById('price-per-btc').textContent =
        invested > 0 && btc > 0 ? `Price paid per BTC: ${formatCurrency(invested / btc)}` : '';
}

investmentForm.addEventListener('input', updatePriceHint);

investmentForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    const invested = parseFloat(investmentForm.investment_amount.value);
    const btc = parseFloat(investmentForm.crypto_amount.value);

    showLoading('Saving transaction...');
    const result = await apiRequest('/api/bitcoin/holdings', {
        method: 'POST',
        body: JSON.stringify({
            amount: btc,
            purchase_price: invested / btc,
            purchase_date: investmentForm.investment_date.value
        })
    });

    if (result.ok && result.data.success) {
        closePopup();
        showSuccess('Transaction has been saved');
        fetchHoldings();
    } else {
        showError('Error adding transaction', result.data.error || 'An error occurred.');
    }
});

// ---------- Init ----------

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-toggle]').forEach(button => {
        button.addEventListener('click', () => {
            const id = button.dataset.toggle;
            heroVisible[id] = !heroVisible[id];
            renderHero();
        });
    });

    document.querySelectorAll('[data-tab]').forEach(button => {
        button.addEventListener('click', () => showTab(button.dataset.tab));
    });

    document.querySelectorAll('[data-open-popup]').forEach(button => {
        button.addEventListener('click', openPopup);
    });
    document.querySelector('[data-close-popup]').addEventListener('click', closePopup);
    popup.addEventListener('click', e => {
        if (e.target === popup) closePopup();
    });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closePopup();
    });

    fetchHoldings();
    // Refresh prices every 60 seconds
    setInterval(fetchHoldings, 60000);
});
