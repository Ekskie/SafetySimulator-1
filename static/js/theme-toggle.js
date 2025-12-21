/**
 * SafeZard Theme Controller
 * Handles Light/Dark mode toggling and persistence via LocalStorage.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const toggleBtn = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const html = document.documentElement;

    // 1. Load Saved Theme on Init
    const savedTheme = localStorage.getItem('safezard_theme') || 'dark';
    applyTheme(savedTheme);

    // 2. Button Event Listener
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            applyTheme(newTheme);
            saveTheme(newTheme);
        });
    }

    /**
     * Applies the selected theme to the DOM and updates the icon.
     * @param {string} theme - 'dark' or 'light'
     */
    function applyTheme(theme) {
        // Set Bootstrap attribute
        html.setAttribute('data-bs-theme', theme);

        // Update Toggle Icon
        if (themeIcon) {
            if (theme === 'light') {
                themeIcon.classList.remove('bi-moon-stars-fill');
                themeIcon.classList.add('bi-sun-fill');
            } else {
                themeIcon.classList.remove('bi-sun-fill');
                themeIcon.classList.add('bi-moon-stars-fill');
            }
        }
    }

    /**
     * Saves preference to LocalStorage.
     * @param {string} theme - 'dark' or 'light'
     */
    function saveTheme(theme) {
        localStorage.setItem('safezard_theme', theme);
    }
});