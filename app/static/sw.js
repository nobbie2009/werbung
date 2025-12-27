const CACHE_NAME = 'ds-cache-v1';

// Assets to pre-cache
const PRECACHE_URLS = [
  '/',
  '/static/manifest.json', // If exists
  '/api/settings'
];

self.addEventListener('install', event => {
  self.skipWaiting(); // Activate immediately
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.map(key => {
        if (key !== CACHE_NAME) {
          return caches.delete(key);
        }
      })
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // 1. Media Files: Cache First, fallback to Network
  if (url.pathname.startsWith('/media/')) {
     event.respondWith(
       caches.open(CACHE_NAME).then(cache => {
         return cache.match(event.request).then(response => {
           return response || fetch(event.request).then(networkResponse => {
             cache.put(event.request, networkResponse.clone());
             return networkResponse;
           });
         });
       })
     );
     return;
  }

  // 2. Playlist & Settings: Network First, fallback to Cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).then(networkResponse => {
        const cloned = networkResponse.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, cloned));
        return networkResponse;
      }).catch(() => {
        return caches.match(event.request);
      })
    );
    return;
  }

  // 3. Default: Network Only (but could be nice to cache index.html too)
  event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
  );
});

// Listen for "SKIP_WAITING" message (triggered by Refresh button)
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
