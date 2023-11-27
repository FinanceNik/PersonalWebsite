const themeToggle = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme');

if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
    if (currentTheme === 'dark-mode') {
        themeToggle.checked = true;
    }
}

themeToggle.addEventListener('change', function () {
    if (themeToggle.checked) {
        document.documentElement.setAttribute('data-theme', 'dark-mode');
        localStorage.setItem('theme', 'dark-mode');
    } else {
        document.documentElement.setAttribute('data-theme', 'light-mode');
        localStorage.setItem('theme', 'light-mode');
    }
});