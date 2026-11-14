// Import page: preview an exchange CSV, import it, and manage imported files

const PROVIDERS = { kraken: 'Kraken', coinbase: 'Coinbase' };

const importForm = document.getElementById('import-form');
const fileInput = document.getElementById('import-file');
const previewEl = document.getElementById('preview');
const confirmButton = document.getElementById('import-confirm');

function plural(count, one, many) {
    return `${count} ${count === 1 ? one : many}`;
}

// Upload a file as multipart form data (apiRequest only sends JSON)
async function uploadFile(url, file) {
    const body = new FormData();
    body.append('file', file);
    try {
        const response = await fetch(url, { method: 'POST', body });
        if (response.status === 401) {
            window.location.href = '/auth/login';
            return { ok: false, data: {} };
        }
        const data = await response.json().catch(() => ({}));
        return { ok: response.ok, data };
    } catch (error) {
        return { ok: false, data: { error: 'Could not reach the server. Please try again.' } };
    }
}

// ---------- Preview ----------

function hidePreview() {
    previewEl.classList.add('hidden');
}

function renderPreview(p) {
    document.getElementById('preview-title').textContent = `${p.filename} · ${PROVIDERS[p.provider] || p.provider}`;
    document.getElementById('preview-counts').textContent =
        `${plural(p.trades, 'trade', 'trades')} found: ${p.new} new, ${p.duplicates} already in CoinFlow`;

    const sides = [];
    if (p.buys) sides.push(plural(p.buys, 'buy', 'buys'));
    if (p.sells) sides.push(plural(p.sells, 'sale', 'sales'));
    if (p.rewards) sides.push(plural(p.rewards, 'reward', 'rewards'));
    document.getElementById('preview-sides').textContent = sides.join(' · ');
    document.getElementById('preview-dates').textContent =
        p.date_from ? `${formatDate(p.date_from)} – ${formatDate(p.date_to)}` : '';

    // Anything that would make the import fail is shown up front, and blocks the button
    let problem = null;
    if (p.already_imported) {
        problem = 'This file was already imported. Remove it below first if you want to import it again.';
    } else if (p.trades === 0) {
        problem = 'No BTC trades in USD were found in this file.';
    } else if (p.new === 0) {
        problem = 'Every trade in this file is already in CoinFlow.';
    } else if (p.problem) {
        problem = `This import would make your history impossible: ${p.problem}. ` +
            'Import the earlier history first, or add the missing buys by hand.';
    }
    const problemEl = document.getElementById('preview-problem');
    problemEl.textContent = problem || '';
    problemEl.classList.toggle('hidden', !problem);

    const skippedEl = document.getElementById('preview-skipped');
    skippedEl.classList.toggle('hidden', p.skipped_count === 0);
    skippedEl.open = false;
    skippedEl.querySelector('summary').textContent = `${plural(p.skipped_count, 'row', 'rows')} skipped`;
    const list = skippedEl.querySelector('ul');
    list.replaceChildren(...p.skipped.map(s => {
        const li = document.createElement('li');
        li.textContent = `Line ${s.line}: ${s.reason}`;
        return li;
    }));
    if (p.skipped_count > p.skipped.length) {
        const more = document.createElement('li');
        more.textContent = `…and ${p.skipped_count - p.skipped.length} more`;
        list.appendChild(more);
    }

    confirmButton.textContent = `Import ${plural(p.new, 'trade', 'trades')}`;
    confirmButton.disabled = Boolean(problem);
    previewEl.classList.remove('hidden');
}

importForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;

    hidePreview();
    showLoading('Reading file...');
    const result = await uploadFile('/api/imports/preview', file);
    if (result.ok && result.data.success) {
        hideLoading();
        renderPreview(result.data.preview);
    } else {
        showError('Could not read this file', result.data.error || 'An error occurred.');
    }
});

confirmButton.addEventListener('click', async function() {
    const file = fileInput.files[0];
    if (!file) return;

    showLoading('Importing...');
    const result = await uploadFile('/api/imports', file);
    if (result.ok && result.data.success) {
        hidePreview();
        importForm.reset();
        showSuccess(`Imported ${plural(result.data.added, 'trade', 'trades')}`);
        loadImports();
    } else {
        showError('Could not import this file', result.data.error || 'An error occurred.');
    }
});

document.getElementById('import-cancel').addEventListener('click', () => {
    hidePreview();
    importForm.reset();
    fileInput.focus();
});

// ---------- Imported files ----------

function renderImports(imports) {
    const tbody = document.getElementById('imports-body');
    tbody.replaceChildren();
    document.getElementById('imports-empty').classList.toggle('hidden', imports.length > 0);

    imports.forEach(record => {
        const row = document.createElement('tr');
        row.dataset.id = record.id;
        const addCell = (text, className) => {
            const td = document.createElement('td');
            td.textContent = text;
            if (className) td.className = className;
            row.appendChild(td);
            return td;
        };

        addCell(record.filename, 'cell-type notes-cell').title = record.filename;
        addCell(PROVIDERS[record.provider] || record.provider);
        addCell(String(record.trade_count), 'num cell-trades');
        addCell(record.date_from ? `${formatDate(record.date_from)} – ${formatDate(record.date_to)}` : '—');
        addCell(formatDate(record.imported_at));

        const actionCell = addCell('', 'cell-actions');
        const actions = document.createElement('div');
        actions.className = 'row-actions';
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'pill pill-icon delete-button';
        removeButton.setAttribute('aria-label', `Remove import ${record.filename}`);
        removeButton.innerHTML = TRASH_ICON;  // constant markup, no user data
        removeButton.addEventListener('click', () => removeImport(record));
        actions.appendChild(removeButton);
        actionCell.appendChild(actions);

        tbody.appendChild(row);
    });
}

async function loadImports() {
    const result = await apiRequest('/api/imports');
    if (!result.ok || !result.data.success) {
        showError('Could not load your imports', 'Please refresh the page.');
        return;
    }
    renderImports(result.data.imports);
    // Marker for tests and scripts: the list has loaded at least once
    if (!document.getElementById('imports-list-loaded')) {
        const marker = document.createElement('span');
        marker.id = 'imports-list-loaded';
        marker.hidden = true;
        document.body.appendChild(marker);
    }
}

async function removeImport(record) {
    const question = `Remove ${record.filename} and its ${plural(record.trade_count, 'trade', 'trades')}?`;
    if (!await confirmAction(question, 'Remove')) {
        return;
    }
    showLoading('Removing...');
    const result = await apiRequest(`/api/imports/${record.id}`, { method: 'DELETE' });
    if (result.ok && result.data.success) {
        showSuccess('Import removed');
        loadImports();
    } else {
        showError('Could not remove this import', result.data.error);
    }
}

document.addEventListener('DOMContentLoaded', loadImports);
