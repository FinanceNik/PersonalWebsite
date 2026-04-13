document.addEventListener("DOMContentLoaded", function() {
    const canvas = document.getElementById('matrixCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const container = document.querySelector('.matrix-container');
    if (!container) return;

    function resizeCanvas() {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
    }

    resizeCanvas();

    const fontSize = 15;
    let columns = Math.floor(container.clientWidth / fontSize);
    let drops = Array(columns).fill(0);

    function draw() {
        const bgColor = getComputedStyle(document.documentElement).getPropertyValue('--matrix-background-color').trim();
        const textColor = getComputedStyle(document.documentElement).getPropertyValue('--matrix-text-color').trim();

        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = textColor;
        ctx.font = fontSize + 'px monospace';

        for (let i = 0; i < drops.length; i++) {
            const text = String.fromCharCode(Math.random() * 128);
            const x = i * fontSize;
            const y = drops[i] * fontSize;

            ctx.fillText(text, x, y);

            if (y > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }

    const interval = setInterval(draw, 50);

    window.addEventListener('resize', function() {
        resizeCanvas();
        columns = Math.floor(container.clientWidth / fontSize);
        drops = Array(columns).fill(0);
    });
});
