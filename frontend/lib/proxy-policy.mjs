// Explicit application surface: credentials and worker endpoints are never proxied.
export function allowedRequest(path, method) {
  if (path.includes('..') || path.includes('%') || path.includes('\\')) return false;
  if (path === 'account' || path === 'github/repositories') return method === 'GET';
  if (path === 'github/connect') return ['POST', 'DELETE'].includes(method);
  if (path === 'projects') return ['GET', 'POST'].includes(method);
  if (/^projects\/[A-Za-z0-9-]+$/.test(path)) return ['GET', 'PATCH'].includes(method);
  if (/^projects\/[A-Za-z0-9-]+\/(activity|strategy)$/.test(path)) return method === 'GET';
  if (/^projects\/[A-Za-z0-9-]+\/workspace$/.test(path)) return ['GET', 'PUT'].includes(method);
  if (/^projects\/[A-Za-z0-9-]+\/(jobs|strategy|citations|search-console)$/.test(path)) return method === 'POST';
  if (/^projects\/[A-Za-z0-9-]+\/content\/[A-Za-z0-9_-]+$/.test(path)) return method === 'POST';
  if (/^jobs\/[A-Za-z0-9-]+$/.test(path)) return method === 'GET';
  return false;
}
