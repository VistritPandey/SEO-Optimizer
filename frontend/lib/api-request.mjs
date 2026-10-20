/** Authenticated transport. Retry reads only; mutations never repeat after an uncertain response. */
export async function requestApi(
  path,
  method,
  body,
  getToken,
  fetcher = fetch,
) {
  let refreshed = false;
  let retried = false;
  const read = method === "GET";
  while (true) {
    const token = await getToken(refreshed);
    let response;
    try {
      response = await fetcher("/api/backend/" + path, {
        method,
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        signal: AbortSignal.timeout(
          path.endsWith("/citations") ? 110_000 : 40_000,
        ),
      });
    } catch {
      if (read && !retried) {
        retried = true;
        continue;
      }
      throw new Error(
        read
          ? "The workspace service could not be reached. Your saved data is unchanged."
          : "The response was interrupted. Check activity before repeating this action.",
      );
    }
    if (response.status === 401 && !refreshed) {
      refreshed = true;
      continue;
    }
    if (read && [502, 503, 504].includes(response.status) && !retried) {
      retried = true;
      continue;
    }
    const raw = await response.text();
    let result;
    try {
      result = raw ? JSON.parse(raw) : null;
    } catch {
      throw new Error(
        read
          ? "The workspace returned an unexpected response. Try loading it again."
          : "The action returned an unexpected response. Check activity before trying again.",
      );
    }
    if (!response.ok) {
      if (response.status === 401)
        throw new Error("Your session has expired. Sign in again.");
      throw new Error(
        typeof result?.detail === "string"
          ? result.detail
          : "The request could not be completed. Check your inputs and try again.",
      );
    }
    return result;
  }
}
