addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // When the request comes in via app.coderclaw.ai the pathname has no /coderclawlink
  // prefix – prepend it so the request resolves to the right page on coderclaw.ai.
  let pathname = url.pathname;
  if (url.hostname === 'app.coderclaw.ai') {
    // '/' → '/coderclawlink', '/foo' → '/coderclawlink/foo'
    pathname = '/coderclawlink' + (pathname === '/' ? '' : pathname);
  }

  const target = new URL(pathname, 'https://coderclaw.ai');
  // Forward query string too
  target.search = url.search;

  const init = { method: event.request.method, headers: event.request.headers };
  event.respondWith(fetch(target.toString(), init));
});