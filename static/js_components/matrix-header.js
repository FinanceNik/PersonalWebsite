document.addEventListener("DOMContentLoaded", function() {
    const canvas = document.getElementById('matrixCanvasHeader');
    const ctx = canvas.getContext('2d');
    const container = document.querySelector('.matrix-container');

    function resizeCanvas() {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--matrix-text-color').trim();
    const fontSize = 15;
    const columns = Math.floor(window.innerWidth / fontSize);
    let drops = Array(columns).fill(0);

    function draw() {
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--matrix-background-color').trim();
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = textColor;
        ctx.font = `${fontSize}px monospace`;

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

    setInterval(draw, 50);

    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        drops = Array(Math.floor(window.innerWidth / fontSize)).fill(0);
    });
});
