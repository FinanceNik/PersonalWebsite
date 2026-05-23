// Service worker — precache static assets + stale-while-revalidate.
// CACHE_NAME bump triggers the activate cleanup of older caches.
var CACHE_NAME = 'ncc-v4';

var STATIC_ASSETS = [
    '/static/css_components/colors.css',
    '/static/css_components/base.css',
    '/static/css_components/layout.css',
    '/static/css_components/components.css',
    '/static/css_components/pages.css',
    '/static/css_components/navigation-bar.css',
    '/static/css_components/footer.css',
    '/static/css_components/sizes.css',
    '/static/js_components/ui-enhancements.js',
    '/static/js_components/theme-toggler.js',
    '/static/image_assets/icon-192.png',
    '/static/image_assets/logo.png',
    '/static/image_assets/profile-without-bg.webp',
    '/static/image_assets/contrast.png',
    '/static/image_assets/crescent-moon.png'
];

// Pages that change on every request, must not be cached at the SW layer
// (analytics, sitemap, feed, robots). The HTML branch below skips them.
var HTML_CACHE_SKIP = /^\/(analytics|sitemap\.xml|robots\.txt|blog\/feed\.xml|api\/)/;

// Soft cap on the HTML cache so it doesn't grow without bound. Once we cross
// the limit, drop the oldest N entries.
var HTML_CACHE_MAX = 30;

// Install — cache static assets
self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(
                names.filter(function (n) { return n !== CACHE_NAME; })
                     .map(function (n) { return caches.delete(n); })
            );
        })
    );
    self.clients.claim();
});

function trimHtmlCache(cache) {
    cache.keys().then(function (requests) {
        // Filter to the HTML-ish ones (everything not under /static/).
        var htmlEntries = requests.filter(function (req) {
            return !new URL(req.url).pathname.startsWith('/static/');
        });
        if (htmlEntries.length <= HTML_CACHE_MAX) return;
        var toDrop = htmlEntries.length - HTML_CACHE_MAX;
        // cache.keys() returns insertion order; drop the oldest.
        for (var i = 0; i < toDrop; i++) {
            cache.delete(htmlEntries[i]);
        }
    });
}

// Fetch — stale-while-revalidate for static, network-first for HTML
self.addEventListener('fetch', function (event) {
    var url = new URL(event.request.url);

    // Only handle GET requests
    if (event.request.method !== 'GET') return;

    // Static assets — cache first, fallback to network
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(function (cached) {
                var networkFetch = fetch(event.request).then(function (response) {
                    if (response.ok) {
                        var clone = response.clone();
                        caches.open(CACHE_NAME).then(function (cache) {
                            cache.put(event.request, clone);
                        });
                    }
                    return response;
                }).catch(function () {
                    return cached;
                });
                return cached || networkFetch;
            })
        );
        return;
    }

    // HTML pages — network first, fallback to cache.
    // Skip dynamic/feed/admin URLs that change on every request or aren't
    // useful offline (analytics, sitemap, robots, RSS, JSON APIs).
    var accept = event.request.headers.get('accept') || '';
    if (accept.includes('text/html') && !HTML_CACHE_SKIP.test(url.pathname)) {
        event.respondWith(
            fetch(event.request).then(function (response) {
                if (response.ok) {
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(function (cache) {
                        cache.put(event.request, clone);
                        trimHtmlCache(cache);
                    });
                }
                return response;
            }).catch(function () {
                return caches.match(event.request);
            })
        );
        return;
    }
});
