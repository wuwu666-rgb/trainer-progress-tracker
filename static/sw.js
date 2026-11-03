const CACHE='repbook-shell-v2-en';
const SHELL=['/','/static/index.html','/static/styles.css','/static/app.js','/static/storage.js','/static/icon.svg','/static/manifest.json'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('repbook-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api/'))return;
 if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match('/')));
 else if(SHELL.includes(url.pathname))event.respondWith(caches.match(event.request).then(c=>c||fetch(event.request)));
});
