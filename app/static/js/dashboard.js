// Dashboard JavaScript

const EYE_OPEN = '/static/img/open-eye.svg';
const EYE_CLOSED = '/static/img/closed-eye.svg';
// Hero values, shown only when their eye toggle is open
const heroVisible = { 'total-btc': false, 'total-invested': false };
let latestPortfolio = null;  // from GET /api/portfolio; amounts are strings

const MASK = '********';

// MSX stripe colours, one per transaction row
const STRIPES = ['--s1', '--s3', '--s7', '--s4', '--s2', '--s5', '--s6', '--s8'];

const TRASH_ICON = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">' +
    '<path d="M2 4h10M5 4V2.5h4V4M3.5 4l.7 8h5.6l.7-8" fill="none" stroke="currentColor" stroke-width="1.3" ' +
    'stroke-linecap="round" stroke-linejoin="round"/></svg>';

const PENCIL_ICON = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">' +
    '<path d="M9.5 2.5l2 2L5 11H3V9z M8 4l2 2" fill="none" stroke="currentColor" stroke-width="1.3" ' +
    'stroke-linecap="round" stroke-linejoin="round"/></svg>';

const BREAK_EVEN_NOTE = 'Sell everything at this price to end up even';

// API amounts arrive as exact decimal strings; convert only for display
function num(value) {
    return value === null || value === undefined ? null : Number(value);
}

// Hero sub-lines keep their label in the <p> and the number in its <span>
function setHeroSub(id, text) {
    document.querySelector(`#${id} span`).textContent = text;
}

// Show a signed P&L (optionally with a percentage) and colour it, or mask it
function setPnl(el, value, percent, visible) {
    el.classList.remove('profit', 'loss');
    if (!visible) {
        el.textContent = MASK;
        return;
    }
    if (value === null) {
        el.textContent = '—';
        return;
    }
    el.textContent = formatSignedCurrency(value) + (percent !== null ? ` ${formatPercent(percent)}` : '');
    if (value > 0) el.classList.add('profit');
    if (value < 0) el.classList.add('loss');
}

function renderHero() {
    const p = latestPortfolio;
    const showBtc = heroVisible['total-btc'];
    const showTotal = heroVisible['total-invested'];

    document.querySelector('[data-value-id="total-btc"]').textContent =
        showBtc && p ? formatBTC(p.held) : MASK;
    document.querySelector('[data-value-id="total-invested"]').textContent =
        showTotal && p ? formatCurrency(num(p.invested)) : MASK;

    // Profit/loss reveals the portfolio size, so it follows the "Total" toggle
    const profitLossEl = document.getElementById('total-profit-loss');
    profitLossEl.classList.remove('profit', 'loss');
    const total = p ? num(p.total_pnl) : null;
    if (total === null) {
        setHeroSub('total-profit-loss', '--');
    } else if (!showTotal) {
        setHeroSub('total-profit-loss', MASK);
    } else {
        setHeroSub('total-profit-loss', `${formatSignedCurrency(total)} ${formatPercent(num(p.total_pnl_percent))}`.trim());
        if (total > 0) profitLossEl.classList.add('profit');
        if (total < 0) profitLossEl.classList.add('loss');
    }

    // The asset card's value follows the "BTC" toggle
    let worth = '--';
    if (p && p.value !== null) {
        worth = showBtc ? `Worth ${formatCurrency(num(p.value))}` : `Worth ${MASK}`;
    }
    document.getElementById('asset-value').textContent = worth;

    Object.keys(heroVisible).forEach(id => {
        const toggle = document.querySelector(`[data-toggle="${id}"]`);
        toggle.querySelector('img').src = heroVisible[id] ? EYE_OPEN : EYE_CLOSED;
        toggle.setAttribute('aria-pressed', heroVisible[id]);
    });

    renderStats();
}

function renderStats() {
    const p = latestPortfolio;
    if (!p) return;

    const breakEven = num(p.break_even);
    const breakEvenEl = document.getElementById('stat-break-even');
    const noteEl = document.getElementById('stat-break-even-note');
    if (breakEven === null) {
        breakEvenEl.textContent = '—';
        noteEl.textContent = BREAK_EVEN_NOTE;
    } else if (breakEven < 0) {
        // Sales already returned more than was invested: the rest is free
        breakEvenEl.textContent = 'Free';
        noteEl.textContent = 'Your sales already returned more than you invested';
    } else {
        breakEvenEl.textContent = formatCurrency(breakEven);
        noteEl.textContent = BREAK_EVEN_NOTE;
    }

    const averageCost = num(p.average_cost);
    document.getElementById('stat-average-cost').textContent =
        averageCost === null ? '—' : formatCurrency(averageCost);

    // P&L reveals the portfolio size, so it follows the "Total" toggle
    const showTotal = heroVisible['total-invested'];
    setPnl(document.getElementById('stat-realized'), num(p.realized_pnl), null, showTotal);
    setPnl(document.getElementById('stat-unrealized'), num(p.unrealized_pnl), num(p.unrealized_pnl_percent), showTotal);
}

