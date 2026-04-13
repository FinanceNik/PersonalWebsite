try {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const currentTheme = localStorage.getItem('theme');

        if (currentTheme) {
            document.documentElement.setAttribute('data-theme', currentTheme);
            themeToggle.checked = (currentTheme === 'dark-mode');
        }

        themeToggle.addEventListener('change', function () {
            const theme = themeToggle.checked ? 'dark-mode' : 'light-mode';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });
    }
} catch (e) {
    // localStorage may be disabled
}
