var el = document.getElementById("wrapper");
var toggleButton = document.getElementById("menu-toggle");
var sidebar = document.getElementById("sidebar-wrapper");

toggleButton.onclick = function (e) {
    e.stopPropagation(); // Prevent event from bubbling
    el.classList.toggle("toggled");
};

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(event) {
    // Check if we're on mobile (sidebar is toggled visible)
    if (window.innerWidth < 768 && el.classList.contains('toggled')) {
        // Check if click is outside sidebar and toggle button
        if (!sidebar.contains(event.target) && !toggleButton.contains(event.target)) {
            el.classList.remove('toggled');
        }
    }
});

// Prevent clicks inside sidebar from closing it
sidebar.addEventListener('click', function(e) {
    e.stopPropagation();
});

// Theme Toggle
const themeToggle = document.getElementById('theme-toggle');
const htmlEl = document.documentElement;

// Check local storage
const currentTheme = localStorage.getItem('theme') || 'light';
htmlEl.setAttribute('data-bs-theme', currentTheme);
updateThemeIcon(currentTheme);

themeToggle.addEventListener('click', () => {
    const theme = htmlEl.getAttribute('data-bs-theme');
    const newTheme = theme === 'light' ? 'dark' : 'light';
    
    htmlEl.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    if (theme === 'dark') {
        themeToggle.innerHTML = '<i class="fas fa-sun"></i><span class="d-none d-md-inline"> Light Mode</span>';
    } else {
        themeToggle.innerHTML = '<i class="fas fa-moon"></i><span class="d-none d-md-inline"> Dark Mode</span>';
    }
}

// Counter Animation for Dashboard
document.addEventListener('DOMContentLoaded', function() {
    const counters = document.querySelectorAll('.counter');
    counters.forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-target'));
        const increment = target / 50;
        let current = 0;
        
        const updateCounter = () => {
            if (current < target) {
                current += increment;
                if (current > target) current = target;
                counter.textContent = counter.textContent.includes('₹') 
                    ? '₹' + current.toFixed(2) 
                    : Math.ceil(current);
                requestAnimationFrame(updateCounter);
            }
        };
        
        updateCounter();
    });
});
