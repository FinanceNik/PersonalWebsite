var CACHE_NAME = 'ncc-v1';
var STATIC_ASSETS = [
    '/static/css_components/colors.css',
    '/static/css_components/styles.css',
    '/static/css_components/navigation-bar.css',
    '/static/css_components/footer.css',
    '/static/css_components/sizes.css',
    '/static/js_components/ui-enhancements.js',
    '/static/js_components/theme-toggler.js',
    '/static/image_assets/logo.png',
    '/static/image_assets/profile-without-bg.webp',
    '/static/image_assets/contrast.png',
    '/static/image_assets/crescent-moon.png',
    '/static/image_assets/linkedin-seeklogo.com.svg'
];

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

    // HTML pages — network first, fallback to cache
    if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
        event.respondWith(
            fetch(event.request).then(function (response) {
                var clone = response.clone();
                caches.open(CACHE_NAME).then(function (cache) {
                    cache.put(event.request, clone);
                });
                return response;
            }).catch(function () {
                return caches.match(event.request);
            })
        );
        return;
    }
});
