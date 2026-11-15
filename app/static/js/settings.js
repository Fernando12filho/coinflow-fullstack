// Settings page: save display settings

const settingsForm = document.getElementById('settings-form');

settingsForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    showLoading('Saving settings...');
    const result = await apiRequest('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({
            currency: settingsForm.currency.value,
            btc_unit: settingsForm.querySelector('input[name="btc_unit"]:checked').value,
            locale: settingsForm.locale.value
        })
    });
    if (result.ok && result.data.success) {
        showSuccess('Settings saved');
    } else {
        showError('Could not save settings', result.data.error || 'An error occurred.');
    }
});

// ---------- Delete all data ----------

const deleteForm = document.getElementById('delete-data-form');

deleteForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    if (!await confirmAction('Delete all your trades, imports and settings?', 'Delete')) {
        return;
    }
    showLoading('Deleting...');
    const result = await apiRequest('/api/account/delete-data', {
        method: 'POST',
        body: JSON.stringify({ confirm: deleteForm.confirm.value })
    });
    if (result.ok && result.data.success) {
        const { trades, imports } = result.data.deleted;
        const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
        deleteForm.reset();
        showSuccess(`Deleted ${plural(trades, 'trade', 'trades')} and ${plural(imports, 'import', 'imports')}`);
    } else {
        showError('Could not delete your data', result.data.error || 'An error occurred.');
    }
});
