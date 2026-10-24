export const websiteSections = {
  overview: "overview",
  findings: "findings",
  activity: "audits",
  pages: "pages",
  research: "research",
  policy: "settings",
};

/** @template {{id: string}} T @param {T[]} projects @param {string} explicit @param {string} remembered */
export function selectWebsite(projects, explicit = "", remembered = "") {
  if (explicit) return projects.find((item) => item.id === explicit);
  return projects.find((item) => item.id === remembered) || projects[0];
}

/** @param {string} uid */
export function rememberedWebsite(uid) {
  if (!uid) return "";
  try {
    return localStorage.getItem(`optimiser-website:${uid}`) || "";
  } catch {
    return "";
  }
}

/** @param {string} uid @param {string} id */
export function rememberWebsite(uid, id) {
  if (!uid || !id) return;
  try {
    localStorage.setItem(`optimiser-website:${uid}`, id);
  } catch {
    /* Selection still works when browser storage is unavailable. */
  }
}

/** @param {string} tab @param {string} id */
export function websitePath(tab = "overview", id = "") {
  if (tab === "connectors")
    return `/dashboard/connections${id ? `?project=${encodeURIComponent(id)}` : ""}`;
  const section =
    Object.entries(websiteSections).find(([key]) => key === tab)?.[1] ||
    "overview";
  return `/dashboard/${section}${id ? `?project=${encodeURIComponent(id)}` : ""}`;
}
