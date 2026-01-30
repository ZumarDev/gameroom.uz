// Search and Filter Functionality

// Category Search
document.addEventListener('DOMContentLoaded', function() {
    // Category search functionality (for rooms_management page)
    const categorySearch = document.getElementById('categorySearch');
    if (categorySearch) {
        categorySearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            // Use .category-item class for category cards
            const categoryCards = document.querySelectorAll('.category-item');
            
            categoryCards.forEach(card => {
                const categoryName = card.dataset.categoryName || '';
                const cardTitle = card.querySelector('.card-title');
                const cardText = card.querySelector('.card-text');
                const name = cardTitle ? cardTitle.textContent.toLowerCase() : '';
                const desc = cardText ? cardText.textContent.toLowerCase() : '';
                
                if (name.includes(searchTerm) || desc.includes(searchTerm) || categoryName.includes(searchTerm)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Room search and filter functionality
    const roomSearch = document.getElementById('roomSearch');
    const categoryFilter = document.getElementById('categoryFilter');
    
    if (roomSearch || categoryFilter) {
        function filterRooms() {
            const searchTerm = roomSearch ? roomSearch.value.toLowerCase() : '';
            const selectedCategory = categoryFilter ? categoryFilter.value.toLowerCase() : '';
            // Use .room-item class for room cards
            const roomCards = document.querySelectorAll('.room-item');
            
            roomCards.forEach(card => {
                const roomName = card.dataset.roomName || '';
                const roomCategory = card.dataset.category || '';
                const cardText = card.querySelector('.card-text');
                const roomDesc = cardText ? cardText.textContent.toLowerCase() : '';
                
                const matchesSearch = roomName.includes(searchTerm) || roomDesc.includes(searchTerm);
                const matchesCategory = !selectedCategory || roomCategory.includes(selectedCategory.toLowerCase());
                
                if (matchesSearch && matchesCategory) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }
        
        if (roomSearch) {
            roomSearch.addEventListener('input', filterRooms);
        }
        if (categoryFilter) {
            categoryFilter.addEventListener('change', filterRooms);
        }
    }

    // Product search and filter functionality
    const productSearch = document.getElementById('productSearch');
    const productCategoryFilter = document.getElementById('productCategoryFilter');
    
    if (productSearch || productCategoryFilter) {
        function filterProducts() {
            const searchTerm = productSearch ? productSearch.value.toLowerCase() : '';
            const selectedCategory = productCategoryFilter ? productCategoryFilter.value.toLowerCase() : '';
            
            // Products are displayed as cards with .product-item class
            const productCards = document.querySelectorAll('.product-item');
            
            productCards.forEach(cardContainer => {
                const productName = cardContainer.dataset.productName || '';
                const productCategory = cardContainer.dataset.category || '';
                
                const matchesSearch = productName.includes(searchTerm);
                
                // Category matching
                let matchesCategory = true;
                if (selectedCategory) {
                    matchesCategory = productCategory.includes(selectedCategory.toLowerCase());
                }
                
                if (matchesSearch && matchesCategory) {
                    cardContainer.style.display = '';
                } else {
                    cardContainer.style.display = 'none';
                }
            });
        }
        
        if (productSearch) {
            productSearch.addEventListener('input', filterProducts);
        }
        if (productCategoryFilter) {
            productCategoryFilter.addEventListener('change', filterProducts);
        }
    }
});

// Analytics date selection functionality
function toggleDateInputs() {
    const reportType = document.getElementById('reportType').value;
    const dailySection = document.getElementById('dailyDateSection');
    const monthlySection = document.getElementById('monthlyDateSection');
    
    if (reportType === 'daily') {
        dailySection.style.display = 'block';
        monthlySection.style.display = 'none';
    } else {
        dailySection.style.display = 'none';
        monthlySection.style.display = 'block';
    }
}

function loadReport() {
    const reportType = document.getElementById('reportType').value;
    let dateParam = '';
    
    if (reportType === 'daily') {
        const selectedDate = document.getElementById('selectedDate').value;
        dateParam = `?type=daily&date=${selectedDate}`;
    } else {
        const selectedMonth = document.getElementById('selectedMonth').value;
        dateParam = `?type=monthly&month=${selectedMonth}`;
    }
    
    // Show loading state
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Yuklanmoqda...';
    button.disabled = true;
    
    // Reload page with new parameters
    window.location.href = '/analytics' + dateParam;
}

// Initialize date inputs with current values
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const currentDate = today.toISOString().split('T')[0];
    const currentMonth = today.toISOString().slice(0, 7);
    
    const selectedDateInput = document.getElementById('selectedDate');
    const selectedMonthInput = document.getElementById('selectedMonth');
    
    if (selectedDateInput && !selectedDateInput.value) {
        selectedDateInput.value = currentDate;
    }
    if (selectedMonthInput && !selectedMonthInput.value) {
        selectedMonthInput.value = currentMonth;
    }
});