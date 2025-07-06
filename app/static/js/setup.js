/**
 * Budget App Setup Flow
 * 
 * This script handles the setup flow UI elements like progress bar updates
 * and step status indicators.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Setup flow progress tracking
    htmx.on('htmx:afterSettle', function(event) {
        updateSetupProgress();
    });
    
    // Initial update
    updateSetupProgress();
});

/**
 * Updates the setup progress bar and step status based on the current step
 */
function updateSetupProgress() {
    // Get current step from the data attribute if available
    const setupContainer = document.querySelector('[data-setup-step]');
    if (!setupContainer) return;
    
    const currentStep = setupContainer.getAttribute('data-setup-step');
    const stepMap = {
        'status': { progress: 10, text: 'Checking setup...' },
        'countries': { progress: 20, text: 'Select Country' },
        'institutions': { progress: 40, text: 'Select Bank' },
        'bank-link': { progress: 60, text: 'Connect Bank' },
        'bank-pending': { progress: 70, text: 'Connecting...' },
        'accounts': { progress: 80, text: 'Select Accounts' },
        'complete': { progress: 100, text: 'Setup Complete!' }
    };
    
    // Update progress bar and status text if elements exist
    const progressBar = document.getElementById('progress-bar');
    const stepStatus = document.getElementById('step-status');
    
    if (progressBar && stepMap[currentStep]) {
        progressBar.style.width = `${stepMap[currentStep].progress}%`;
    }
    
    if (stepStatus && stepMap[currentStep]) {
        stepStatus.textContent = stepMap[currentStep].text;
    }
}