function renderAssets() {
    const p = latestPortfolio;
    document.getElementById('bitcoin-asset-card').classList.toggle('hidden', num(p.held) <= 0);
    document.getElementById('asset-price').textContent = formatCurrency(num(p.price));
}

// ---------- Portfolio ----------

async function fetchPortfolio() {
    const result = await apiRequest('/api/portfolio');
    if (!result.ok || !result.data.success) {
        showError('Could not load your portfolio', 'Please refresh the page.');
        return;
    }
    latestPortfolio = result.data.portfolio;
    setHeroSub('btc-price', formatCurrency(num(latestPortfolio.price)));
    renderAssets();
    renderHero();
}

async function fetchTrades() {
    const result = await apiRequest('/api/trades');
    if (result.ok && result.data.success) {
        renderTransactions(result.data.trades);
    }
}

function refresh() {
    fetchPortfolio();
    fetchTrades();
}

const SIDE_LABELS = { buy: 'Buy', sell: 'Sell', reward: 'Reward' };

function formatBreakEven(value) {
    if (value === null) return '—';
    return value < 0 ? 'Free' : formatCurrency(value);
}

function formatFee(trade) {
    if (num(trade.fee) === 0) return '—';
    // BTC fees are shown exactly as stored (e.g. 0.0001 BTC)
    return trade.fee_asset === 'BTC' ? `${trade.fee} BTC` : formatCurrency(num(trade.fee));
}

function renderTransactions(trades) {
    const tbody = document.getElementById('transactions-body');
    tbody.replaceChildren();
    document.getElementById('transactions-empty').classList.toggle('hidden', trades.length > 0);

    trades.forEach((trade, index) => {
        const row = document.createElement('tr');
        row.dataset.id = trade.id;
        const addCell = (text, className) => {
            const td = document.createElement('td');
            td.textContent = text;
            if (className) td.className = className;
            row.appendChild(td);
            return td;
        };

        const chipCell = addCell('', 'cell-chip');
        const chip = document.createElement('span');
        chip.className = 'stripe-chip';
        chip.setAttribute('aria-hidden', 'true');
        chip.style.background = `var(${STRIPES[index % STRIPES.length]})`;
        chipCell.appendChild(chip);

        const isSell = trade.side === 'sell';
        addCell(SIDE_LABELS[trade.side] || trade.side, 'cell-type');
        addCell(formatDate(trade.date));
        addCell(`${isSell ? '−' : '+'}${formatBTC(trade.btc)}`, 'num');
        addCell(trade.side === 'reward' ? '—' : formatCurrency(num(trade.price)), 'num');
        addCell(formatFee(trade), 'num');
        addCell(formatBreakEven(num(trade.break_even)), 'num');

        const realized = num(trade.realized_pnl);
        const pnlCell = addCell(realized === null ? '—' : formatSignedCurrency(realized), 'num cell-pnl');
        if (realized > 0) pnlCell.classList.add('profit');
        if (realized < 0) pnlCell.classList.add('loss');

        const notesCell = addCell(trade.notes || '', 'notes-cell');
        notesCell.title = trade.notes || '';

        const actionCell = addCell('', 'cell-actions');
        const actions = document.createElement('div');
        actions.className = 'row-actions';
        actionCell.appendChild(actions);

        const editButton = document.createElement('button');
        editButton.type = 'button';
        editButton.className = 'pill pill-icon edit-button';
        editButton.setAttribute('aria-label', 'Edit transaction');
        editButton.innerHTML = PENCIL_ICON;  // constant markup, no user data
        editButton.addEventListener('click', event => openPopup(event, trade));
        actions.appendChild(editButton);

        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'pill pill-icon delete-button';
        deleteButton.setAttribute('aria-label', 'Delete transaction');
        deleteButton.innerHTML = TRASH_ICON;  // constant markup, no user data
        deleteButton.addEventListener('click', () => deleteTrade(trade.id));
        actions.appendChild(deleteButton);

        tbody.appendChild(row);
    });
}

