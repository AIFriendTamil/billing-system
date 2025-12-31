var el = document.getElementById("wrapper");
var toggleButton = document.getElementById("menu-toggle");

toggleButton.onclick = function () {
    el.classList.toggle("toggled");
};

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
