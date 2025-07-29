// Dashboard specific JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh dashboard every 30 seconds
    if (window.location.pathname === '/dashboard') {
        setInterval(function() {
            // Only refresh if no modals are open
            if (!document.querySelector('.modal.show')) {
                window.location.reload();
            }
        }, 30000); // 30 seconds
    }

    // Format numbers with thousand separators
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    // Add confirmation dialogs for dangerous actions
    document.querySelectorAll('[data-confirm]').forEach(function(element) {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Update session totals dynamically (for session detail page)
    if (window.location.pathname.includes('/sessions/')) {
        updateSessionTotals();
    }
});

function updateSessionTotals() {
    // This function can be called after adding/removing products
    // to update the session totals without full page refresh
    const sessionPriceElements = document.querySelectorAll('[data-session-price]');
    const productsTotalElements = document.querySelectorAll('[data-products-total]');
    const totalPriceElements = document.querySelectorAll('[data-total-price]');

    // Implementation would depend on having API endpoints to fetch updated totals
    // For now, we'll just refresh the page
    if (sessionPriceElements.length > 0) {
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

// Function to show loading state on buttons
function showLoading(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="spinner-border spinner-border-sm"></i> Loading...';
    button.disabled = true;
    
    return function() {
        button.innerHTML = originalText;
        button.disabled = false;
    };
}

// Add loading states to form submissions
document.querySelectorAll('form').forEach(function(form) {
    form.addEventListener('submit', function(e) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            showLoading(submitButton);
        }
    });
});
