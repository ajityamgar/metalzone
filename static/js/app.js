document.addEventListener('DOMContentLoaded', () => {
    // Mobile menu toggle
    const menuToggle = document.getElementById('menuToggle');
    const nav = document.getElementById('mainNav');

    if (menuToggle && nav) {
        menuToggle.addEventListener('click', () => {
            nav.classList.toggle('open');
            menuToggle.classList.toggle('open');
        });
    }

    // Auto-hide flash messages
    const flashWrapper = document.querySelector('.flash-wrapper');
    if (flashWrapper) {
        setTimeout(() => {
            flashWrapper.style.opacity = '0';
            flashWrapper.style.transform = 'translateX(-50%) translateY(-20px)';
            setTimeout(() => flashWrapper.remove(), 300);
        }, 5000);
    }

    // Search functionality
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    fetch(`/search?q=${encodeURIComponent(query)}`)
                        .then(res => res.json())
                        .then(data => {
                            // Handle search results if needed
                            console.log('Search results:', data);
                        })
                        .catch(err => console.error('Search error:', err));
                }, 300);
            }
        });
    }

    // Quantity input validation
    const quantityInputs = document.querySelectorAll('.quantity-input, input[name^="qty_"]');
    quantityInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            const max = parseInt(e.target.max);
            const min = parseInt(e.target.min) || 1;
            
            if (value < min) {
                e.target.value = min;
            } else if (value > max) {
                e.target.value = max;
                alert(`Maximum quantity available is ${max}`);
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = 'var(--danger)';
                    
                    setTimeout(() => {
                        field.style.borderColor = '';
                    }, 2000);
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // Image lazy loading
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Cart update confirmation
    const cartUpdateForms = document.querySelectorAll('form[action*="cart/update"]');
    cartUpdateForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const inputs = form.querySelectorAll('input[type="number"]');
            let hasChanges = false;
            
            inputs.forEach(input => {
                if (input.value !== input.defaultValue) {
                    hasChanges = true;
                }
            });
            
            if (!hasChanges) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Product image gallery
    const productImages = document.querySelectorAll('.gallery img[onclick]');
    productImages.forEach(img => {
        img.style.cursor = 'pointer';
        img.addEventListener('click', function() {
            const mainImage = this.parentElement.previousElementSibling || this.parentElement.querySelector('img:not([onclick])');
            if (mainImage) {
                mainImage.src = this.src;
            }
        });
    });

    // Add to cart animation with loading state
    const addToCartButtons = document.querySelectorAll('form[action*="cart/add"] button[type="submit"]');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const form = this.closest('form');
            if (form) {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Adding...';
                this.disabled = true;
                
                // Form will submit, but if there's an error, restore button
                setTimeout(() => {
                    if (!form.checkValidity()) {
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }
                }, 100);
            }
        });
    });
    
    // Loading states for forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                if (submitBtn.tagName === 'BUTTON') {
                    const originalText = submitBtn.innerHTML;
                    submitBtn.dataset.originalText = originalText;
                    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
                }
            }
        });
    });

    // Price formatting
    const priceElements = document.querySelectorAll('.price, .mrp');
    priceElements.forEach(el => {
        const text = el.textContent;
        if (text && !text.includes('₹')) {
            const num = parseFloat(text.replace(/[^0-9.]/g, ''));
            if (!isNaN(num)) {
                el.textContent = `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            }
        }
    });
});

// Utility function for AJAX requests
function makeRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    return fetch(url, options)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Request failed:', error);
            throw error;
        });
}
