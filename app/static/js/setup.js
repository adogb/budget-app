/**
 * Budget App Setup Flow - Simple Vanilla JS
 * 
 * Only handles:
 * - Bank search filtering
 * - Account checkbox validation
 * - Progress bar updates
 */

const Setup = {
    /**
     * Step configuration with progress percentages and labels
     */
    stepConfig: {
        'start': { progress: 10, label: 'Getting started...' },
        'status': { progress: 10, label: 'Checking setup...' },
        'countries': { progress: 25, label: 'Step 1: Select Country' },
        'institutions': { progress: 50, label: 'Step 2: Select Bank' },
        'bank-link': { progress: 60, label: 'Step 3: Connect Bank' },
        'bank-pending': { progress: 70, label: 'Step 3: Connecting...' },
        'accounts': { progress: 85, label: 'Step 4: Select Accounts' },
        'complete': { progress: 100, label: 'Setup Complete!' }
    },

    /**
     * Initialize the setup flow
     */
    init() {
        this.updateProgress();
        this.initBankSearch();
        this.initAccountForm();
    },

    /**
     * Initialize bank search functionality
     */
    initBankSearch() {
        const searchInput = document.getElementById('bank-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const bankItems = document.querySelectorAll('.bank-item');
            
            bankItems.forEach(item => {
                const bankName = item.textContent.toLowerCase();
                item.style.display = bankName.includes(searchTerm) ? '' : 'none';
            });
        });
    },

    /**
     * Initialize account form checkbox validation
     */
    initAccountForm() {
        const form = document.getElementById('account-form');
        if (!form) return;

        const checkboxes = form.querySelectorAll('.account-checkbox');
        const submitBtn = document.getElementById('save-accounts-btn');

        const updateButtonState = () => {
            const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
            submitBtn.disabled = !anyChecked;
            if (!anyChecked) {
                submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        };

        checkboxes.forEach(cb => cb.addEventListener('change', updateButtonState));
        updateButtonState();
    },

    /**
     * Update progress bar based on current step
     */
    updateProgress() {
        const stepContent = document.querySelector('[data-step]');
        if (!stepContent) return;

        const step = stepContent.getAttribute('data-step');
        const config = this.stepConfig[step];
        if (!config) return;

        const progressBar = document.getElementById('progress-bar');
        const stepStatus = document.getElementById('step-status');

        if (progressBar) {
            progressBar.style.width = `${config.progress}%`;
            progressBar.className = step === 'complete' 
                ? 'bg-green-600 h-2.5 rounded-full transition-all duration-300'
                : 'bg-indigo-600 h-2.5 rounded-full transition-all duration-300';
        }

        if (stepStatus) {
            stepStatus.textContent = config.label;
            stepStatus.className = step === 'complete' 
                ? 'text-green-600 font-medium' 
                : 'text-indigo-600 font-medium';
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => Setup.init());
