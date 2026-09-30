// Newsletter page JavaScript

const loadingEl = document.getElementById('newsletter-loading');
const subscribedEl = document.getElementById('newsletter-subscribed');
const newsletterForm = document.getElementById('newsletter-form');

async function checkNewsletterStatus() {
    const result = await apiRequest('/api/newsletter/status');
    if (!result.ok || !result.data.success) {
        loadingEl.textContent = 'Could not check your subscription. Please refresh the page.';
        return;
    }

    loadingEl.classList.add('hidden');
    subscribedEl.classList.toggle('hidden', !result.data.subscribed);
    newsletterForm.classList.toggle('hidden', result.data.subscribed);
    if (result.data.subscribed) {
        document.getElementById('subscribed-email').textContent = result.data.email;
    }
}

newsletterForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    showLoading('Subscribing...');
    const result = await apiRequest('/api/newsletter/subscribe', {
        method: 'POST',
        body: JSON.stringify({ email: newsletterForm.email.value })
    });

    if (result.ok && result.data.success) {
        showSuccess('You are subscribed!');
        checkNewsletterStatus();
    } else {
        showError('Subscription failed', result.data.error);
    }
});

document.getElementById('unsubscribe-button').addEventListener('click', async function() {
    if (!await confirmAction('Unsubscribe from the newsletter?', 'Unsubscribe')) {
        return;
    }

    const result = await apiRequest('/api/newsletter/unsubscribe', { method: 'POST' });

    if (result.ok && result.data.success) {
        showSuccess('You have been unsubscribed');
        checkNewsletterStatus();
    } else {
        showError('Unsubscribe failed', result.data.error);
    }
});

document.addEventListener('DOMContentLoaded', checkNewsletterStatus);
