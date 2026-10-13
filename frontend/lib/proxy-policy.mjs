// Explicit application surface: credentials and worker endpoints are never proxied.
export function allowedRequest(path, method) {
  if (path.includes('..') || path.includes('%') || path.includes('\\')) return false;
  if (path === 'account' || path === 'github/repositories') return method === 'GET';
  if (path === 'github/connect') return ['POST', 'DELETE'].includes(method);
  if (path === 'projects') return ['GET', 'POST'].includes(method);
  if (/^projects\/[A-Za-z0-9-]+$/.test(path)) return ['GET', 'PATCH'].includes(method);
  if (/^projects\/[A-Za-z0-9-]+\/(activity|strategy)$/.test(path)) return method === 'GET';
  if (/^projects\/[A-Za-z0-9-]+\/research$/.test(path)) return ['GET', 'PUT'].includes(method);
  if (/^projects\/[A-Za-z0-9-]+\/(jobs|content|strategy|citations\/probe|search-console)$/.test(path)) return method === 'POST';
  if (/^jobs\/[A-Za-z0-9-]+$/.test(path)) return method === 'GET';
  return false;
}
