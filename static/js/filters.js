// Search and Filter Functionality

// Category Search
document.addEventListener('DOMContentLoaded', function() {
    // Category search functionality
    const categorySearch = document.getElementById('categorySearch');
    if (categorySearch) {
        categorySearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const categoryName = row.cells[0].textContent.toLowerCase();
                const categoryDesc = row.cells[1].textContent.toLowerCase();
                
                if (categoryName.includes(searchTerm) || categoryDesc.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
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
            const selectedCategory = categoryFilter ? categoryFilter.value : '';
            const roomCards = document.querySelectorAll('.col-md-6.col-lg-4');
            
            roomCards.forEach(card => {
                const roomName = card.querySelector('.card-title').textContent.toLowerCase();
                const roomCategory = card.querySelector('.badge').textContent;
                const roomDesc = card.querySelector('.card-text') ? 
                    card.querySelector('.card-text').textContent.toLowerCase() : '';
                
                const matchesSearch = roomName.includes(searchTerm) || roomDesc.includes(searchTerm);
                const matchesCategory = !selectedCategory || roomCategory === selectedCategory;
                
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
            const rows = document.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                if (row.cells && row.cells.length >= 2) {
                    const productName = row.cells[0].textContent.toLowerCase();
                    const productCategoryElement = row.cells[1].querySelector('.badge');
                    const productCategory = productCategoryElement ? productCategoryElement.textContent.toLowerCase() : '';
                    
                    const matchesSearch = productName.includes(searchTerm);
                    
                    // Category mapping for better matching
                    let matchesCategory = true;
                    if (selectedCategory) {
                        const categoryMap = {
                            'ichimliklar': ['drinks', 'ichimliklar'],
                            'gazaklar': ['snacks', 'gazaklar'],
                            'ovqatlar': ['food', 'ovqatlar'],
                            'shirinliklar': ['desserts', 'shirinliklar'],
                            'boshqa': ['other', 'boshqa']
                        };
                        
                        const validCategories = categoryMap[selectedCategory] || [selectedCategory];
                        matchesCategory = validCategories.some(cat => productCategory.includes(cat));
                    }
                    
                    if (matchesSearch && matchesCategory) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
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