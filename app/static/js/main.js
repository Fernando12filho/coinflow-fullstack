// Main JavaScript - Common functionality

// Format currency
function formatCurrency(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Format Bitcoin amount
function formatBTC(value) {
    return parseFloat(value).toFixed(8);
}

// Format a percentage, or nothing when unknown
function formatPercent(value) {
    return value === null || value === undefined ? '' : `(${value.toFixed(2)}%)`;
}

// Format a purchase date. Dates are stored in UTC, so display them in UTC
// to avoid showing the previous day in timezones behind UTC.
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
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

function showSuccess(title) {
    if (!window.Swal) return;
    Swal.fire({ icon: 'success', title, timer: 1500, showConfirmButton: false });
}

function showError(title, text) {
    if (!window.Swal) {
        alert(text ? `${title}\n${text}` : title);
        return;
    }
    Swal.fire({ icon: 'error', title, text, confirmButtonColor: '#0088cc' });
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
        confirmButtonColor: '#c04848'
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

document.addEventListener('DOMContentLoaded', function() {
    showFlashMessages();

    // Loading popup while login/register forms submit
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', () => showLoading(form.dataset.loading));
    });
});
