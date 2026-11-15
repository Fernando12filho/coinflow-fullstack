// Main JavaScript - Common functionality

// Trash icon for delete buttons (constant markup, safe for innerHTML)
const TRASH_ICON = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">' +
    '<path d="M2 4h10M5 4V2.5h4V4M3.5 4l.7 8h5.6l.7-8" fill="none" stroke="currentColor" stroke-width="1.3" ' +
    'stroke-linecap="round" stroke-linejoin="round"/></svg>';

// ---------- Formatting (follows the user's Settings) ----------

// Settings embedded by base.html for logged-in users: {currency, btc_unit, locale}
const USER_SETTINGS = (() => {
    try {
        const el = document.getElementById('user-settings');
        return el ? JSON.parse(el.textContent) || {} : {};
    } catch (error) {
        return {};
    }
})();

// Currency used when none is given; pages update it from API responses
let displayCurrency = USER_SETTINGS.currency || 'USD';

// undefined lets the browser pick its own language ("Automatic")
function userLocale() {
    return USER_SETTINGS.locale && USER_SETTINGS.locale !== 'auto' ? USER_SETTINGS.locale : undefined;
}

function formatCurrency(value, currency = displayCurrency) {
    if (value === null || value === undefined) {
        return '—';
    }
    return new Intl.NumberFormat(userLocale(), {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// The symbol for a currency in the user's number format (e.g. "R$", "US$", "€")
function currencySymbol(currency = displayCurrency) {
    const parts = new Intl.NumberFormat(userLocale(), { style: 'currency', currency }).formatToParts(0);
    const symbol = parts.find(part => part.type === 'currency');
    return symbol ? symbol.value : currency;
}

// BTC with 8 decimals, or whole satoshis, depending on Settings
function formatBTC(value) {
    const btc = Number(value);
    if (USER_SETTINGS.btc_unit === 'sats') {
        return `${new Intl.NumberFormat(userLocale()).format(Math.round(btc * 1e8))} sats`;
    }
    return new Intl.NumberFormat(userLocale(), {
        minimumFractionDigits: 8,
        maximumFractionDigits: 8
    }).format(btc);
}

// Format money with an explicit sign (+$5.00 / −$5.00) so gains and losses
// don't rely on colour alone
function formatSignedCurrency(value, currency = displayCurrency) {
    if (value === null || value === undefined) {
        return '—';
    }
    const sign = value > 0 ? '+' : value < 0 ? '−' : '';
    return sign + formatCurrency(Math.abs(value), currency);
}

function formatNumber(value, decimals) {
    return new Intl.NumberFormat(userLocale(), {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

// Format a signed percentage, or nothing when unknown
function formatPercent(value) {
    if (value === null || value === undefined) {
        return '';
    }
    const sign = value > 0 ? '+' : value < 0 ? '−' : '';
    return `(${sign}${formatNumber(Math.abs(value), 2)}%)`;
}

// Format a date. Dates are stored in UTC, so display them in UTC
// to avoid showing the previous day in timezones behind UTC.
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString(userLocale(), {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        timeZone: 'UTC'
    });
}

// Make API request
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (response.status === 401) {
            window.location.href = '/auth/login';
            return { ok: false, data: {} };
        }

        const data = await response.json();
        return { ok: response.ok, data };
    } catch (error) {
        console.error('API request failed:', error);
        return { ok: false, data: {}, error: error.message };
    }
}

// ---------- Popups (SweetAlert2, with a plain fallback if it failed to load) ----------

function showLoading(title) {
    if (!window.Swal) return;
    Swal.fire({
        title,
        showConfirmButton: false,
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading()
    });
}

function hideLoading() {
    if (window.Swal) Swal.close();
}

function showSuccess(title) {
    if (!window.Swal) return;
    Swal.fire({ icon: 'success', title, timer: 1500, showConfirmButton: false });
}

function showError(title, text) {
    if (!window.Swal) {
        alert(text ? `${title}\n${text}` : title);
        return;
    }
    Swal.fire({ icon: 'error', title, text });
}

async function confirmAction(title, confirmButtonText) {
    if (!window.Swal) {
        return confirm(title);
    }
    const result = await Swal.fire({
        icon: 'warning',
        title,
        showCancelButton: true,
        confirmButtonText,
        customClass: { confirmButton: 'swal-danger' }
    });
    return result.isConfirmed;
}

// Show Flask flash messages as popups
function showFlashMessages() {
    const el = document.getElementById('flash-data');
    const messages = el ? JSON.parse(el.textContent) : [];
    if (messages.length === 0) return;

    const [category, message] = messages[messages.length - 1];
    if (category === 'error') {
        showError(message);
    } else if (window.Swal) {
        const icon = ['success', 'warning', 'info'].includes(category) ? category : 'info';
        Swal.fire({ icon, title: message, timer: 1800, showConfirmButton: false });
    }
}

// Desktop app: show "Update available" when GitHub has a newer release
async function checkForUpdates() {
    const link = document.getElementById('update-link');
    if (!link) return;
    const result = await apiRequest('/api/updates');
    const update = result.ok && result.data.success ? result.data.update : null;
    if (!update) return;
    link.textContent = `Update available: v${update.version}`;
    link.href = update.url;
    link.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', function() {
    showFlashMessages();
    checkForUpdates();

    // Loading popup while login/register forms submit
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', () => showLoading(form.dataset.loading));
    });
});
