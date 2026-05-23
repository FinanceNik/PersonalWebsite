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

    // --- prefers-reduced-motion gate ---
    // Many users (vestibular conditions, low-spec devices, opt-in setting) ask
    // their browser to suppress non-essential motion. Both the hero typing
    // animation and the stats counter are decorative — show the final state
    // immediately when reduced-motion is requested.
    var REDUCED_MOTION = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- Hero typing animation ---
    // Opt-in via [data-typed] on the element. Decoupled from the actual text
    // so renaming "NIK" to anything else doesn't silently disable the effect.
    var typedEl = document.querySelector('.hero-title [data-typed]');
    if (typedEl && typedEl.textContent.trim().length > 0) {
        if (REDUCED_MOTION) {
            // Leave the final text in place; no setInterval, no caret.
        } else {
            var text = typedEl.textContent;
            typedEl.textContent = '';
            typedEl.style.borderRight = '2px solid var(--accent-color)';
            // Screen readers shouldn't hear "N" then "NI" then "NIK".
            typedEl.setAttribute('aria-label', text);
            typedEl.setAttribute('aria-live', 'off');
            var i = 0;
            var typeInterval = setInterval(function () {
                typedEl.textContent += text.charAt(i);
                i++;
                if (i >= text.length) {
                    clearInterval(typeInterval);
                    setTimeout(function () {
                        typedEl.style.borderRight = 'none';
                    }, 1000);
                }
            }, 150);
        }
    }

    // --- Animated stats counter ---
    // Templates render the final value as text so no-JS visitors see real numbers;
    // when JS is available we reset to 0 and animate up.
    var statNumbers = document.querySelectorAll('.stat-number');
    if (statNumbers.length) {
        // Tell screen readers not to read every intermediate count.
        statNumbers.forEach(function (el) {
            el.setAttribute('aria-live', 'off');
            var target = el.getAttribute('data-target') || el.textContent;
            el.setAttribute('aria-label', target);
        });

        if (REDUCED_MOTION) {
            // Skip the count-up; the text content is already the final number
            // (rendered by the template).
        } else {
            statNumbers.forEach(function (el) { el.textContent = '0'; });

            var statsObserver = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        var el = entry.target;
                        var target = parseInt(el.getAttribute('data-target'), 10);
                        var duration = 1500;
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
