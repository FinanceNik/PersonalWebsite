document.addEventListener('DOMContentLoaded', function () {

    // --- Scroll reveal with variants ---
    var revealEls = document.querySelectorAll('.card, .process-step, .blog-post-card, .lead-banner, .calc-result, .modular-container-services-one, .modular-container-services-two');
    revealEls.forEach(function (el) {
        if (!el.classList.contains('reveal') && !el.classList.contains('reveal-left') && !el.classList.contains('reveal-scale')) {
            el.classList.add('reveal');
        }
    });

    // Add reveal-left to process step content
    document.querySelectorAll('.process-step-content').forEach(function (el) {
        el.classList.add('reveal-left');
    });

    // Add reveal-scale to lead banners
    document.querySelectorAll('.lead-banner, .calc-result').forEach(function (el) {
        el.classList.remove('reveal');
        el.classList.add('reveal-scale');
    });

    // Add stagger class to card containers
    document.querySelectorAll('.card-container').forEach(function (el) {
        el.classList.add('reveal-stagger');
    });

    // Observe all revealable elements
    var allRevealEls = document.querySelectorAll('.reveal, .reveal-fade, .reveal-left, .reveal-scale');
    var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                // Also reveal stagger children
                if (entry.target.classList.contains('reveal-stagger')) {
                    entry.target.querySelectorAll('.reveal').forEach(function (child) {
                        child.classList.add('revealed');
                    });
                }
            }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    allRevealEls.forEach(function (el) { revealObserver.observe(el); });

    // Also observe stagger containers
    document.querySelectorAll('.reveal-stagger').forEach(function (el) {
        revealObserver.observe(el);
    });

    // --- Sticky header shadow (rAF throttled) ---
    var header = document.querySelector('.header');
    var headerScrolled = false;
    if (header) {
        function onScroll() {
            var shouldScroll = window.scrollY > 80;
            if (shouldScroll !== headerScrolled) {
                headerScrolled = shouldScroll;
                header.classList.toggle('scrolled', shouldScroll);
            }
        }
        window.addEventListener('scroll', function () {
            requestAnimationFrame(onScroll);
        }, { passive: true });
    }

    // --- Active page indicator ---
    var currentPath = window.location.pathname;
    document.querySelectorAll('.header__link').forEach(function (link) {
        var href = link.getAttribute('href');
        if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active-page');
        }
    });

    // --- Back to top button ---
    var btn = document.createElement('button');
    btn.className = 'back-to-top';
    btn.setAttribute('aria-label', 'Back to top');
    btn.innerHTML = '\u2191';
    document.body.appendChild(btn);

    window.addEventListener('scroll', function () {
        btn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    btn.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // --- Mobile menu close on link click + hamburger reset ---
    document.querySelectorAll('.dropdown-content a').forEach(function (link) {
        link.addEventListener('click', function () {
            var dropdown = document.querySelector('.dropdown');
            var hamburger = document.querySelector('.hamburger');
            if (dropdown) dropdown.classList.remove('open');
            if (hamburger) hamburger.classList.remove('is-active');
        });
    });

    // --- Hero typing animation ---
    var heroTitle = document.querySelector('.hero-title strong');
    if (heroTitle && heroTitle.textContent === 'NIK') {
        var text = heroTitle.textContent;
        heroTitle.textContent = '';
        heroTitle.style.borderRight = '2px solid var(--accent-color)';
        var i = 0;
        var typeInterval = setInterval(function () {
            heroTitle.textContent += text.charAt(i);
            i++;
            if (i >= text.length) {
                clearInterval(typeInterval);
                setTimeout(function () {
                    heroTitle.style.borderRight = 'none';
                }, 1000);
            }
        }, 150);
    }

    // --- Animated stats counter ---
    var statNumbers = document.querySelectorAll('.stat-number');
    if (statNumbers.length) {
        var statsObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var el = entry.target;
                    var target = parseInt(el.getAttribute('data-target'), 10);
                    var duration = 1500;
                    var start = 0;
                    var startTime = null;
                    function animate(ts) {
                        if (!startTime) startTime = ts;
                        var progress = Math.min((ts - startTime) / duration, 1);
                        var eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
                        el.textContent = Math.floor(eased * target);
                        if (progress < 1) {
                            requestAnimationFrame(animate);
                        } else {
                            el.textContent = target;
                        }
                    }
                    requestAnimationFrame(animate);
                    statsObserver.unobserve(el);
                }
            });
        }, { threshold: 0.5 });

        statNumbers.forEach(function (el) { statsObserver.observe(el); });
    }

    // --- Reading progress bar (blog posts only) ---
    var blogContent = document.querySelector('.blog-content');
    if (blogContent) {
        var progressBar = document.createElement('div');
        progressBar.className = 'reading-progress';
        document.body.appendChild(progressBar);

        window.addEventListener('scroll', function () {
            var rect = blogContent.getBoundingClientRect();
            var contentTop = rect.top + window.scrollY;
            var contentHeight = blogContent.offsetHeight;
            var scrolled = window.scrollY - contentTop + window.innerHeight * 0.3;
            var progress = Math.min(Math.max(scrolled / contentHeight * 100, 0), 100);
            progressBar.style.width = progress + '%';
        }, { passive: true });
    }
});
