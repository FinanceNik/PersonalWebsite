document.addEventListener("DOMContentLoaded", function () {
    var canvas = document.getElementById('matrixCanvas');
    if (!canvas) return;
    var container = document.querySelector('.matrix-container');
    if (!container) return;

    var ctx = canvas.getContext('2d');
    var fontSize = 15;
    // Katakana + hex digits — the original Matrix charset, no random control codes.
    var charset = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';

    var columns = 0;
    var drops = [];

    function resize() {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        columns = Math.floor(canvas.width / fontSize) || 1;
        drops = new Array(columns).fill(0);
    }

    // Cache theme colors; refresh only when data-theme actually changes.
    var bgColor = '';
    var textColor = '';
    function refreshColors() {
        var root = getComputedStyle(document.documentElement);
        bgColor = root.getPropertyValue('--matrix-background-color').trim();
        textColor = root.getPropertyValue('--matrix-text-color').trim();
    }

    function draw() {
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = textColor;
        ctx.font = fontSize + 'px monospace';

        for (var i = 0; i < drops.length; i++) {
            var ch = charset.charAt(Math.floor(Math.random() * charset.length));
            var x = i * fontSize;
            var y = drops[i] * fontSize;
            ctx.fillText(ch, x, y);
            if (y > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }

    resize();
    refreshColors();

    // Reduced motion: paint a single static frame and stop. The visual remains,
    // the CPU does not.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        draw();
        return;
    }

    // rAF-driven loop throttled to ~20fps; pauses automatically when the tab
    // is hidden (browsers stop firing rAF then) and when the container scrolls
    // out of view (IntersectionObserver below).
    var FRAME_MS = 50;
    var lastFrame = 0;
    var rafId = null;
    var inView = false;

    function loop(ts) {
        if (!inView) { rafId = null; return; }
        if (ts - lastFrame >= FRAME_MS) {
            draw();
            lastFrame = ts;
        }
        rafId = requestAnimationFrame(loop);
    }

    function start() {
        if (rafId != null) return;
        lastFrame = 0;
        rafId = requestAnimationFrame(loop);
    }

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            inView = entry.isIntersecting;
            if (inView) start();
        });
    }, { threshold: 0 });
    observer.observe(container);

    // Theme toggle changes --matrix-* CSS vars; re-read them when data-theme flips.
    var themeObserver = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
            if (mutations[i].attributeName === 'data-theme') {
                refreshColors();
                break;
            }
        }
    });
    themeObserver.observe(document.documentElement, { attributes: true });

    // Debounce resize so we don't rebuild the drops array per pixel.
    var resizeTimer = null;
    window.addEventListener('resize', function () {
        if (resizeTimer) clearTimeout(resizeTimer);
        resizeTimer = setTimeout(resize, 150);
    });
});
