// Explicit application surface: project-scoped connection setup is allowed; worker secrets are not.
export function allowedRequest(path, method) {
  if (path.includes("..") || path.includes("%") || path.includes("\\"))
    return false;
  if (/^projects\/[A-Za-z0-9-]+\/connectors$/.test(path))
    return method === "GET";
  if (/^projects\/[A-Za-z0-9-]+\/connectors\/[a-z_]+$/.test(path))
    return ["PUT", "DELETE"].includes(method);
  if (
    /^projects\/[A-Za-z0-9-]+\/connectors\/[a-z_]+\/(collect|proposals|import|oauth)$/.test(
      path,
    )
  )
    return method === "POST";
  if (
    /^projects\/[A-Za-z0-9-]+\/connectors\/[a-z_]+\/proposals\/[a-f0-9]+\/(apply|rollback|verify)$/.test(
      path,
    )
  )
    return method === "POST";
  if (path === "account" || path === "github/repositories")
    return method === "GET";
  if (path === "github/connect") return ["POST", "DELETE"].includes(method);
  if (path === "github/install") return method === "POST";
  if (path === "projects") return ["GET", "POST"].includes(method);
  if (/^projects\/[A-Za-z0-9-]+$/.test(path))
    return ["GET", "PATCH"].includes(method);
  if (/^projects\/[A-Za-z0-9-]+\/(activity|strategy)$/.test(path))
    return method === "GET";
  if (/^projects\/[A-Za-z0-9-]+\/workspace$/.test(path))
    return ["GET", "PUT"].includes(method);
  if (
    /^projects\/[A-Za-z0-9-]+\/(jobs|strategy|citations|search-console)$/.test(
      path,
    )
  )
    return method === "POST";
  if (/^projects\/[A-Za-z0-9-]+\/content\/[A-Za-z0-9_-]+$/.test(path))
    return method === "POST";
  if (/^jobs\/[A-Za-z0-9-]+$/.test(path)) return method === "GET";
  return false;
}
