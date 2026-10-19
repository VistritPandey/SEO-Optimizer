import type { Metadata } from "next";

export const site = {
  name: "Your Optimiser",
  url: "https://youroptimiser.com",
  description:
    "Ongoing SEO care for a website that keeps changing. Your AI agent checks updates, prepares focused fixes in GitHub and verifies them after deployment.",
  repository: "https://github.com/VistritPandey/SEO-Optimizer",
};

export const publicPages = [
  "/",
  "/how-it-works",
  "/seo-and-ai-search",
  "/guides/continuous-seo",
  "/security",
  "/contact",
  "/privacy",
  "/terms",
];

export function pageMetadata(
  title: string,
  description: string,
  path: string,
): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { title: `${title} · ${site.name}`, description, url: path },
  };
}
