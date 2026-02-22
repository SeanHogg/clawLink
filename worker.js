addEventListener('fetch', event => {
  // simple proxy to whichever origin is running the Python app;
  // adjust the target URL as needed (e.g. http://localhost:8000)
  const url = new URL(event.request.url);
  // strip the /coderclawlink prefix and forward
  const target = new URL(url.pathname.replace(/^\/coderclawlink/, ''), 'https://coderclaw.ai');
  const init = { method: event.request.method, headers: event.request.headers };
  event.respondWith(fetch(target.toString(), init));
});