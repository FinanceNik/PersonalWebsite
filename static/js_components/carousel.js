document.addEventListener('DOMContentLoaded', function () {
    var carousel = document.getElementById('testimonial-carousel');
    if (!carousel) return;

    var track = carousel.querySelector('.carousel-track');
    var slides = carousel.querySelectorAll('.carousel-slide');
    var dotsContainer = document.getElementById('carousel-dots');
    var prevBtn = carousel.querySelector('.carousel-nav--prev');
    var nextBtn = carousel.querySelector('.carousel-nav--next');
    var current = 0;
    var total = slides.length;
    var autoInterval = null;
    var AUTO_DELAY = 5000;

    // Build dots
    for (var i = 0; i < total; i++) {
        var dot = document.createElement('button');
        dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
        dot.setAttribute('aria-label', 'Go to testimonial ' + (i + 1));
        dot.setAttribute('data-index', i);
        dotsContainer.appendChild(dot);
    }

    var dots = dotsContainer.querySelectorAll('.carousel-dot');

    function goTo(index) {
        if (index < 0) index = total - 1;
        if (index >= total) index = 0;
        current = index;
        track.style.transform = 'translateX(-' + (current * 100) + '%)';
        dots.forEach(function (d, i) {
            d.classList.toggle('active', i === current);
        });
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    function startAuto() {
        stopAuto();
        autoInterval = setInterval(next, AUTO_DELAY);
    }

    function stopAuto() {
        if (autoInterval) clearInterval(autoInterval);
    }

    // Button listeners
    nextBtn.addEventListener('click', function () { next(); startAuto(); });
    prevBtn.addEventListener('click', function () { prev(); startAuto(); });

    // Dot listeners
    dots.forEach(function (dot) {
        dot.addEventListener('click', function () {
            goTo(parseInt(dot.getAttribute('data-index'), 10));
            startAuto();
        });
    });

    // Touch/swipe support
    var touchStartX = 0;
    var touchEndX = 0;

    track.addEventListener('touchstart', function (e) {
        touchStartX = e.changedTouches[0].screenX;
        stopAuto();
    }, { passive: true });

    track.addEventListener('touchend', function (e) {
        touchEndX = e.changedTouches[0].screenX;
        var diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) next(); else prev();
        }
        startAuto();
    }, { passive: true });

    // Pause on hover
    carousel.addEventListener('mouseenter', stopAuto);
    carousel.addEventListener('mouseleave', startAuto);

    // Respect reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return; // Don't auto-rotate
    }

    startAuto();
});