async function deleteTrade(tradeId) {
    if (!await confirmAction('Delete this transaction?', 'Delete')) {
        return;
    }

    showLoading('Deleting transaction...');
    const result = await apiRequest(`/api/trades/${tradeId}`, { method: 'DELETE' });

    if (result.ok && result.data.success) {
        showSuccess('Transaction has been deleted');
        refresh();
    } else {
        showError('Could not delete transaction', result.data.error);
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

// ---------- Add / edit transaction popup ----------

const popup = document.getElementById('trade-popup');
const tradeForm = document.getElementById('trade-form');
const fiatField = document.getElementById('fiat-field');
let popupTrigger = null;
let editingId = null;  // id of the trade being edited, or null when adding

function todayLocal() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function selectedSide() {
    return tradeForm.querySelector('input[name="side"]:checked').value;
}

// Rewards have no dollar amount; sells receive dollars instead of paying them
function updateSideFields() {
    const side = selectedSide();
    const isReward = side === 'reward';
    fiatField.classList.toggle('hidden', isReward);
    tradeForm.fiat.disabled = isReward;
    document.getElementById('fiat-label').textContent =
        side === 'sell' ? 'Amount received ($)' : 'Amount paid ($)';
    updatePriceHint();
}

function updatePriceHint() {
    const fiat = parseFloat(tradeForm.fiat.value);
    const btc = parseFloat(tradeForm.btc.value);
    document.getElementById('price-per-btc').textContent =
        selectedSide() !== 'reward' && fiat > 0 && btc > 0 ? `Price per BTC: ${formatCurrency(fiat / btc)}` : '';
}

function openPopup(event, trade = null) {
    popupTrigger = event && event.currentTarget ? event.currentTarget : document.activeElement;
    editingId = trade ? trade.id : null;
    tradeForm.reset();
    document.getElementById('popup-title').textContent = trade ? 'Edit Transaction' : 'Add Transaction';
    document.getElementById('trade-submit').textContent = trade ? 'Save changes' : 'Save';
    tradeForm.date.max = todayLocal();
    tradeForm.date.value = todayLocal();

    if (trade) {
        tradeForm.querySelector(`input[name="side"][value="${trade.side}"]`).checked = true;
        tradeForm.date.value = trade.date;
        tradeForm.btc.value = trade.btc;
        if (trade.side !== 'reward') tradeForm.fiat.value = trade.fiat;
        if (num(trade.fee) > 0) {
            tradeForm.fee.value = trade.fee;
            tradeForm.fee_asset.value = trade.fee_asset;
        }
        tradeForm.notes.value = trade.notes || '';
    }

    updateSideFields();
    popup.classList.remove('hidden');
    tradeForm.btc.focus();
}

function closePopup() {
    if (popup.classList.contains('hidden')) return;
    popup.classList.add('hidden');
    // Return focus to whatever opened the dialog
    if (popupTrigger) popupTrigger.focus();
}

tradeForm.addEventListener('input', updatePriceHint);
tradeForm.querySelectorAll('input[name="side"]').forEach(radio => {
    radio.addEventListener('change', updateSideFields);
});

tradeForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    // Amounts go to the API exactly as typed (strings), so no precision is lost
    const side = selectedSide();
    const body = {
        side,
        date: tradeForm.date.value,
        btc: tradeForm.btc.value,
        notes: tradeForm.notes.value
    };
    if (side !== 'reward') body.fiat = tradeForm.fiat.value;
    if (tradeForm.fee.value !== '') {
        body.fee = tradeForm.fee.value;
        body.fee_asset = tradeForm.fee_asset.value;
    }

    const editing = editingId !== null;
    showLoading('Saving transaction...');
    const result = await apiRequest(editing ? `/api/trades/${editingId}` : '/api/trades', {
        method: editing ? 'PUT' : 'POST',
        body: JSON.stringify(body)
    });

    if (result.ok && result.data.success) {
        closePopup();
        showSuccess(editing ? 'Transaction updated' : 'Transaction saved');
        refresh();
    } else {
        // The form stays open so nothing typed is lost
        showError('Could not save transaction', result.data.error || 'An error occurred.');
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
        if (e.key === 'Escape' && !document.querySelector('.swal2-container')) closePopup();
    });

    refresh();
    // Refresh prices every 60 seconds
    setInterval(refresh, 60000);
});
